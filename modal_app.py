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

# ─── MODAL IMAGE ──────────────────────────────────────────────────────────────
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("flask", "werkzeug")
)

app = modal.App("varvid", image=image)

# Volume para armazenar jobs temporários
volume = modal.Volume.from_name("varvid-jobs", create_if_missing=True)
JOBS_DIR = "/jobs"

# ─── BLOCK DEFINITIONS ────────────────────────────────────────────────────────
BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']
BLOCK_ALIASES = {
    'hook':      ['hook', 'he1', 'he2', 'he3', 'he4', 'he5', 'h1', 'h2', 'h3'],
    'story':     ['story', 'storia', 'estoria'],
    'revelacao': ['revelac', 'revelação', 'revelacao', 'rev'],
    'prova':     ['prova', 'proof', 'resultado'],
    'cta':       ['cta', 'call'],
}
SWAPPABLE_BLOCKS = {'hook', 'story', 'cta'}


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
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except:
        return 0.0


def build_combinations(groups, count, seed=42):
    rng = random.Random(seed)
    choices = {}
    for block in BLOCK_ORDER:
        if block not in groups:
            continue
        choices[block] = sorted(groups[block].keys())
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


def render_variation(groups, combo, output_path, tmp_dir):
    rng = random.Random(combo['_micro_seed'] * 9973 + 1337)
    os.makedirs(tmp_dir, exist_ok=True)
    seg_files = []

    all_segs = []
    for block in BLOCK_ORDER:
        if block not in combo:
            continue
        variant = combo[block]
        files = groups[block][variant]
        for part_idx, filepath in enumerate(files):
            all_segs.append((block, part_idx, filepath, len(files)))

    for i, (block, part_idx, filepath, _) in enumerate(all_segs):
        duration = get_duration(filepath)
        if duration < 0.1:
            continue

        seg_out = os.path.join(tmp_dir, f'seg_{i:03d}.mp4')
        is_first = (i == 0)
        is_last = (i == len(all_segs) - 1)

        trim_start = 0.0
        if not is_first:
            trim_start = rng.randint(1, 5) / 30.0

        trim_end = duration
        if not is_last:
            trim_end = duration - (rng.randint(1, 3) / 30.0)
        if trim_end <= trim_start + 0.1:
            trim_end = trim_start + 0.1

        actual_duration = trim_end - trim_start
        apply_zoom = (not is_first and not is_last and rng.random() < 0.25)

        if apply_zoom:
            zoom_factor = rng.uniform(1.04, 1.08)
            w = int(1080 / zoom_factor)
            h = int(1920 / zoom_factor)
            x = int((1080 - w) / 2)
            y = int((1920 - h) / 2)
            vf = f'crop={w}:{h}:{x}:{y},scale=1080:1920:flags=bilinear'
            cmd = [
                'ffmpeg', '-y', '-ss', str(trim_start), '-t', str(actual_duration),
                '-i', filepath, '-vf', vf,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
                '-c:a', 'aac', '-ar', '44100', '-ac', '2',
                '-pix_fmt', 'yuv420p', '-avoid_negative_ts', 'make_zero', seg_out
            ]
        else:
            cmd = [
                'ffmpeg', '-y', '-ss', str(trim_start), '-t', str(actual_duration),
                '-i', filepath, '-c', 'copy',
                '-avoid_negative_ts', 'make_zero', seg_out
            ]

        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and os.path.exists(seg_out):
            seg_files.append(seg_out)

    if not seg_files:
        return False

    if len(seg_files) == 1:
        shutil.move(seg_files[0], output_path)
        return True

    concat_list = os.path.join(tmp_dir, 'concat.txt')
    with open(concat_list, 'w') as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")

    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
        '-c', 'copy', '-movflags', '+faststart', output_path
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        cmd2 = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '28',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', output_path
        ]
        r = subprocess.run(cmd2, capture_output=True)

    return r.returncode == 0 and os.path.exists(output_path)


# ─── MODAL FUNCTIONS ──────────────────────────────────────────────────────────

@app.function(
    volumes={JOBS_DIR: volume},
    timeout=600,
    memory=2048,
)
def process_job(job_id: str, count: int):
    """Processa as variações de vídeo. Roda no Modal com 2GB RAM."""
    job_dir = os.path.join(JOBS_DIR, job_id)
    takes_dir = os.path.join(job_dir, 'takes')
    output_dir = os.path.join(job_dir, 'output')
    status_file = os.path.join(job_dir, 'status.json')
    os.makedirs(output_dir, exist_ok=True)

    def save_status(data):
        with open(status_file, 'w') as f:
            json.dump(data, f)
        volume.commit()

    try:
        save_status({'status': 'analyzing', 'progress': 5, 'completed': 0, 'total': count})

        file_list = [
            os.path.join(takes_dir, f)
            for f in os.listdir(takes_dir)
            if not f.startswith('.')
        ]
        groups = group_takes(file_list)

        save_status({'status': 'planning', 'progress': 15, 'completed': 0, 'total': count})

        combos = build_combinations(groups, count)

        output_files = []
        for i, combo in enumerate(combos):
            out_path = os.path.join(output_dir, f'variation_{i+1:02d}.mp4')
            tmp_dir = os.path.join(job_dir, f'tmp_{i}')

            success = render_variation(groups, combo, out_path, tmp_dir)
            shutil.rmtree(tmp_dir, ignore_errors=True)

            if success:
                output_files.append(f'variation_{i+1:02d}.mp4')

            combo_desc = ' → '.join([
                f"{b.upper()}{'v'+str(combo[b]) if b in SWAPPABLE_BLOCKS else ''}"
                for b in BLOCK_ORDER if b in combo
            ])
            save_status({
                'status': 'rendering',
                'progress': 20 + int((i + 1) / count * 75),
                'completed': i + 1,
                'total': count,
                'last_combo': combo_desc,
            })

        save_status({
            'status': 'done',
            'progress': 100,
            'completed': count,
            'total': count,
            'files': output_files,
            'count': len(output_files),
        })

    except Exception as e:
        import traceback
        save_status({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc(),
        })


@app.function(
    volumes={JOBS_DIR: volume},
    timeout=120,
    memory=512,
)
def save_takes(job_id: str, files_data: list):
    """Salva os arquivos enviados no volume. files_data = [{name, data}]"""
    takes_dir = os.path.join(JOBS_DIR, job_id, 'takes')
    os.makedirs(takes_dir, exist_ok=True)

    for file_info in files_data:
        path = os.path.join(takes_dir, file_info['name'])
        with open(path, 'wb') as f:
            f.write(bytes(file_info['data']))

    # Escreve status inicial
    status_file = os.path.join(JOBS_DIR, job_id, 'status.json')
    with open(status_file, 'w') as f:
        json.dump({'status': 'ready'}, f)

    volume.commit()
    return {'ok': True, 'files': len(files_data)}


@app.function(
    volumes={JOBS_DIR: volume},
    timeout=30,
)
def get_status(job_id: str):
    """Lê o status atual do job."""
    volume.reload()
    status_file = os.path.join(JOBS_DIR, job_id, 'status.json')
    if not os.path.exists(status_file):
        return {'status': 'not_found'}
    with open(status_file) as f:
        return json.load(f)


@app.function(
    volumes={JOBS_DIR: volume},
    timeout=30,
)
def get_video(job_id: str, filename: str):
    """Retorna os bytes de um vídeo processado."""
    volume.reload()
    path = os.path.join(JOBS_DIR, job_id, 'output', filename)
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return f.read()


@app.function(
    volumes={JOBS_DIR: volume},
    timeout=30,
)
def cleanup_job(job_id: str):
    """Remove arquivos do job após download."""
    job_dir = os.path.join(JOBS_DIR, job_id)
    shutil.rmtree(job_dir, ignore_errors=True)
    volume.commit()
    return {'ok': True}
