import modal
import os
import json
import uuid
import random
import re
import shutil
import subprocess
from pathlib import Path
from itertools import product as iterproduct

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("requests")
)

app = modal.App("varvid", image=image)

BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']
BLOCK_ALIASES = {
    'hook':      ['hook', 'he1', 'he2', 'he3', 'he4', 'he5', 'h1', 'h2', 'h3'],
    'story':     ['story', 'storia', 'estoria'],
    'revelacao': ['revelac', 'revelação', 'revelacao', 'rev'],
    'prova':     ['prova', 'proof', 'resultado'],
    'cta':       ['cta', 'call'],
}
SWAPPABLE_BLOCKS = {'hook', 'cta'}

# Resolução alvo — portrait TikTok
TARGET_W = 1080
TARGET_H = 1920


def classify_take(filename):
    stem = Path(filename).stem.lower()
    stem_clean = stem.replace('_', ' ').replace('-', ' ')
    block = None
    for b, aliases in BLOCK_ALIASES.items():
        for alias in aliases:
            if alias in stem_clean or stem_clean.startswith(alias):
                block = b
                break
        if block:
            break
    if not block:
        return {'block': 'unknown', 'variant': 1, 'part': 1}
    variant_match = re.search(r'(?:he|h|hook|cta|story|rev|prova)[\s_]?(\d)', stem_clean)
    variant = int(variant_match.group(1)) if variant_match else 1
    part_match = re.search(r'pt[\s_]?(\d+)', stem_clean)
    part = int(part_match.group(1)) if part_match else 1
    return {'block': block, 'variant': variant, 'part': part}


def group_takes(file_list):
    groups = {}
    for filepath in file_list:
        filename = os.path.basename(filepath)
        info = classify_take(filename)
        b, v, p = info['block'], info['variant'], info['part']
        if b not in groups:
            groups[b] = {}
        if v not in groups[b]:
            groups[b][v] = []
        groups[b][v].append((p, filepath))
    for block in groups:
        for variant in groups[block]:
            groups[block][variant].sort(key=lambda x: x[0])
            groups[block][variant] = [fp for _, fp in groups[block][variant]]
    return groups


def get_duration(filepath):
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath],
        capture_output=True, text=True
    )
    try:
        return float(json.loads(result.stdout)['format']['duration'])
    except:
        return 0.0


def build_combinations(groups, count, seed=42):
    rng = random.Random(seed)
    choices = {b: sorted(groups[b].keys()) for b in BLOCK_ORDER if b in groups}
    blocks = [b for b in BLOCK_ORDER if b in choices]
    all_combos = list(iterproduct(*[choices[b] for b in blocks]))
    rng.shuffle(all_combos)
    result = []
    for i in range(count):
        combo_tuple = all_combos[i % len(all_combos)]
        combo = {blocks[j]: combo_tuple[j] for j in range(len(blocks))}
        combo['_micro_seed'] = i
        result.append(combo)
    return result


def normalize_segment(src, dst, trim_start, duration, zoom_factor=1.0):
    """
    Re-encoda um segmento para H264/AAC com resolução e color space fixos.
    Sempre re-encoda (nunca stream copy) para garantir codec uniforme no concat.
    Aplica zoom se zoom_factor > 1.
    """
    # Filtro de vídeo base: escala para resolução alvo com padding se necessário
    # e corrige color space
    if zoom_factor > 1.0:
        w = int(TARGET_W / zoom_factor)
        h = int(TARGET_H / zoom_factor)
        x = int((TARGET_W - w) / 2)
        y = int((TARGET_H - h) / 2)
        vf = (
            f'crop={w}:{h}:{x}:{y},'
            f'scale={TARGET_W}:{TARGET_H}:flags=lanczos,'
            f'format=yuv420p'
        )
    else:
        # Escala para resolução alvo mantendo aspect ratio com pad preto
        vf = (
            f'scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,'
            f'pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,'
            f'format=yuv420p'
        )

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(trim_start),
        '-t', str(duration),
        '-i', src,
        '-vf', vf,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-profile:v', 'high',
        '-level', '4.0',
        '-colorspace', 'bt709',
        '-color_primaries', 'bt709',
        '-color_trc', 'bt709',
        '-c:a', 'aac',
        '-ar', '44100',
        '-ac', '2',
        '-b:a', '128k',
        '-avoid_negative_ts', 'make_zero',
        '-movflags', '+faststart',
        dst
    ]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and os.path.exists(dst)


def concat_segments(seg_files, output_path):
    """
    Concatena segmentos já normalizados usando stream copy (todos têm o mesmo codec).
    """
    concat_list = output_path + '.txt'
    with open(concat_list, 'w') as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_list,
        '-c', 'copy',
        '-movflags', '+faststart',
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True)
    os.remove(concat_list)
    return r.returncode == 0 and os.path.exists(output_path)


def render_variation(groups, combo, output_path, tmp_dir):
    rng = random.Random(combo['_micro_seed'] * 9973 + 1337)
    os.makedirs(tmp_dir, exist_ok=True)
    seg_files = []

    all_segs = []
    for block in BLOCK_ORDER:
        if block not in combo:
            continue
        for part_idx, filepath in enumerate(groups[block][combo[block]]):
            all_segs.append((block, part_idx, filepath))

    total = len(all_segs)

    for i, (block, part_idx, filepath) in enumerate(all_segs):
        duration = get_duration(filepath)
        if duration < 0.1:
            continue

        is_first = (i == 0)
        is_last  = (i == total - 1)

        # Micro-trim: remove poucos frames nas junções para suavizar cortes
        trim_start = 0.0 if is_first else rng.randint(1, 4) / 30.0
        trim_end   = duration if is_last else duration - (rng.randint(1, 3) / 30.0)
        if trim_end <= trim_start + 0.1:
            trim_end = trim_start + 0.5
        actual_duration = trim_end - trim_start

        # Zoom sutil: só em segmentos do meio, 20% de chance
        apply_zoom = (not is_first and not is_last and rng.random() < 0.20)
        zoom_factor = rng.uniform(1.03, 1.07) if apply_zoom else 1.0

        seg_out = os.path.join(tmp_dir, f'seg_{i:03d}.mp4')
        ok = normalize_segment(filepath, seg_out, trim_start, actual_duration, zoom_factor)

        if ok:
            seg_files.append(seg_out)
        else:
            print(f"[WARN] Falhou ao normalizar segmento {i}: {filepath}")

    if not seg_files:
        return False

    if len(seg_files) == 1:
        shutil.move(seg_files[0], output_path)
        return True

    return concat_segments(seg_files, output_path)


@app.function(timeout=600, memory=2048)
def process_job_http(job_id: str, file_urls: list, output_base_url: str, count: int):
    """Baixa arquivos do Render via HTTP, processa, envia outputs de volta."""
    import requests

    tmp_base = f'/tmp/varvid_{job_id}'
    takes_dir = os.path.join(tmp_base, 'takes')
    output_dir = os.path.join(tmp_base, 'output')
    os.makedirs(takes_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Baixa cada arquivo do Render
        file_list = []
        for url in file_urls:
            fname = url.split('/')[-1]
            local_path = os.path.join(takes_dir, fname)
            print(f"[DL] {fname}")
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(r.content)
                file_list.append(local_path)
            else:
                print(f"[WARN] Falhou ao baixar {url}: {r.status_code}")

        if not file_list:
            return {'error': 'no files downloaded'}

        groups = group_takes(file_list)
        print(f"[INFO] Blocos detectados: {list(groups.keys())}")

        combos = build_combinations(groups, count)
        output_files = []

        for i, combo in enumerate(combos):
            print(f"[RENDER] Variação {i+1}/{count}")
            out_path = os.path.join(output_dir, f'variation_{i+1:02d}.mp4')
            tmp_dir  = os.path.join(tmp_base, f'tmp_{i}')

            success = render_variation(groups, combo, out_path, tmp_dir)
            shutil.rmtree(tmp_dir, ignore_errors=True)

            if success and os.path.exists(out_path):
                fname = f'variation_{i+1:02d}.mp4'
                print(f"[UPLOAD] {fname} ({os.path.getsize(out_path)//1024//1024}MB)")
                with open(out_path, 'rb') as f:
                    resp = requests.put(
                        f"{output_base_url}/{fname}",
                        data=f.read(),
                        headers={'Content-Type': 'video/mp4'},
                        timeout=180
                    )
                if resp.status_code == 200:
                    output_files.append(fname)
                    print(f"[OK] {fname} enviado")
                else:
                    print(f"[ERR] Falhou upload {fname}: {resp.status_code}")
                os.remove(out_path)
            else:
                print(f"[ERR] Falhou render variação {i+1}")

        return {'status': 'done', 'files': output_files, 'count': len(output_files)}

    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)
