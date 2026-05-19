import os
import re
import json
import uuid
import random
import subprocess
import shutil
from itertools import product
from pathlib import Path

# Setup static ffmpeg
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

# ─── BLOCK DEFINITIONS ────────────────────────────────────────────────────────

BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']

BLOCK_ALIASES = {
    'hook':     ['hook', 'he1', 'he2', 'he3', 'he4', 'he5', 'h1', 'h2', 'h3'],
    'story':    ['story', 'storia', 'estoria'],
    'revelacao':['revelac', 'revelação', 'revelacao', 'rev'],
    'prova':    ['prova', 'proof', 'resultado'],
    'cta':      ['cta', 'call'],
}

SWAPPABLE_BLOCKS = {'hook', 'story', 'cta'}

# ─── TAKE PARSER ──────────────────────────────────────────────────────────────

def classify_take(filename: str) -> dict:
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
        return {'block': 'unknown', 'variant': 1, 'part': 1, 'original_name': filename}

    variant_match = re.search(r'(?:he|h|hook|cta|story|rev|prova)[\s_]?(\d)', stem_clean)
    variant = int(variant_match.group(1)) if variant_match else 1

    part_match = re.search(r'pt[\s_]?(\d+)', stem_clean)
    part = int(part_match.group(1)) if part_match else 1

    return {'block': block, 'variant': variant, 'part': part, 'original_name': filename}


def group_takes(file_list: list) -> dict:
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


def get_duration(filepath: str) -> float:
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        return float(data['format']['duration'])
    except:
        return 0.0


def summarize_groups(groups: dict) -> dict:
    summary = {}
    for block in BLOCK_ORDER:
        if block not in groups:
            continue
        variants = []
        for v_num, files in sorted(groups[block].items()):
            total_dur = sum(get_duration(f) for f in files)
            variants.append({
                'variant': v_num,
                'files': [os.path.basename(f) for f in files],
                'duration': round(total_dur, 2),
                'parts': len(files),
            })
        summary[block] = variants
    return summary


# ─── COMBINATION ENGINE ───────────────────────────────────────────────────────

def build_combinations(groups: dict, count: int, seed: int = 42) -> list:
    rng = random.Random(seed)

    choices = {}
    for block in BLOCK_ORDER:
        if block not in groups:
            continue
        variant_keys = sorted(groups[block].keys())
        choices[block] = variant_keys

    blocks_with_choices = [b for b in BLOCK_ORDER if b in choices]
    all_options = [choices[b] for b in blocks_with_choices]
    all_combos = list(product(*all_options))
    rng.shuffle(all_combos)

    result = []
    for i in range(count):
        combo_tuple = all_combos[i % len(all_combos)]
        combo = {blocks_with_choices[j]: combo_tuple[j] for j in range(len(blocks_with_choices))}
        combo['_micro_seed'] = i
        result.append(combo)

    return result


# ─── FFMPEG RENDERER ──────────────────────────────────────────────────────────

def _normalize_to_mp4(src: str, dst: str) -> bool:
    """
    Re-encode a single file to a standard H264/AAC MP4 with fixed resolution.
    Used ONLY when the segment needs a zoom filter applied.
    Uses ultrafast + low quality to minimize RAM.
    """
    cmd = [
        'ffmpeg', '-y', '-i', src,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '35',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        '-pix_fmt', 'yuv420p',
        '-threads', '1',
        dst
    ]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and os.path.exists(dst)


def _trim_and_copy(src: str, dst: str, trim_start: float, duration: float) -> bool:
    """
    Trim a segment using stream copy (no re-encode = very low RAM).
    """
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(trim_start),
        '-t', str(duration),
        '-i', src,
        '-c', 'copy',
        '-avoid_negative_ts', 'make_zero',
        dst
    ]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and os.path.exists(dst)


def _trim_and_zoom(src: str, dst: str, trim_start: float, duration: float, zoom_factor: float) -> bool:
    """
    Trim + apply zoom crop, re-encode only this segment.
    """
    z = zoom_factor
    # Assume 1080x1920 (portrait). Crop center then scale back.
    w = int(1080 / z)
    h = int(1920 / z)
    x = int((1080 - w) / 2)
    y = int((1920 - h) / 2)
    vf = f'crop={w}:{h}:{x}:{y},scale=1080:1920:flags=bilinear'

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(trim_start),
        '-t', str(duration),
        '-i', src,
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '35',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        '-pix_fmt', 'yuv420p',
        '-threads', '1',
        '-avoid_negative_ts', 'make_zero',
        dst
    ]
    r = subprocess.run(cmd, capture_output=True)
    return r.returncode == 0 and os.path.exists(dst)


def _concat_segments(seg_files: list, output_path: str) -> bool:
    """
    Concatenate segments using stream copy (no re-encode).
    If files have mixed codecs/params this can fail — fallback to re-encode concat.
    """
    tmp_list = output_path + '.concat.txt'
    with open(tmp_list, 'w') as f:
        for sf in seg_files:
            f.write(f"file '{sf}'\n")

    # Try stream copy first (fast, low RAM)
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0', '-i', tmp_list,
        '-c', 'copy',
        '-movflags', '+faststart',
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True)

    if r.returncode != 0 or not os.path.exists(output_path):
        # Fallback: re-encode concat (slower but safe for mixed inputs)
        cmd2 = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0', '-i', tmp_list,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '35',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-pix_fmt', 'yuv420p',
            '-threads', '1',
            '-movflags', '+faststart',
            output_path
        ]
        r2 = subprocess.run(cmd2, capture_output=True)
        os.remove(tmp_list)
        return r2.returncode == 0 and os.path.exists(output_path)

    os.remove(tmp_list)
    return True


def render_variation(groups: dict, combo: dict, output_path: str, tmp_base: str) -> bool:
    rng = random.Random(combo['_micro_seed'] * 9973 + 1337)

    tmp_dir = os.path.join(tmp_base, f'render_{uuid.uuid4().hex[:8]}')
    os.makedirs(tmp_dir, exist_ok=True)

    seg_files = []

    try:
        seg_idx = 0
        all_segs = []
        for block in BLOCK_ORDER:
            if block not in combo:
                continue
            variant = combo[block]
            files = groups[block][variant]
            for part_idx, filepath in enumerate(files):
                all_segs.append((block, part_idx, filepath, len(files)))

        total_segs = len(all_segs)

        for i, (block, part_idx, filepath, block_total) in enumerate(all_segs):
            duration = get_duration(filepath)
            if duration < 0.1:
                continue

            seg_out = os.path.join(tmp_dir, f'seg_{i:03d}.mp4')

            is_first = (i == 0)
            is_last = (i == total_segs - 1)

            # Micro-trim decisions
            trim_start = 0.0
            if not is_first:
                trim_frames = rng.randint(1, 5)
                trim_start = trim_frames / 30.0

            trim_end = duration
            if not is_last:
                trim_frames_end = rng.randint(1, 3)
                trim_end = duration - (trim_frames_end / 30.0)

            if trim_end <= trim_start + 0.1:
                trim_end = trim_start + 0.1

            actual_duration = trim_end - trim_start

            # Zoom: only on middle segments, 25% chance
            apply_zoom = (not is_first and not is_last and rng.random() < 0.25)
            zoom_factor = rng.uniform(1.04, 1.08) if apply_zoom else 1.0

            if apply_zoom:
                ok = _trim_and_zoom(filepath, seg_out, trim_start, actual_duration, zoom_factor)
            else:
                ok = _trim_and_copy(filepath, seg_out, trim_start, actual_duration)

            if ok:
                seg_files.append(seg_out)

        if not seg_files:
            return False

        if len(seg_files) == 1:
            # Single segment — just move it
            shutil.move(seg_files[0], output_path)
            return os.path.exists(output_path)

        return _concat_segments(seg_files, output_path)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── HIGH-LEVEL JOB RUNNER ────────────────────────────────────────────────────

def run_job(job: dict, file_list: list, count: int, output_dir: str):
    try:
        job['status'] = 'analyzing'
        job['progress'] = 5

        groups = group_takes(file_list)
        job['groups'] = groups
        job['summary'] = summarize_groups(groups)
        job['progress'] = 15

        job['status'] = 'planning'
        combos = build_combinations(groups, count)
        job['total'] = count
        job['completed'] = 0
        job['progress'] = 20

        job['status'] = 'rendering'
        tmp_base = os.path.join(output_dir, 'tmp')
        os.makedirs(tmp_base, exist_ok=True)

        output_files = []
        for i, combo in enumerate(combos):
            out_path = os.path.join(output_dir, f'variation_{i+1:02d}.mp4')
            success = render_variation(groups, combo, out_path, tmp_base)

            if success:
                output_files.append(out_path)

            combo_desc = ' → '.join([
                f"{b.upper()}{'v'+str(combo[b]) if b in SWAPPABLE_BLOCKS else ''}"
                for b in BLOCK_ORDER if b in combo
            ])
            job['last_combo'] = combo_desc
            job['completed'] = i + 1
            job['progress'] = 20 + int((i + 1) / count * 75)

        shutil.rmtree(tmp_base, ignore_errors=True)

        job['status'] = 'done'
        job['progress'] = 100
        job['files'] = output_files
        job['count'] = len(output_files)

    except Exception as e:
        import traceback
        job['status'] = 'error'
        job['error'] = str(e)
        job['traceback'] = traceback.format_exc()
