"""
VarVid — função de RENDER no Modal (produção)

O app web (local_app.py, no modo RENDER_BACKEND=modal, hospedado no Render)
despacha os jobs pra cá. Esta função:
  1. baixa os takes das URLs recebidas (RENDER_URL/files/<job>/<nome>),
  2. renderiza as variações (mesma lógica da versão local — remix de blocos
     OU modo vídeo único), e
  3. devolve cada vídeo pronto via PUT em RENDER_URL/output/<job>/<arquivo>,
     mais o takes_map e um marcador _done em RENDER_URL/output/<job>/meta/...

Deploy:  modal deploy modal_app.py
O nome do app ("varvid") tem que bater com MODAL_APP_NAME no Render.
"""

import modal

APP_NAME = "varvid"

# ─── IMAGEM (ffmpeg + libs de rosto + fonte do headline) ──────────────────────
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "curl", "fonts-dejavu-core")
    .pip_install(
        "opencv-python-headless>=4.8",
        "mediapipe==0.10.9",
        "numpy<2",
    )
    .run_commands(
        "mkdir -p /usr/share/fonts/poppins",
        "curl -fsSL -o /usr/share/fonts/poppins/Poppins-ExtraBold.ttf "
        "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf || true",
    )
)

app = modal.App(APP_NAME)


# ══════════════════════════════════════════════════════════════════════════════
#  Tudo abaixo roda DENTRO do container do Modal (a imagem tem ffmpeg + libs).
#  É a mesma lógica de render da versão local, adaptada pra usar /tmp.
# ══════════════════════════════════════════════════════════════════════════════

import os
import re
import json
import uuid
import random
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path
from itertools import product as iterproduct

TARGET_W = 1080
TARGET_H = 1920
TEXT_Y_TOP = 260

BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']
BLOCK_ALIASES = {
    'hook':      ['hook', 'he1', 'he2', 'he3', 'he4', 'he5', 'h1', 'h2', 'h3'],
    'story':     ['story', 'historia', 'estoria', 'storia'],
    'revelacao': ['revelac', 'revelação', 'revelacao', 'rev'],
    'prova':     ['prova', 'proof', 'resultado'],
    'cta':       ['cta', 'call'],
}

_TMP = tempfile.gettempdir()


def _find_font():
    for c in ['/usr/share/fonts/poppins/Poppins-ExtraBold.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.exists(c):
            return c
    return None


FONT_PATH = _find_font()


def _face_available():
    try:
        import cv2  # noqa
        import mediapipe  # noqa
        return True
    except Exception:
        return False


# ─── PARSER DE TAKES ──────────────────────────────────────────────────────────

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
        info = classify_take(os.path.basename(filepath))
        b, v, p = info['block'], info['variant'], info['part']
        groups.setdefault(b, {}).setdefault(v, []).append((p, filepath))
    for block in groups:
        for variant in groups[block]:
            groups[block][variant].sort(key=lambda x: x[0])
            groups[block][variant] = [fp for _, fp in groups[block][variant]]
    return groups


def get_duration(filepath):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath],
            capture_output=True, text=True)
        return float(json.loads(result.stdout)['format']['duration'])
    except Exception:
        return 0.0


def get_fps(filepath):
    try:
        r = subprocess.run(
            ['ffprobe', '-v', '0', '-select_streams', 'v:0',
             '-show_entries', 'stream=r_frame_rate', '-of', 'default=nk=1:nw=1', filepath],
            capture_output=True, text=True)
        num, den = r.stdout.strip().split('/')
        fps = float(num) / float(den)
        return fps if fps > 0 else 30.0
    except Exception:
        return 30.0


# ─── FACE DETECT (opcional) ───────────────────────────────────────────────────

def detect_face_center(filepath):
    if not _face_available():
        return None
    try:
        import cv2
        import mediapipe as mp
        duration = get_duration(filepath)
        if duration < 0.1:
            return None
        mid = duration / 2
        tmp_frame = os.path.join(_TMP, f'face_{uuid.uuid4().hex[:8]}.jpg')
        cmd = ['ffmpeg', '-y', '-ss', str(mid), '-i', filepath,
               '-frames:v', '1', '-q:v', '2', tmp_frame]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0 or not os.path.exists(tmp_frame):
            return None
        img = cv2.imread(tmp_frame)
        os.remove(tmp_frame)
        if img is None:
            return None
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_face = mp.solutions.face_detection
        with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as det:
            results = det.process(img_rgb)
        if not results.detections:
            return None
        best = max(results.detections, key=lambda d: d.location_data.relative_bounding_box.width)
        bb = best.location_data.relative_bounding_box
        cx = max(0.1, min(0.9, bb.xmin + bb.width / 2))
        cy = max(0.1, min(0.9, bb.ymin + bb.height / 2))
        return (cx, cy)
    except Exception as e:
        print(f"[FACE] erro: {e}")
        return None


# ─── COMBINAÇÕES ──────────────────────────────────────────────────────────────

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


# ─── HEADLINE ─────────────────────────────────────────────────────────────────

def wrap_text(text, max_chars=24):
    words, lines, current = text.split(), [], ''
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


def build_headline_filter(text, style_seed, headline_duration):
    if not text or not text.strip() or not FONT_PATH:
        return None
    dark_style = (style_seed % 2 == 1)
    bg_color   = '0x000000E6' if dark_style else '0xFFFFFFEE'
    font_color = 'white'      if dark_style else 'black'
    font_size, pad_x, pad_y, line_spacing = 52, 36, 18, 10

    lines = wrap_text(text.strip(), max_chars=24)
    line_h = font_size + line_spacing
    box_h  = pad_y * 2 + line_h * len(lines) - line_spacing
    box_w  = min(max(len(l) for l in lines) * 28 + pad_x * 2, TARGET_W - 80)
    box_w  = max(box_w, 300)
    box_x  = (TARGET_W - box_w) // 2
    box_y  = TEXT_Y_TOP
    time_disable = str(float(headline_duration))

    filters = [
        f"drawbox=x={box_x}:y={box_y}:w={box_w}:h={box_h}:"
        f"color={bg_color}:t=fill:enable='between(t,0,{time_disable})'"
    ]
    for i, line in enumerate(lines):
        esc = line.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
        text_y = box_y + pad_y + i * line_h
        filters.append(
            f"drawtext=fontfile='{FONT_PATH}':text='{esc}':fontcolor={font_color}:"
            f"fontsize={font_size}:x=(w-text_w)/2:y={text_y}:"
            f"enable='between(t,0,{time_disable})'"
        )
    return ','.join(filters)


def build_zoom_filter(zoom_factor, face_center=None):
    z = zoom_factor
    w = int(TARGET_W / z) & ~1
    h = int(TARGET_H / z) & ~1
    w = max(2, min(w, TARGET_W))
    h = max(2, min(h, TARGET_H))
    if face_center:
        cx_px = int(face_center[0] * TARGET_W)
        cy_px = int(face_center[1] * TARGET_H)
        x = max(0, min(TARGET_W - w, cx_px - w // 2))
        y = max(0, min(TARGET_H - h, cy_px - h // 2))
    else:
        x = (TARGET_W - w) // 2
        y = (TARGET_H - h) // 2
    x &= ~1
    y &= ~1
    return (f'scale={TARGET_W}:{TARGET_H}:flags=lanczos,'
            f'crop={w}:{h}:{x}:{y},'
            f'scale={TARGET_W}:{TARGET_H}:flags=lanczos,format=yuv420p')


# ─── RENDER DE SEGMENTO ───────────────────────────────────────────────────────

def normalize_segment(src, dst, trim_start, duration,
                      zoom_factor=1.0, face_center=None, headline_filter=None):
    vf_parts = []
    if zoom_factor > 1.0:
        vf_parts.append(build_zoom_filter(zoom_factor, face_center))
    else:
        vf_parts.append(
            f'scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease:flags=lanczos,'
            f'pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p'
        )
    if headline_filter:
        vf_parts.append(headline_filter)
    vf = ','.join(vf_parts)

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(trim_start), '-t', str(duration), '-i', src,
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2', '-b:a', '128k',
        '-threads', '2', '-avoid_negative_ts', 'make_zero',
        '-movflags', '+faststart', dst,
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
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
           '-c', 'copy', '-movflags', '+faststart', output_path]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not os.path.exists(output_path):
        cmd2 = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-c:a', 'aac', '-ar', '44100', '-ac', '2',
                '-pix_fmt', 'yuv420p', '-threads', '2',
                '-movflags', '+faststart', output_path]
        r = subprocess.run(cmd2, capture_output=True)
    if os.path.exists(concat_list):
        os.remove(concat_list)
    return os.path.exists(output_path)


def render_variation(groups, combo, output_path, tmp_dir,
                     headline_text='', headline_duration=3, face_cache=None):
    rng = random.Random(combo['_micro_seed'] * 9973 + 1337)
    os.makedirs(tmp_dir, exist_ok=True)
    seg_files, takes_used = [], {}

    headline_filter = None
    if headline_text and headline_text.strip():
        headline_filter = build_headline_filter(
            headline_text, style_seed=combo['_micro_seed'],
            headline_duration=headline_duration)

    all_segs = []
    for block in BLOCK_ORDER:
        if block not in combo:
            continue
        for part_idx, filepath in enumerate(groups[block][combo[block]]):
            all_segs.append((block, part_idx, filepath))
            fname = os.path.basename(filepath)
            takes_used.setdefault(block, [])
            if fname not in takes_used[block]:
                takes_used[block].append(fname)

    total = len(all_segs)
    scale_levels = []
    for i in range(total):
        if i == 0 or i == total - 1:
            scale_levels.append(1.0)
        else:
            scale_levels.append(rng.choice([1.0, rng.uniform(1.03, 1.06)]))

    for i, (block, part_idx, filepath) in enumerate(all_segs):
        duration = get_duration(filepath)
        if duration < 0.1:
            continue
        is_first, is_last = (i == 0), (i == total - 1)
        trim_start = 0.0 if is_first else rng.randint(1, 4) / 30.0
        trim_end   = duration if is_last else duration - (rng.randint(1, 3) / 30.0)
        if trim_end <= trim_start + 0.1:
            trim_end = trim_start + 0.5
        actual_duration = trim_end - trim_start

        zoom_factor = scale_levels[i]
        face_center = face_cache.get(filepath) if (face_cache and zoom_factor > 1.0) else None
        seg_out = os.path.join(tmp_dir, f'seg_{i:03d}.mp4')
        seg_headline = headline_filter if is_first else None

        if normalize_segment(filepath, seg_out, trim_start, actual_duration,
                             zoom_factor=zoom_factor, face_center=face_center,
                             headline_filter=seg_headline):
            seg_files.append(seg_out)
        else:
            print(f"[WARN] falhou segmento {i}: {filepath}")

    if not seg_files:
        return False, {}
    if len(seg_files) == 1:
        shutil.move(seg_files[0], output_path)
        return os.path.exists(output_path), takes_used
    return concat_segments(seg_files, output_path), takes_used


# ─── MODO VÍDEO ÚNICO ─────────────────────────────────────────────────────────

def render_single_variation(src, dst, tmp_dir, micro_seed,
                            headline_text='', headline_duration=3):
    rng = random.Random(micro_seed * 9973 + 1337)
    os.makedirs(tmp_dir, exist_ok=True)

    duration = get_duration(src)
    fps = get_fps(src)
    if duration < 0.3:
        return False

    trim_start = rng.randint(1, 4) / fps
    end_cut    = rng.randint(1, 3) / fps
    new_duration = duration - trim_start - end_cut
    if new_duration < 0.3:
        trim_start, new_duration = 0.0, duration

    zoom = rng.uniform(1.02, 1.06)

    headline_filter = None
    if headline_text and headline_text.strip():
        headline_filter = build_headline_filter(
            headline_text, style_seed=micro_seed, headline_duration=headline_duration)

    return normalize_segment(
        src, dst, trim_start, new_duration,
        zoom_factor=zoom, face_center=None, headline_filter=headline_filter)


# ─── RUNNERS (chamam os PUTs de volta pro app web) ────────────────────────────

def _run_remix(files, out_dir, count, headline_text, headline_duration, put_file):
    groups = group_takes(files)
    print("[MODAL] blocos:", list(groups.keys()))
    face_cache = {}
    if _face_available():
        print("[MODAL] analisando rostos...")
        for fp in files:
            face_cache[fp] = detect_face_center(fp)
    combos = build_combinations(groups, count)
    takes_map = {}
    for i, combo in enumerate(combos):
        fname = f"variation_{i+1:02d}.mp4"
        out_path = os.path.join(out_dir, fname)
        tmp_dir = os.path.join(out_dir, f"tmp_{i}")
        print(f"[MODAL][remix] {i+1}/{count}")
        ok, takes_used = render_variation(
            groups, combo, out_path, tmp_dir,
            headline_text=headline_text, headline_duration=headline_duration,
            face_cache=face_cache)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if ok and os.path.exists(out_path):
            put_file(fname, out_path)
            takes_map[fname] = takes_used
        else:
            print(f"[MODAL] falhou variação {i+1}")
    return takes_map


def _run_single(files, out_dir, count, headline_text, headline_duration, put_file):
    if not files:
        raise RuntimeError("nenhum vídeo enviado")
    files = sorted(files)
    for i in range(count):
        src = files[i % len(files)]
        fname = f"variation_{i+1:02d}.mp4"
        out_path = os.path.join(out_dir, fname)
        tmp_dir = os.path.join(out_dir, f"tmp_{i}")
        print(f"[MODAL][single] {i+1}/{count} <- {os.path.basename(src)}")
        ok = render_single_variation(
            src, out_path, tmp_dir, micro_seed=i,
            headline_text=headline_text, headline_duration=headline_duration)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        if not (ok and os.path.exists(out_path)):
            print(f"[MODAL] falhou variação {i+1}")
            continue
        put_file(fname, out_path)
    return {}


# ─── FUNÇÃO PRINCIPAL (o app web dá spawn nesta) ──────────────────────────────

@app.function(image=image, timeout=1800, memory=2048, cpu=2.0)
def process_job_http(job_id, file_urls, output_base_url, count,
                     headline_text="", headline_duration=3,
                     mode="remix", callback_secret=""):
    workdir = tempfile.mkdtemp(prefix=f"varvid_{job_id}_")
    takes_dir = os.path.join(workdir, "takes")
    out_dir = os.path.join(workdir, "out")
    os.makedirs(takes_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    def _with_token(url):
        if callback_secret and "token=" not in url:
            url += ("&" if "?" in url else "?") + "token=" + urllib.parse.quote(callback_secret)
        return url

    def _put(url, data, ctype):
        req = urllib.request.Request(_with_token(url), data=data, method="PUT",
                                     headers={"Content-Type": ctype})
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.read()

    def put_file(fname, path):
        with open(path, "rb") as f:
            _put(f"{output_base_url}/{urllib.parse.quote(fname)}", f.read(), "video/mp4")
        print(f"[MODAL] devolvido {fname}")

    def put_meta(name, obj):
        _put(f"{output_base_url}/meta/{urllib.parse.quote(name)}",
             json.dumps(obj).encode(), "application/json")

    # 1) baixa os takes
    local_files = []
    for url in file_urls:
        base = urllib.parse.unquote(urllib.parse.urlparse(url).path.split("/")[-1])
        dst = os.path.join(takes_dir, base or f"take_{len(local_files)}.mp4")
        try:
            with urllib.request.urlopen(_with_token(url), timeout=180) as r, open(dst, "wb") as f:
                shutil.copyfileobj(r, f)
            local_files.append(dst)
        except Exception as e:
            print("[MODAL] falha ao baixar", url, e)

    # 2) renderiza  +  3) devolve
    try:
        if not local_files:
            raise RuntimeError("nenhum take baixado")
        if mode == "single":
            takes_map = _run_single(local_files, out_dir, count,
                                    headline_text, headline_duration, put_file)
        else:
            takes_map = _run_remix(local_files, out_dir, count,
                                   headline_text, headline_duration, put_file)
        if takes_map:
            put_meta("takes_map.json", takes_map)
        put_meta("_done.json", {"status": "done", "takes_map": takes_map})
        print(f"[MODAL] job {job_id} concluído")
    except Exception as e:
        import traceback
        print("[MODAL] erro:", e, traceback.format_exc())
        try:
            put_meta("_done.json", {"status": "error", "error": str(e)})
        except Exception as e2:
            print("[MODAL] falha ao avisar erro:", e2)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
