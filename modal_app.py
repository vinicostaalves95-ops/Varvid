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
    .apt_install("ffmpeg", "wget", "fontconfig", "libgl1", "libglib2.0-0")
    .pip_install("requests", "numpy")
    .pip_install("mediapipe==0.10.9", "opencv-python-headless")
    .run_commands(
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
    'story':     ['story', 'historia', 'estoria'],
    'revelacao': ['revelac', 'revelação', 'revelacao', 'rev'],
    'prova':     ['prova', 'proof', 'resultado'],
    'cta':       ['cta', 'call'],
}

TARGET_W = 1080
TARGET_H = 1920
FONT_PATH = '/usr/share/fonts/poppins/Poppins-ExtraBold.ttf'
TEXT_Y_TOP = 260


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


def detect_face_center(filepath):
    try:
        import cv2
        import mediapipe as mp

        duration = get_duration(filepath)
        if duration < 0.1:
            return None

        mid = duration / 2
        tmp_frame = f'/tmp/face_{uuid.uuid4().hex[:8]}.jpg'
        cmd = [
            'ffmpeg', '-y', '-ss', str(mid), '-i', filepath,
            '-frames:v', '1', '-q:v', '2', tmp_frame
        ]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0 or not os.path.exists(tmp_frame):
            return None

        img = cv2.imread(tmp_frame)
        os.remove(tmp_frame)
        if img is None:
            return None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_face = mp.solutions.face_detection
        with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as detector:
            results = detector.process(img_rgb)

        if not results.detections:
            return None

        best = max(results.detections, key=lambda d: d.location_data.relative_bounding_box.width)
        bb = best.location_data.relative_bounding_box
        cx = max(0.1, min(0.9, bb.xmin + bb.width / 2))
        cy = max(0.1, min(0.9, bb.ymin + bb.height / 2))
        return (cx, cy)

    except Exception as e:
        print(f"[FACE] Erro: {e}")
        return None


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


def wrap_text(text, max_chars=24):
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


def build_headline_filter(text, style_seed, headline_duration, font_path=FONT_PATH):
    if not text or not text.strip():
        return None

    dark_style   = (style_seed % 2 == 1)
    bg_color     = '0x000000E6' if dark_style else '0xFFFFFFEE'
    font_color   = 'white'      if dark_style else 'black'
    font_size    = 52
    pad_x        = 36
    pad_y        = 18
    line_spacing = 10

    lines     = wrap_text(text.strip(), max_chars=24)
    num_lines = len(lines)
    line_h    = font_size + line_spacing
    box_h     = pad_y * 2 + line_h * num_lines - line_spacing

    max_chars_line = max(len(l) for l in lines)
    estimated_w = max_chars_line * 28 + pad_x * 2
    box_w = min(estimated_w, TARGET_W - 80)
    box_w = max(box_w, 300)
    box_x = (TARGET_W - box_w) // 2
    box_y = TEXT_Y_TOP
    time_disable = str(float(headline_duration))

    filters = []
    filters.append(
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:"
        f"color={bg_color}:t=fill:"
        f"enable='between(t,0,{time_disable})'"
    )
    for i, line in enumerate(lines):
        line_escaped = line.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
        text_y = box_y + pad_y + i * line_h
        filters.append(
            f"drawtext=fontfile='{font_path}':"
            f"text='{line_escaped}':"
            f"fontcolor={font_color}:"
            f"fontsize={font_size}:"
            f"x=(w-text_w)/2:"
            f"y={text_y}:"
            f"enable='between(t,0,{time_disable})'"
        )
    return ','.join(filters)


def build_zoom_filter(zoom_factor, face_center=None):
    z = zoom_factor
    w = int(TARGET_W / z)
    h = int(TARGET_H / z)

    if face_center:
        cx_px = int(face_center[0] * TARGET_W)
        cy_px = int(face_center[1] * TARGET_H)
        x = max(0, min(TARGET_W - w, cx_px - w // 2))
        y = max(0, min(TARGET_H - h, cy_px - h // 2))
    else:
        x = (TARGET_W - w) // 2
        y = (TARGET_H - h) // 2

    return f'crop={w}:{h}:{x}:{y},scale={TARGET_W}:{TARGET_H}:flags=lanczos,format=yuv420p'


def normalize_segment(src, dst, trim_start, duration,
                      zoom_factor=1.0, face_center=None,
                      headline_filter=None,
                      color_params=None,
                      pitch_shift=0.0):
    """
    Renderiza um segmento com:
    - zoom estático centrado no rosto (se detectado)
    - ajuste de cor sutil (eq + colorchannelmixer)
    - pitch shift sutil no áudio
    - headline overlay (só no primeiro segmento)
    """
    vf_parts = []

    # 1. Escala / zoom
    if zoom_factor > 1.0:
        vf_parts.append(build_zoom_filter(zoom_factor, face_center))
    else:
        vf_parts.append(
            f'scale={TARGET_W}:{TARGET_H}:'
            f'force_original_aspect_ratio=decrease,'
            f'pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,'
            f'format=yuv420p'
        )

    # 2. Ajuste de cor sutil — temperatura + brilho + saturação
    if color_params:
        brightness = color_params.get('brightness', 0.0)   # -0.03 a +0.03
        contrast   = color_params.get('contrast', 1.0)     # 0.97 a 1.03
        saturation = color_params.get('saturation', 1.0)   # 0.97 a 1.03
        # Temperatura: r_gain e b_gain opostos (quente = +r/-b, frio = -r/+b)
        r_gain = color_params.get('r_gain', 1.0)           # 0.97 a 1.03
        b_gain = color_params.get('b_gain', 1.0)           # 0.97 a 1.03

        vf_parts.append(
            f'eq=brightness={brightness:.3f}:'
            f'contrast={contrast:.3f}:'
            f'saturation={saturation:.3f}'
        )
        # Temperatura via colorchannelmixer (r e b channels)
        if abs(r_gain - 1.0) > 0.001 or abs(b_gain - 1.0) > 0.001:
            vf_parts.append(
                f'colorchannelmixer='
                f'rr={r_gain:.3f}:gg=1.000:bb={b_gain:.3f}'
            )

    # 3. Headline
    if headline_filter:
        vf_parts.append(headline_filter)

    vf = ','.join(vf_parts)

    # Áudio: pitch shift via atempo + asetrate (mantém duração, muda pitch)
    # pitch_shift em semitons — ex: 0.5 semitom = ratio 2^(0.5/12) ≈ 1.029
    af_parts = []
    if abs(pitch_shift) > 0.01:
        ratio = 2 ** (pitch_shift / 12.0)
        # asetrate muda o pitch; atempo corrige a velocidade de volta
        af_parts.append(f'asetrate=44100*{ratio:.4f},atempo={1/ratio:.4f}')
    af = ','.join(af_parts) if af_parts else None

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(trim_start),
        '-t', str(duration),
        '-i', src,
        '-vf', vf,
    ]
    if af:
        cmd += ['-af', af]
    cmd += [
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
    if r.returncode != 0:
        print(f"[FFMPEG_ERR] {r.stderr.decode()[-500:]}")
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


def render_variation(groups, combo, output_path, tmp_dir,
                     headline_text='', headline_duration=3,
                     face_cache=None):
    rng = random.Random(combo['_micro_seed'] * 9973 + 1337)
    os.makedirs(tmp_dir, exist_ok=True)
    seg_files = []
    takes_used = {}

    headline_filter = None
    if headline_text and headline_text.strip():
        headline_filter = build_headline_filter(
            headline_text,
            style_seed=combo['_micro_seed'],
            headline_duration=headline_duration
        )

    # Parâmetros de cor — únicos por vídeo, aplicados em todos os segmentos
    # Sutis: ±2% em cada canal
    color_params = {
        'brightness': rng.uniform(-0.02, 0.02),
        'contrast':   rng.uniform(0.98, 1.02),
        'saturation': rng.uniform(0.98, 1.02),
        'r_gain':     rng.uniform(0.98, 1.02),
        'b_gain':     rng.uniform(0.98, 1.02),
    }

    # Pitch shift — único por vídeo: ±0.5 semitom máximo
    pitch_shift = rng.uniform(-0.5, 0.5)

    print(f"[COLOR] brightness={color_params['brightness']:.3f} "
          f"contrast={color_params['contrast']:.3f} "
          f"sat={color_params['saturation']:.3f} "
          f"r={color_params['r_gain']:.3f} b={color_params['b_gain']:.3f}")
    print(f"[PITCH] {pitch_shift:+.2f} semitons")

    all_segs = []
    for block in BLOCK_ORDER:
        if block not in combo:
            continue
        for part_idx, filepath in enumerate(groups[block][combo[block]]):
            all_segs.append((block, part_idx, filepath))
            if block not in takes_used:
                takes_used[block] = []
            fname = os.path.basename(filepath)
            if fname not in takes_used[block]:
                takes_used[block].append(fname)

    total = len(all_segs)

    # Variação de escala entre segmentos — alterna plano aberto/fechado
    # Escala base por segmento: alguns em 1.0, alguns em 1.04-1.06
    scale_levels = []
    for i in range(total):
        if i == 0 or i == total - 1:
            scale_levels.append(1.0)  # hook e CTA sempre em escala normal
        else:
            # Alterna entre aberto e fechado para criar ritmo nos cortes
            scale_levels.append(rng.choice([1.0, rng.uniform(1.03, 1.06)]))

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

        zoom_factor = scale_levels[i]
        face_center = face_cache.get(filepath) if (face_cache and zoom_factor > 1.0) else None

        seg_out = os.path.join(tmp_dir, f'seg_{i:03d}.mp4')
        seg_headline = headline_filter if is_first else None

        ok = normalize_segment(
            filepath, seg_out,
            trim_start, actual_duration,
            zoom_factor=zoom_factor,
            face_center=face_center,
            headline_filter=seg_headline,
            color_params=color_params,
            pitch_shift=pitch_shift
        )

        if ok:
            seg_files.append(seg_out)
        else:
            print(f"[WARN] Falhou segmento {i}: {filepath}")

    if not seg_files:
        return False, {}
    if len(seg_files) == 1:
        shutil.move(seg_files[0], output_path)
        return os.path.exists(output_path), takes_used
    ok = concat_segments(seg_files, output_path)
    return ok, takes_used


@app.function(timeout=1800, memory=2048)
def process_job_http(job_id: str, file_urls: list, output_base_url: str,
                     count: int, headline_text: str = '',
                     headline_duration: int = 3):
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
                    with requests.get(url, timeout=120, stream=True) as r:
                        if r.status_code == 200:
                            with open(local_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=1024*1024):
                                    if chunk:
                                        f.write(chunk)
                            file_list.append(local_path)
                            downloaded = True
                            break
                except Exception as e:
                    print(f"[ERR] {fname}: {e}")
            if not downloaded:
                print(f"[SKIP] {fname}")

        if not file_list:
            return {'error': 'no files downloaded'}

        groups = group_takes(file_list)
        print(f"[INFO] Blocos: {list(groups.keys())}")

        # Análise de rostos — uma vez por take
        print("[FACE] Analisando rostos...")
        face_cache = {}
        for filepath in file_list:
            result = detect_face_center(filepath)
            face_cache[filepath] = result
            status = f"({result[0]:.2f}, {result[1]:.2f})" if result else "não detectado"
            print(f"[FACE] {os.path.basename(filepath)}: {status}")

        combos = build_combinations(groups, count)
        output_files = []

        for i, combo in enumerate(combos):
            print(f"[RENDER] {i+1}/{count}")
            out_path = os.path.join(output_dir, f'variation_{i+1:02d}.mp4')
            tmp_dir  = os.path.join(tmp_base, f'tmp_{i}')

            success, takes_used = render_variation(
                groups, combo, out_path, tmp_dir,
                headline_text=headline_text,
                headline_duration=headline_duration,
                face_cache=face_cache
            )
            shutil.rmtree(tmp_dir, ignore_errors=True)

            if success and os.path.exists(out_path):
                fname = f'variation_{i+1:02d}.mp4'

                # Metadata com retry
                meta = json.dumps(takes_used)
                for attempt in range(4):
                    try:
                        r = requests.put(
                            f"{output_base_url}/meta/{fname}",
                            data=meta.encode(),
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )
                        if r.status_code == 200:
                            break
                    except Exception as e:
                        print(f"[WARN] meta attempt {attempt+1}: {e}")
                        time.sleep(2 * (attempt + 1))

                # Upload do vídeo com retry robusto
                with open(out_path, 'rb') as f:
                    video_data = f.read()
                uploaded = False
                for attempt in range(5):
                    try:
                        if attempt > 0:
                            print(f"[RETRY] {fname} tentativa {attempt+1}")
                            time.sleep(3 * attempt)
                        resp = requests.put(
                            f"{output_base_url}/{fname}",
                            data=video_data,
                            headers={'Content-Type': 'video/mp4'},
                            timeout=300
                        )
                        if resp.status_code == 200:
                            output_files.append(fname)
                            print(f"[OK] {fname} ({len(video_data)//1024//1024}MB)")
                            uploaded = True
                            break
                        else:
                            print(f"[WARN] {fname} status {resp.status_code}")
                    except Exception as e:
                        print(f"[ERR] {fname} attempt {attempt+1}: {e}")

                if not uploaded:
                    print(f"[ERR] Falhou upload {fname} após 5 tentativas")
                os.remove(out_path)
            else:
                print(f"[ERR] Render falhou render {i+1}")

        return {'status': 'done', 'files': output_files, 'count': len(output_files)}

    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)
