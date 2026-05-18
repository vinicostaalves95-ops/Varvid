import os
import re
import json
import uuid
import random
import subprocess
import shutil
from itertools import product
from pathlib import Path

# ─── BLOCK DEFINITIONS ────────────────────────────────────────────────────────

BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']

BLOCK_ALIASES = {
    'hook':      ['hook', 'he1', 'he2', 'he3', 'he4', 'he5', 'h1', 'h2', 'h3'],
    'story':     ['story', 'storia', 'estoria'],
    'revelacao': ['revelac', 'revelação', 'revelacao', 'rev'],
    'prova':     ['prova', 'proof', 'resultado'],
    'cta':       ['cta', 'call'],
}

# Which blocks can be swapped between alternatives
SWAPPABLE_BLOCKS = {'hook', 'story', 'cta'}

# ─── TAKE PARSER ──────────────────────────────────────────────────────────────

def classify_take(filename: str) -> dict:
    """
    Parse a filename like H1_pt1.MOV, Story_pt3.MOV, Cta_2.MOV, Revelacao_pt1.MOV
    Returns: { block, variant, part, original_name }
    """
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

    # Extract variant number (H1, H2, H3, Cta_1, Cta_2...)
    variant_match = re.search(r'(?:he|h|hook|cta|story|rev|prova)[\s_]?(\d)', stem_clean)
    variant = int(variant_match.group(1)) if variant_match else 1

    # Extract part number (pt1, pt2, part1...)
    part_match = re.search(r'pt[\s_]?(\d+)', stem_clean)
    part = int(part_match.group(1)) if part_match else 1

    return {
        'block': block,
        'variant': variant,
        'part': part,
        'original_name': filename,
    }


def group_takes(file_list: list) -> dict:
    """
    Groups files into blocks and variants.
    Returns:
    {
      'hook': {
        1: ['/path/H1_pt1.MOV', '/path/H1_pt2.MOV'],
        2: ['/path/H2_pt1.MOV', '/path/H2_pt2.MOV'],
        3: ['/path/H3_pt1.MOV', '/path/H3_pt2.MOV'],
      },
      'story': {
        1: ['/path/Story_pt1.MOV', '/path/Story_pt2.MOV'],
        ...
      },
      ...
    }
    """
    groups = {}

    for filepath in file_list:
        filename = os.path.basename(filepath)
        info = classify_take(filename)
        b = info['block']
        v = info['variant']
        p = info['part']

        if b not in groups:
            groups[b] = {}
        if v not in groups[b]:
            groups[b][v] = []

        groups[b][v].append((p, filepath))

    # Sort parts within each variant
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
    """Build a summary dict for the UI"""
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
    """
    Generate `count` unique video combinations.
    Each combination = one variant chosen per swappable block + fixed blocks.
    Returns list of combos: [{ block: variant_number, ... }]
    """
    rng = random.Random(seed)

    # Build pool of choices per swappable block
    choices = {}
    for block in BLOCK_ORDER:
        if block not in groups:
            continue
        variant_keys = sorted(groups[block].keys())
        if block in SWAPPABLE_BLOCKS and len(variant_keys) > 1:
            choices[block] = variant_keys
        else:
            choices[block] = variant_keys  # even fixed blocks need a choice (just 1 option)

    # Generate all possible unique combos
    blocks_with_choices = [b for b in BLOCK_ORDER if b in choices]
    all_options = [choices[b] for b in blocks_with_choices]

    all_combos = list(product(*all_options))
    rng.shuffle(all_combos)

    # If we need more than possible unique combos, allow repeats with different micro-seed
    result = []
    for i in range(count):
        combo_tuple = all_combos[i % len(all_combos)]
        combo = {blocks_with_choices[j]: combo_tuple[j] for j in range(len(blocks_with_choices))}
        combo['_micro_seed'] = i  # for frame-level variation
        result.append(combo)

    return result


# ─── FFMPEG RENDERER ──────────────────────────────────────────────────────────

def render_variation(groups: dict, combo: dict, output_path: str, tmp_base: str) -> bool:
    """
    Renders one video variation from a combination.
    Applies micro-variations (zoom, frame trim) for fingerprint uniqueness.
    """
    rng = random.Random(combo['_micro_seed'] * 9973 + 1337)
    tmp_dir = os.path.join(tmp_base, f'render_{uuid.uuid4().hex[:8]}')
    os.makedirs(tmp_dir, exist_ok=True)

    seg_files = []

    try:
        for block in BLOCK_ORDER:
            if block not in combo:
                continue
            variant = combo[block]
            files = groups[block][variant]

            for part_idx, filepath in enumerate(files):
                duration = get_duration(filepath)
                if duration < 0.1:
                    continue

                seg_out = os.path.join(tmp_dir, f'{block}_{variant}_{part_idx:02d}.mp4')

                # Micro-variation decisions
                # 1. Trim a few frames from start (except very first segment)
                trim_start = 0.0
                is_first_seg = (block == BLOCK_ORDER[0] and part_idx == 0)
                if not is_first_seg:
                    trim_frames = rng.randint(1, 6)
                    trim_start = trim_frames / 30.0

                # 2. Trim a few frames from end
                trim_end = duration
                is_last_seg = (block == BLOCK_ORDER[-1] and part_idx == len(files) - 1)
                if not is_last_seg:
                    trim_frames_end = rng.randint(1, 3)
                    trim_end = duration - (trim_frames_end / 30.0)

                if trim_end <= trim_start + 0.1:
                    trim_end = trim_start + 0.1

                actual_duration = trim_end - trim_start

                # 3. Zoom on some segments (not first, not last)
                apply_zoom = (not is_first_seg and not is_last_seg and rng.random() < 0.3)
                zoom_factor = rng.uniform(1.04, 1.10) if apply_zoom else 1.0

                # Build ffmpeg command
                cmd = ['ffmpeg', '-y', '-ss', str(trim_start), '-t', str(actual_duration), '-i', filepath]

                vf_filters = []
                if zoom_factor > 1.0:
                    z = zoom_factor
                    w = int(1080 / z)
                    h = int(1920 / z)
                    x = int((1080 - w) / 2)
                    y = int((1920 - h) / 2)
                    vf_filters.append(f'crop={w}:{h}:{x}:{y},scale=1080:1920:flags=lanczos')

                if vf_filters:
                    cmd += ['-vf', ','.join(vf_filters)]
                    cmd += ['-c:v', 'libx264', '-preset', 'fast', '-crf', '22']
                else:
                    cmd += ['-c:v', 'libx264', '-preset', 'fast', '-crf', '22']

                cmd += [
                    '-c:a', 'aac', '-ar', '44100', '-ac', '2',
                    '-avoid_negative_ts', 'make_zero',
                    '-pix_fmt', 'yuv420p',
                    seg_out
                ]

                r = subprocess.run(cmd, capture_output=True)
                if r.returncode == 0 and os.path.exists(seg_out):
                    seg_files.append(seg_out)

        if not seg_files:
            return False

        # Concat all segments
        concat_list = os.path.join(tmp_dir, 'concat.txt')
        with open(concat_list, 'w') as f:
            for sf in seg_files:
                f.write(f"file '{sf}'\n")

        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0', '-i', concat_list,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
            '-c:a', 'aac', '-ar', '44100', '-ac', '2',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── HIGH-LEVEL JOB RUNNER ────────────────────────────────────────────────────

def run_job(job: dict, file_list: list, count: int, output_dir: str):
    """Main job runner — called in a thread"""
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
