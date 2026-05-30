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
    .apt_install("ffmpeg", "wget", "fontconfig")
    .pip_install("requests")
    .run_commands(
        # Instala Poppins ExtraBold do Google Fonts
        "mkdir -p /usr/share/fonts/poppins",
        "wget -q -O /usr/share/fonts/poppins/Poppins-ExtraBold.ttf "
        "'https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf'",
        "fc-cache -f -v",
    )
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

TARGET_W = 1080
TARGET_H = 1920

FONT_PATH = '/usr/share/fonts/poppins/Poppins-ExtraBold.ttf'

# Zona segura TikTok: topo começa em ~15% da altura (288px em 1920)
TEXT_Y_TOP = 210   # px do topo onde o bloco de texto é posicionado


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


def wrap_text(text, max_chars=22):
    """Quebra o texto em linhas para caber no headline."""
    words = text.split()
    lines = []
    current = ''
    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = (current + ' ' + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_headline_filter(text, style_seed, font_path=FONT_PATH):
    """
    Gera o filtro FFmpeg para o headline no topo.
    style_seed par = fundo branco + texto preto
    style_seed ímpar = fundo preto + texto branco
    Retorna string de filtro vf pronta para uso.
    """
    if not text or not text.strip():
        return None

    # Variação de cor por vídeo — determinística pelo seed
    dark_style = (style_seed % 2 == 1)
    bg_color    = '0x000000DD' if dark_style else '0xFFFFFFEE'
    font_color  = 'white'      if dark_style else 'black'

    font_size   = 54
    pad_x       = 40
    pad_y       = 22
    line_spacing = 8
    corner_r    = 14

    lines = wrap_text(text.strip(), max_chars=22)
    num_lines = len(lines)

    # Altura total do bloco
    line_h   = font_size + line_spacing
    box_h    = pad_y * 2 + line_h * num_lines - line_spacing
    box_w    = TARGET_W - 120   # margem lateral de 60px de cada lado
    box_x    = 60
    box_y    = TEXT_Y_TOP

    # Constrói filtros: drawbox (fundo) + drawtext por linha
    filters = []

    # Fundo com bordas arredondadas via drawbox
    filters.append(
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:"
        f"color={bg_color}:t=fill"
    )

    # Texto linha por linha, centralizado
    for i, line in enumerate(lines):
        # Escapa caracteres especiais para o FFmpeg drawtext
        line_escaped = (line
            .replace('\\', '\\\\')
            .replace(':', '\\:')
            .replace("'", "\\'")
        )
        text_y = box_y + pad_y + i * line_h
        filters.append(
            f"drawtext=fontfile='{font_path}':"
            f"text='{line_escaped}':"
            f"fontcolor={font_color}:"
            f"fontsize={font_size}:"
            f"x=(w-text_w)/2:"
            f"y={text_y}:"
            f"line_spacing=0"
        )

    return ','.join(filters)


def normalize_segment(src, dst, trim_start, duration,
                      zoom_factor=1.0, headline_filter=None):
    """
    Re-encoda segmento para H264/AAC preservando color space original.
    Aplica headline via drawtext se fornecido.
    """
    vf_parts = []

    if zoom_factor > 1.0:
        w = int(TARGET_W / zoom_factor)
        h = int(TARGET_H / zoom_factor)
        x = int((TARGET_W - w) / 2)
        y = int((TARGET_H - h) / 2)
        vf_parts.append(
            f'crop={w}:{h}:{x}:{y},'
            f'scale={TARGET_W}:{TARGET_H}:flags=lanczos,'
            f'format=yuv420p'
        )
    else:
        vf_parts.append(
            f'scale={TARGET_W}:{TARGET_H}:'
            f'force_original_aspect_ratio=decrease,'
            f'pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,'
            f'format=yuv420p'
        )

    if headline_filter:
        vf_parts.append(headline_filter)

    vf = ','.join(vf_parts)

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(trim_start),
        '-t', str(duration),
        '-i', src,
        '-vf', vf,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-profile:v', 'high',
        '-level', '4.0',
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


def render_variation(groups, combo, output_path, tmp_dir, headline_text=''):
    rng = random.Random(combo['_micro_seed'] * 9973 + 1337)
    os.makedirs(tmp_dir, exist_ok=True)
    seg_files = []

    # Headline: determina estilo UMA vez por vídeo (seed do combo)
    headline_filter = None
    if headline_text and headline_text.strip():
        headline_filter = build_headline_filter(
            headline_text,
            style_seed=combo['_micro_seed']
        )

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

        trim_start = 0.0 if is_first else rng.randint(1, 4) / 30.0
        trim_end   = duration if is_last else duration - (rng.randint(1, 3) / 30.0)
        if trim_end <= trim_start + 0.1:
            trim_end = trim_start + 0.5
        actual_duration = trim_end - trim_start

        apply_zoom = (not is_first and not is_last and rng.random() < 0.20)
        zoom_factor = rng.uniform(1.03, 1.07) if apply_zoom else 1.0

        seg_out = os.path.join(tmp_dir, f'seg_{i:03d}.mp4')

        # Headline só no primeiro segmento (hook) — onde o texto faz sentido
        seg_headline = headline_filter if is_first else None

        ok = normalize_segment(
            filepath, seg_out,
            trim_start, actual_duration,
            zoom_factor=zoom_factor,
            headline_filter=seg_headline
        )

        if ok:
            seg_files.append(seg_out)
        else:
            print(f"[WARN] Falhou segmento {i}: {filepath}")

    if not seg_files:
        return False
    if len(seg_files) == 1:
        shutil.move(seg_files[0], output_path)
        return True
    return concat_segments(seg_files, output_path)


@app.function(timeout=1800, memory=2048)
def process_job_http(job_id: str, file_urls: list, output_base_url: str,
                     count: int, headline_text: str = ''):
    import requests
    import time

    tmp_base = f'/tmp/varvid_{job_id}'
    takes_dir = os.path.join(tmp_base, 'takes')
    output_dir = os.path.join(tmp_base, 'output')
    os.makedirs(takes_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    try:
        file_list = []
        for url in file_urls:
            fname = url.split('/')[-1]
            local_path = os.path.join(takes_dir, fname)
            print(f"[DL] {fname}")
            downloaded = False
            for attempt in range(5):
                try:
                    if attempt > 0:
                        time.sleep(3 * attempt)
                        print(f"[RETRY] {fname} tentativa {attempt+1}")
                    with requests.get(url, timeout=120, stream=True) as r:
                        if r.status_code == 200:
                            with open(local_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=1024*1024):
                                    if chunk:
                                        f.write(chunk)
                            file_list.append(local_path)
                            downloaded = True
                            break
                        else:
                            print(f"[WARN] HTTP {r.status_code} para {fname}")
                except Exception as e:
                    print(f"[ERR] Download {fname}: {e}")
            if not downloaded:
                print(f"[SKIP] Falhou após 5 tentativas: {fname}")

        if not file_list:
            return {'error': 'no files downloaded'}

        groups = group_takes(file_list)
        print(f"[INFO] Blocos: {list(groups.keys())}")
        print(f"[INFO] Headline: '{headline_text}'")

        combos = build_combinations(groups, count)
        output_files = []

        for i, combo in enumerate(combos):
            print(f"[RENDER] Variação {i+1}/{count}")
            out_path = os.path.join(output_dir, f'variation_{i+1:02d}.mp4')
            tmp_dir  = os.path.join(tmp_base, f'tmp_{i}')

            success = render_variation(
                groups, combo, out_path, tmp_dir,
                headline_text=headline_text
            )
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
                    print(f"[OK] {fname}")
                else:
                    print(f"[ERR] Upload {fname}: {resp.status_code}")
                os.remove(out_path)
            else:
                print(f"[ERR] Render falhou variação {i+1}")

        return {'status': 'done', 'files': output_files, 'count': len(output_files)}

    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)
