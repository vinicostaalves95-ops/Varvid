"""
VarVid — versão 100% LOCAL (sem Modal, sem Render)

Roda tudo na sua máquina: o mesmo web app (ui.html), mas o render dos vídeos
acontece localmente via ffmpeg. Face-zoom e headline funcionam se as libs
opcionais (opencv/mediapipe) e uma fonte estiverem disponíveis; caso contrário,
o app degrada com elegância (zoom centralizado / sem headline) e continua gerando.

Uso:
    pip install -r requirements_local.txt      # (flask, werkzeug, e opcionais)
    # precisa do ffmpeg/ffprobe instalados no sistema
    python local_app.py
    # abra http://localhost:5000
"""

import os
import re
import json
import uuid
import random
import shutil
import errno
import tempfile
import subprocess
import threading
from pathlib import Path
from itertools import product as iterproduct

import time
import urllib.request
import urllib.error
import urllib.parse

from flask import Flask, request, jsonify, send_file, abort, redirect
from werkzeug.utils import secure_filename

# ─── CONFIG ───────────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.environ.get('VARVID_DATA', os.path.join(BASE_DIR, 'data', 'varvid'))
UI_HTML_PATH = os.path.join(BASE_DIR, 'ui.html')
os.makedirs(DATA_DIR, exist_ok=True)

# ─── BACKEND DE RENDER (local ffmpeg  ×  Modal serverless) ─────────────────────
# 'local'  -> renderiza aqui mesmo com ffmpeg (padrão; ideal pra testar na máquina)
# 'modal'  -> despacha o job pro Modal (produção no Render; escala sob demanda)
RENDER_BACKEND = (os.environ.get('RENDER_BACKEND', 'local') or 'local').strip().lower()
MODAL_ENABLED  = (RENDER_BACKEND == 'modal')
MODAL_APP_NAME = (os.environ.get('MODAL_APP_NAME', 'varvid') or 'varvid').strip()
MODAL_FUNCTION = (os.environ.get('MODAL_FUNCTION', 'process_job_http') or 'process_job_http').strip()
# Segredo compartilhado: o Modal usa pra baixar os takes (/files) e devolver os
# vídeos (/output). Protege esses endpoints de acesso de terceiros. (Recomendado.)
MODAL_CALLBACK_SECRET = (os.environ.get('MODAL_CALLBACK_SECRET', '') or '').strip()
# URL pública deste app — o Modal chama de volta aqui. No Render, RENDER_EXTERNAL_URL
# já vem pronta. Localmente pode ficar vazia (só é usada no modo modal).
PUBLIC_URL = (os.environ.get('PUBLIC_URL') or os.environ.get('RENDER_EXTERNAL_URL') or '').strip().rstrip('/')

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
# Blocos que a UI mostra como "variam" (para calcular max_combinations exibido)
SWAPPABLE_BLOCKS = {'hook', 'cta'}


# ─── SUPABASE / AUTH ──────────────────────────────────────────────────────────
# Login liga só quando existir supabase_config.json (ou as env vars) com URL+chave.
# Sem isso, o app roda como antes (modo local, sem login) — nada trava.

def _load_supabase_config():
    url = os.environ.get('SUPABASE_URL', '').strip()
    key = os.environ.get('SUPABASE_ANON_KEY', '').strip()
    service = os.environ.get('SUPABASE_SERVICE_KEY', '').strip()
    cfg_path = os.path.join(BASE_DIR, 'supabase_config.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                d = json.load(f)
            url = (d.get('url') or url).strip()
            key = (d.get('anon_key') or key).strip()
            service = (d.get('service_key') or service).strip()
        except Exception:
            pass
    return url, key, service


SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY = _load_supabase_config()
AUTH_ENABLED = bool(SUPABASE_URL and SUPABASE_ANON_KEY)
# Créditos ligam quando existir a service_key (secreta) além do login.
CREDITS_ENABLED = bool(AUTH_ENABLED and SUPABASE_SERVICE_KEY)

# Planos: 1 crédito = 1 vídeo gerado. Ajuste os números como quiser.
PLANS = {'free': 10, 'starter': 100, 'pro': 500}
DEFAULT_PLAN = 'free'
DEFAULT_CREDITS = PLANS[DEFAULT_PLAN]

_token_cache = {}   # access_token -> (user_id, expira_em)


def verify_token(token):
    """Valida o token no Supabase e devolve o user_id (ou None)."""
    if not token:
        return None
    now = time.time()
    hit = _token_cache.get(token)
    if hit and hit[1] > now:
        return hit[0]
    try:
        req = urllib.request.Request(
            SUPABASE_URL.rstrip('/') + '/auth/v1/user',
            headers={'Authorization': 'Bearer ' + token, 'apikey': SUPABASE_ANON_KEY})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        uid = data.get('id')
        if uid:
            _token_cache[token] = (uid, now + 60)
            return uid
    except Exception:
        return None
    return None


def _bearer_token():
    h = request.headers.get('Authorization', '')
    if h.startswith('Bearer '):
        return h[7:].strip()
    return request.args.get('access_token', '').strip() or None


def current_user_id():
    """'local' quando o login está desligado; senão o id do Supabase (ou None se inválido)."""
    if not AUTH_ENABLED:
        return 'local'
    return verify_token(_bearer_token())


def current_user_email():
    """Pega o e-mail do usuário logado (ou None)."""
    if not AUTH_ENABLED:
        return None
    try:
        req = urllib.request.Request(
            SUPABASE_URL.rstrip('/') + '/auth/v1/user',
            headers={'Authorization': 'Bearer ' + (_bearer_token() or ''), 'apikey': SUPABASE_ANON_KEY})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get('email')
    except Exception:
        return None


# ─── CRÉDITOS / PLANOS ────────────────────────────────────────────────────────
# Usa a service_key (secreta) pra ler/gravar a tabela `profiles` no Supabase.
# Sem a service_key, os créditos ficam desligados e a geração é ilimitada (como antes).

def _sb_rest(method, path, body=None):
    url = SUPABASE_URL.rstrip('/') + '/rest/v1/' + path
    data = json.dumps(body).encode() if body is not None else None
    last = None
    for attempt in range(3):   # tenta de novo em caso de blip momentâneo do Supabase
        try:
            req = urllib.request.Request(url, data=data, method=method, headers={
                'apikey': SUPABASE_SERVICE_KEY,
                'Authorization': 'Bearer ' + SUPABASE_SERVICE_KEY,
                'Content-Type': 'application/json',
                'Prefer': 'return=representation',
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else []
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(0.6 * (attempt + 1))
    raise last


def get_or_create_profile(uid, email=None):
    """Lê o perfil do usuário; se não existir, cria com o plano/créditos padrão."""
    try:
        rows = _sb_rest('GET', 'profiles?id=eq.%s&select=credits,plan' % uid)
        if rows:
            return rows[0]
        created = _sb_rest('POST', 'profiles',
                           {'id': uid, 'email': email, 'plan': DEFAULT_PLAN, 'credits': DEFAULT_CREDITS})
        return created[0] if created else {'credits': DEFAULT_CREDITS, 'plan': DEFAULT_PLAN}
    except Exception as e:
        print('[CREDITS] erro ao ler/criar perfil:', e)
        return None


def charge_credits(uid, amount):
    """Cobra `amount` créditos. Retorna (ok, restantes, erro).
    erro == 'sem_creditos' -> bloquear; outros erros -> deixar passar (fail-open)."""
    prof = get_or_create_profile(uid)
    if prof is None:
        return False, None, 'db_indisponivel'
    have = int(prof.get('credits', 0))
    if have < amount:
        return False, have, 'sem_creditos'
    try:
        _sb_rest('PATCH', 'profiles?id=eq.%s' % uid, {'credits': have - amount})
        return True, have - amount, None
    except Exception as e:
        print('[CREDITS] erro ao cobrar:', e)
        return False, have, 'db_indisponivel'


def set_plan(uid, plan, extra=None):
    """Define o plano do usuário e recarrega os créditos pra cota do plano."""
    patch = {'plan': plan, 'credits': PLANS.get(plan, PLANS['free'])}
    if extra:
        patch.update(extra)
    try:
        _sb_rest('PATCH', 'profiles?id=eq.%s' % uid, patch)
        return True
    except Exception as e:
        print('[STRIPE] erro ao definir plano:', e)
        return False


# ─── STRIPE / ASSINATURAS ─────────────────────────────────────────────────────
# Liga quando existir a stripe_secret_key + os price ids no supabase_config.json.
# Precisa dos créditos ligados (planos ficam na tabela profiles).

def _load_stripe_config():
    d = {}
    cfg_path = os.path.join(BASE_DIR, 'supabase_config.json')
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path) as f:
                d = json.load(f)
        except Exception:
            d = {}
    sk = (d.get('stripe_secret_key') or os.environ.get('STRIPE_SECRET_KEY', '')).strip()
    wh = (d.get('stripe_webhook_secret') or os.environ.get('STRIPE_WEBHOOK_SECRET', '')).strip()
    prices = {
        'starter': (d.get('stripe_price_starter') or os.environ.get('STRIPE_PRICE_STARTER', '')).strip(),
        'pro':     (d.get('stripe_price_pro') or os.environ.get('STRIPE_PRICE_PRO', '')).strip(),
    }
    return sk, wh, prices


STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_IDS = _load_stripe_config()
STRIPE_ENABLED = bool(CREDITS_ENABLED and STRIPE_SECRET_KEY and STRIPE_PRICE_IDS.get('starter'))
stripe = None
if STRIPE_ENABLED:
    try:
        import stripe as _stripe
        stripe = _stripe
        stripe.api_key = STRIPE_SECRET_KEY
    except Exception as e:
        print('[STRIPE] biblioteca nao instalada (pip install stripe):', e)
        STRIPE_ENABLED = False


def _find_font():
    """Procura uma fonte .ttf utilizável para o headline. Retorna caminho ou None."""
    candidates = [
        os.environ.get('VARVID_FONT', ''),
        os.path.join(BASE_DIR, 'assets', 'Poppins-ExtraBold.ttf'),
        os.path.join(BASE_DIR, 'Poppins-ExtraBold.ttf'),
        '/usr/share/fonts/poppins/Poppins-ExtraBold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',      # macOS
        'C:/Windows/Fonts/arialbd.ttf',                            # Windows
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


FONT_PATH = _find_font()

# ─── DETECÇÃO OPCIONAL DE ROSTO (opencv + mediapipe) ──────────────────────────

try:
    import cv2  # noqa
    import mediapipe as mp  # noqa
    _FACE_OK = True
except Exception:
    _FACE_OK = False


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
    # Resiliente: se o ffprobe não existir (ex.: Render coordenando o Modal), devolve 0.
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath],
            capture_output=True, text=True
        )
        return float(json.loads(result.stdout)['format']['duration'])
    except Exception:
        return 0.0


def summarize_groups(groups):
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


# ─── FACE DETECT ──────────────────────────────────────────────────────────────

def detect_face_center(filepath):
    if not _FACE_OK:
        return None
    try:
        duration = get_duration(filepath)
        if duration < 0.1:
            return None
        mid = duration / 2
        tmp_frame = os.path.join(DATA_DIR, f'face_{uuid.uuid4().hex[:8]}.jpg')
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
        # fallback: re-encode
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


# ─── DESPACHO PRO MODAL (produção) ────────────────────────────────────────────
# No modo 'modal', em vez de renderizar aqui, mandamos o job pro Modal. Ele baixa
# os takes em /files/<job>/<nome>, renderiza e devolve os vídeos em PUT
# /output/<job>/<arquivo> (+ /output/<job>/meta/... pro takes_map e o _done).

def _callback_urls(job_id):
    base = PUBLIC_URL or ''
    q = ('?token=' + urllib.parse.quote(MODAL_CALLBACK_SECRET)) if MODAL_CALLBACK_SECRET else ''
    takes_dir = os.path.join(job_dir(job_id), 'takes')
    names = sorted([f for f in os.listdir(takes_dir) if not f.startswith('.')])
    file_urls = [f"{base}/files/{job_id}/{urllib.parse.quote(n)}{q}" for n in names]
    output_base_url = f"{base}/output/{job_id}"
    return file_urls, output_base_url


def _fail_job(job_id, msg):
    j = load_job(job_id) or {}
    j['status'] = 'error'
    j['error'] = msg
    save_job(job_id, j)
    print('[MODAL]', msg)


def dispatch_modal(job_id, count, headline_text, headline_duration, mode):
    """Manda o job pro Modal (não bloqueia). Marca erro no job se o despacho falhar."""
    if not PUBLIC_URL:
        return _fail_job(job_id, 'PUBLIC_URL/RENDER_EXTERNAL_URL nao definida (modo modal)')
    try:
        import modal
    except Exception as e:
        return _fail_job(job_id, 'biblioteca modal nao instalada: ' + str(e))
    try:
        file_urls, output_base_url = _callback_urls(job_id)
        fn = modal.Function.from_name(MODAL_APP_NAME, MODAL_FUNCTION)
        fn.spawn(job_id, file_urls, output_base_url, count,
                 headline_text, headline_duration, mode, MODAL_CALLBACK_SECRET)
        print(f"[MODAL] despachado job={job_id} mode={mode} count={count} "
              f"-> {MODAL_APP_NAME}.{MODAL_FUNCTION} ({len(file_urls)} takes)")
    except Exception as e:
        import traceback
        j = load_job(job_id) or {}
        j['status'] = 'error'
        j['error'] = 'falha ao despachar pro Modal: ' + str(e)
        j['traceback'] = traceback.format_exc()
        save_job(job_id, j)
        print('[MODAL] erro no despacho:', e)


# ─── JOB RUNNER LOCAL (roda em thread) ────────────────────────────────────────

def run_job_local(job_id, count, headline_text, headline_duration):
    job = load_job(job_id)
    if not job:
        return
    try:
        takes_dir  = os.path.join(job_dir(job_id), 'takes')
        output_dir = os.path.join(job_dir(job_id), 'output')
        os.makedirs(output_dir, exist_ok=True)

        file_list = [os.path.join(takes_dir, f) for f in os.listdir(takes_dir)
                     if not f.startswith('.')]
        groups = group_takes(file_list)
        print(f"[INFO] blocos: {list(groups.keys())}")

        face_cache = {}
        if _FACE_OK:
            print("[FACE] analisando rostos...")
            for fp in file_list:
                face_cache[fp] = detect_face_center(fp)

        combos = build_combinations(groups, count)
        job['status'] = 'rendering'
        job['count_requested'] = count
        job['files'] = []
        job['takes_map'] = {}
        save_job(job_id, job)

        for i, combo in enumerate(combos):
            print(f"[RENDER] {i+1}/{count}")
            fname = f'variation_{i+1:02d}.mp4'
            out_path = os.path.join(output_dir, fname)
            tmp_dir  = os.path.join(job_dir(job_id), f'tmp_{i}')
            ok, takes_used = render_variation(
                groups, combo, out_path, tmp_dir,
                headline_text=headline_text, headline_duration=headline_duration,
                face_cache=face_cache)
            shutil.rmtree(tmp_dir, ignore_errors=True)

            j = load_job(job_id) or job
            if ok and os.path.exists(out_path):
                files = j.get('files', [])
                if fname not in files:
                    files.append(fname)
                    files.sort()
                j['files'] = files
                j['completed'] = len(files)
                j.setdefault('takes_map', {})[fname] = takes_used
            j['status'] = 'rendering'
            j['progress'] = max(5, int((i + 1) / count * 95))
            save_job(job_id, j)

        j = load_job(job_id) or job
        j['status'] = 'done'
        j['progress'] = 100
        save_job(job_id, j)
        print(f"[DONE] job {job_id}: {j.get('completed', 0)} vídeos")

    except Exception as e:
        import traceback
        j = load_job(job_id) or job
        j['status'] = 'error'
        j['error'] = str(e)
        j['traceback'] = traceback.format_exc()
        save_job(job_id, j)
        print(f"[ERR] {e}")


# ─── MODO VÍDEO ÚNICO ─────────────────────────────────────────────────────────

def get_fps(filepath):
    """Descobre o frame rate do vídeo (fallback 30)."""
    try:
        r = subprocess.run(
            ['ffprobe', '-v', '0', '-select_streams', 'v:0',
             '-show_entries', 'stream=r_frame_rate', '-of', 'default=nk=1:nw=1', filepath],
            capture_output=True, text=True
        )
        num, den = r.stdout.strip().split('/')
        fps = float(num) / float(den)
        return fps if fps > 0 else 30.0
    except Exception:
        return 30.0


def render_single_variation(src, dst, tmp_dir, micro_seed,
                            headline_text='', headline_duration=3):
    """
    Cria UMA variação a partir de UM vídeo completo, aplicando os MESMOS tipos
    de ajuste da versão atual:
      - micro-corte no começo (1 a 4 quadros) e no fim (1 a 3 quadros)
      - zoom sutil (crop central + reescala)
      - headline opcional no início
    Cada saída tem trim e zoom próprios (seed por índice) => vídeos distintos.
    """
    rng = random.Random(micro_seed * 9973 + 1337)
    os.makedirs(tmp_dir, exist_ok=True)

    duration = get_duration(src)
    fps = get_fps(src)
    if duration < 0.3:
        return False

    # Micro-cortes (mesma lógica da versão atual, mas nas pontas do vídeo inteiro)
    trim_start = rng.randint(1, 4) / fps
    end_cut    = rng.randint(1, 3) / fps
    new_duration = duration - trim_start - end_cut
    if new_duration < 0.3:            # vídeo muito curto: não corta
        trim_start, new_duration = 0.0, duration

    # Zoom sutil — sempre aplicado (float único por saída garante distinção),
    # na mesma faixa da versão atual (~1.03–1.06), começando em 1.02 pra ficar leve.
    zoom = rng.uniform(1.02, 1.06)

    headline_filter = None
    if headline_text and headline_text.strip():
        headline_filter = build_headline_filter(
            headline_text, style_seed=micro_seed, headline_duration=headline_duration)

    return normalize_segment(
        src, dst, trim_start, new_duration,
        zoom_factor=zoom, face_center=None, headline_filter=headline_filter)


def run_single_job(job_id, count, headline_text, headline_duration):
    job = load_job(job_id)
    if not job:
        return
    try:
        takes_dir  = os.path.join(job_dir(job_id), 'takes')
        output_dir = os.path.join(job_dir(job_id), 'output')
        os.makedirs(output_dir, exist_ok=True)

        files = sorted([os.path.join(takes_dir, f) for f in os.listdir(takes_dir)
                        if not f.startswith('.')])
        if not files:
            raise RuntimeError('nenhum vídeo enviado')

        job['status'] = 'rendering'
        job['count_requested'] = count
        job['files'] = []
        save_job(job_id, job)

        for i in range(count):
            src = files[i % len(files)]           # se enviar >1 vídeo, alterna entre eles
            print(f"[SINGLE] {i+1}/{count} <- {os.path.basename(src)}")
            fname = f'variation_{i+1:02d}.mp4'
            out_path = os.path.join(output_dir, fname)
            tmp_dir  = os.path.join(job_dir(job_id), f'tmp_{i}')
            ok = render_single_variation(
                src, out_path, tmp_dir, micro_seed=i,
                headline_text=headline_text, headline_duration=headline_duration)
            shutil.rmtree(tmp_dir, ignore_errors=True)

            j = load_job(job_id) or job
            if ok and os.path.exists(out_path):
                fl = j.get('files', [])
                if fname not in fl:
                    fl.append(fname)
                    fl.sort()
                j['files'] = fl
                j['completed'] = len(fl)
            else:
                print(f"[WARN] falhou variação {i+1}")
            j['status'] = 'rendering'
            j['progress'] = max(5, int((i + 1) / count * 95))
            save_job(job_id, j)

        j = load_job(job_id) or job
        j['status'] = 'done'
        j['progress'] = 100
        save_job(job_id, j)
        print(f"[DONE] single {job_id}: {j.get('completed', 0)} vídeos")

    except Exception as e:
        import traceback
        j = load_job(job_id) or job
        j['status'] = 'error'
        j['error'] = str(e)
        j['traceback'] = traceback.format_exc()
        save_job(job_id, j)
        print(f"[ERR] {e}")


# ─── FLASK APP ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB
UI_HTML = open(UI_HTML_PATH).read() if os.path.exists(UI_HTML_PATH) else '<h1>ui.html não encontrado</h1>'


def _read_html(name, fallback):
    p = os.path.join(BASE_DIR, name)
    return open(p, encoding='utf-8').read() if os.path.exists(p) else fallback


APP_HTML = _read_html('app.html', UI_HTML)      # app unificado (abas + guia novo)
LOGIN_HTML = _read_html('login.html', '<h1>login.html não encontrado</h1>')

SINGLE_HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VarVid — Vídeo Único</title>
<style>
:root{--accent:#E8FF47;--bg:#080808;--bg2:#0e0e0e;--border:#2a2a2a;--muted:#888}
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,Inter,sans-serif}
body{background:var(--bg);color:#fff;min-height:100vh;padding:24px 16px}
.wrap{max-width:560px;margin:0 auto}
.top{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.dot{width:26px;height:26px;background:var(--accent);border-radius:7px}
h1{font-size:20px;font-weight:800;letter-spacing:-.02em}
.sub{color:var(--muted);font-size:13px;margin-bottom:20px;line-height:1.5}
.sub a{color:var(--accent)}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:14px;padding:16px;margin-bottom:14px}
.label{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#bbb;margin-bottom:10px;font-weight:600}
.drop{border:1px dashed #333;border-radius:12px;padding:26px 16px;text-align:center;cursor:pointer;position:relative;transition:.2s}
.drop.over{border-color:var(--accent)}
.drop input{position:absolute;inset:0;opacity:0;cursor:pointer}
.drop .m{font-size:14px;color:#ddd}.drop .s{font-size:12px;color:#555;margin-top:4px}
.badge{display:inline-block;margin-top:10px;padding:4px 12px;background:#E8FF4712;border:1px solid #E8FF4740;border-radius:20px;font-size:12px;color:var(--accent)}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.vb{height:46px;background:var(--bg2);border:1px solid var(--border);color:#777;font-size:16px;font-weight:700;border-radius:10px;cursor:pointer}
.vb.active{background:var(--accent);border-color:var(--accent);color:#000}
.row{display:flex;gap:8px}
textarea{flex:1;resize:none;height:64px;background:#0b0b0b;border:1px solid var(--border);border-radius:10px;padding:10px;color:#fff;font-size:13px;outline:none}
textarea:focus{border-color:var(--accent)}
.dur{width:76px;background:#0b0b0b;border:1px solid var(--border);border-radius:10px;text-align:center;color:#fff;font-size:22px;font-weight:800;outline:none}
.hint{font-size:11px;color:#555;margin-top:8px;line-height:1.5}
.btn{width:100%;height:52px;background:var(--accent);border:none;border-radius:14px;font-size:15px;font-weight:800;color:#000;cursor:pointer;letter-spacing:.05em}
.btn:disabled{opacity:.3;cursor:not-allowed}
.track{height:4px;background:#1a1a1a;border-radius:2px;overflow:hidden;margin:12px 0 8px}
.fill{height:100%;background:var(--accent);width:0;transition:width .4s}
.res{display:flex;align-items:center;gap:12px;background:#111;border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:8px}
.res .n{flex:1;font-size:13px;font-weight:600}
.res a{color:var(--accent);text-decoration:none;font-size:12px;border:1px solid #E8FF4740;padding:6px 12px;border-radius:8px}
.hidden{display:none}
</style></head><body><div class="wrap">
<div class="top"><div class="dot"></div><h1>VarVid · Vídeo Único</h1></div>
<div class="sub">Suba <b>1 vídeo pronto</b> e gere N variações com os mesmos ajustes da versão atual:
micro-cortes no começo/fim + zoom sutil. &nbsp;·&nbsp; <a href="/">← modo remix de takes</a></div>

<div class="card">
  <div class="label">1 · Seu vídeo</div>
  <div class="drop" id="drop">
    <input type="file" id="file" accept="video/*,.mov,.mp4,.MOV,.MP4" multiple>
    <div class="m">Toque ou arraste o vídeo aqui</div>
    <div class="s">.mp4 · .mov — pode subir mais de um pra gerar em lote</div>
    <div class="badge hidden" id="badge">✦ <span id="fcount">0</span> vídeo(s)</div>
  </div>
</div>

<div class="card">
  <div class="label">2 · Quantas variações</div>
  <div class="grid" id="vargrid">
    <button class="vb active" data-n="5">5</button>
    <button class="vb" data-n="10">10</button>
    <button class="vb" data-n="15">15</button>
    <button class="vb" data-n="20">20</button>
  </div>
</div>

<div class="card">
  <div class="label">3 · Headline (opcional)</div>
  <div class="row">
    <textarea id="hl" maxlength="80" placeholder="Texto no topo do vídeo... (deixe vazio p/ nenhum)"></textarea>
    <input type="number" id="hd" class="dur" value="3" min="1" max="15" title="segundos">
  </div>
  <div class="hint">Os ajustes de fingerprint (micro-corte + zoom) são sempre aplicados. O headline é só um extra visual.</div>
</div>

<button class="btn" id="go" disabled>▶ GERAR VARIAÇÕES</button>

<div class="card hidden" id="progwrap" style="margin-top:14px">
  <div class="label" id="plabel">Renderizando...</div>
  <div class="track"><div class="fill" id="fill"></div></div>
  <div class="hint" id="pfrac">0 / 0</div>
</div>

<div id="results" style="margin-top:14px"></div>
</div>
<script>
let files=[],count=5,job=null,poll=null;
const $=id=>document.getElementById(id);
$('file').addEventListener('change',e=>setFiles(e.target.files));
['dragenter','dragover'].forEach(ev=>$('drop').addEventListener(ev,e=>{e.preventDefault();$('drop').classList.add('over')}));
['dragleave','drop'].forEach(ev=>$('drop').addEventListener(ev,e=>{e.preventDefault();$('drop').classList.remove('over')}));
$('drop').addEventListener('drop',e=>setFiles(e.dataTransfer.files));
function setFiles(fl){
  files=Array.from(fl).filter(f=>/\\.(mp4|mov|avi|mkv|webm)$/i.test(f.name));
  $('fcount').textContent=files.length;
  $('badge').classList.toggle('hidden',!files.length);
  $('go').disabled=!files.length;
}
$('vargrid').addEventListener('click',e=>{
  if(!e.target.dataset.n)return;
  count=parseInt(e.target.dataset.n);
  document.querySelectorAll('.vb').forEach(b=>b.classList.toggle('active',b===e.target));
});
$('go').addEventListener('click',async()=>{
  if(!files.length)return;
  $('go').disabled=true;$('go').textContent='GERANDO...';
  $('results').innerHTML='';$('progwrap').classList.remove('hidden');
  const fd=new FormData();
  files.forEach(f=>fd.append('files',f,f.name));
  fd.append('count',count);
  fd.append('headline_text',$('hl').value.trim());
  fd.append('headline_duration',$('hd').value||'3');
  const r=await fetch('/single/generate',{method:'POST',body:fd});
  const d=await r.json();
  if(d.error){alert('Erro: '+d.error);reset();return}
  job=d.job_id;
  poll=setInterval(check,1500);
});
async function check(){
  const d=await(await fetch('/status/'+job)).json();
  const total=d.count_requested||count,done=d.completed||0;
  $('fill').style.width=(d.progress||0)+'%';
  $('pfrac').textContent=done+' / '+total;
  $('plabel').textContent=d.status==='done'?'Pronto!':'Renderizando...';
  renderResults(d.files||[]);
  if(d.status==='done'||d.status==='error'){clearInterval(poll);reset();
    if(d.status==='error')alert('Erro no render: '+(d.error||''));}
}
function renderResults(fl){
  $('results').innerHTML=fl.map((f,i)=>
    `<div class="res"><div class="n">Variação ${String(i+1).padStart(2,'0')}</div>
     <a href="/download/${job}/${f}" download>⬇ baixar</a></div>`).join('');
}
function reset(){$('go').disabled=false;$('go').textContent='▶ GERAR VARIAÇÕES';}
</script></body></html>"""


def job_dir(job_id):
    return os.path.join(DATA_DIR, job_id)


def save_job(job_id, data):
    """Grava o job de forma ATÔMICA.

    O jeito antigo (`open(path,'w')` + json.dump) truncava o arquivo ANTES de
    escrever: se o dump falhasse no meio (disco cheio, worker morto), o JSON
    ficava vazio pra sempre e todo /status daquele job virava 500 eterno.
    Foi exatamente o que derrubou a produção em 06/09/2026.
    Escrevendo em .tmp e trocando com os.replace(), ou o arquivo antigo continua
    íntegro, ou o novo aparece inteiro — nunca um estado pela metade.
    """
    path = os.path.join(DATA_DIR, job_id + '.json')
    # O temporário PRECISA ser único por escritor. Com um nome fixo (job.json.tmp),
    # dois workers do gunicorn gravando o mesmo job — o que acontece de fato entre
    # o PUT do Modal e o /status — abririam o MESMO arquivo, intercalariam bytes e
    # o os.replace publicaria lixo. mkstemp dá um nome exclusivo e atômico.
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix=job_id + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)          # atômico: ou o antigo, ou o novo inteiro
    except Exception as e:
        try:
            os.remove(tmp)
        except Exception:
            pass
        print('[JOB] falha ao salvar %s: %s' % (job_id, e))
        raise


def load_job(job_id):
    """Lê o job. Devolve None se o arquivo sumiu OU está corrompido/vazio.

    Antes, um JSON vazio estourava JSONDecodeError e o Flask devolvia 500 —
    o front recebia HTML no lugar de JSON e mostrava "Unexpected token '<'".
    """
    path = os.path.join(DATA_DIR, job_id + '.json')
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        # Leitura NÃO apaga: quem é dono da remoção é o sweeper. Uma leitura que
        # muta o disco cria corrida com um escritor concorrente (um reader chegou
        # a apagar arquivo que um writer ia publicar). Devolver None já basta —
        # o /status responde 'not_found' em JSON e o sweeper recolhe o lixo.
        print('[JOB] arquivo ilegível, tratando como inexistente %s: %s' % (job_id, e))
        return None


def _purge_job(jid):
    """Apaga o JSON e a pasta de um job."""
    try:
        os.remove(os.path.join(DATA_DIR, jid + '.json'))
    except Exception:
        pass
    shutil.rmtree(os.path.join(DATA_DIR, jid), ignore_errors=True)


# ─── ESTADO "EM ANDAMENTO" ────────────────────────────────────────────────────
# Um job só bloqueia uma nova geração enquanto estiver DE FATO rodando. Sem um
# conceito de job morto, um container do Modal que morre sem mandar o _done
# deixaria o status preso em 'queued' e trancaria o usuário pra sempre — um bug
# pior que o problema original.
#
# O corte usa o created_at do próprio job, não o mtime do arquivo: o /status
# reescreve o JSON a cada consulta, então o mtime só avança enquanto a aba está
# aberta. Quem fecha a aba durante um render longo teria o job dado como morto.
# O limite fica acima do timeout do Modal (1800s), pra nunca cortar antes dele.

JOB_STALE_MINUTES = float(os.environ.get('VARVID_JOB_STALE_MINUTES', '45'))
RUNNING_STATES = ('queued', 'rendering')


def _job_is_running(j, now=None):
    """True se o job está rodando e ainda dentro do prazo plausível."""
    if not j or j.get('status') not in RUNNING_STATES:
        return False
    now = now or time.time()
    started = j.get('created_at')
    if not started:
        return True          # job antigo, sem carimbo: trata como vivo
    return (now - float(started)) < JOB_STALE_MINUTES * 60


def user_jobs_sweep(uid, purge=True, force=False):
    """Varre os jobs do usuário UMA vez e devolve o que está rodando (ou None).

    Substitui o antigo cleanup_user, que apagava tudo do usuário sem olhar o
    status — inclusive uma geração em andamento. Agora:
      · achou job rodando  -> devolve e NÃO apaga nada (o endpoint vai recusar,
                              então seria injusto destruir os downloads antigos)
      · não achou          -> limpa os jobs encerrados, liberando espaço
      · force=True         -> apaga tudo, inclusive o que está rodando. Só o
                              botão "Limpar" usa isso: é o usuário pedindo, e
                              precisa funcionar mesmo com um job travado — é a
                              válvula de escape dele.
    Uma varredura só, em vez de duas (antes eram cleanup + verificação).
    """
    now = time.time()
    running = None
    encerrados = []
    try:
        for entry in os.scandir(DATA_DIR):
            name = entry.name
            if not (entry.is_file() and name.endswith('.json')):
                continue
            jid = name[:-5]
            j = load_job(jid)
            if not j or j.get('user_id') != uid:
                continue
            if not force and _job_is_running(j, now):
                running = dict(j, job_id=jid)
            else:
                encerrados.append(jid)
    except Exception as e:
        print('[JOBS] erro ao varrer jobs de %s: %s' % (uid, e))
        return None
    if running:
        return running                       # bloqueia: não apaga nada
    if purge or force:
        for jid in encerrados:
            _purge_job(jid)
    return None


def cleanup_user(uid):
    """Compatibilidade: limpa os jobs encerrados do usuário."""
    user_jobs_sweep(uid, purge=True)


def _bloqueio_geracao_em_andamento(uid):
    """Recusa nova geração se já existe uma rodando. None = pode seguir."""
    running = user_jobs_sweep(uid)
    if not running:
        return None
    print('[JOBS] %s tentou nova geração com %s em andamento' % (uid, running.get('job_id')))
    return jsonify({
        'error': 'geracao_em_andamento',
        'job_id': running.get('job_id'),
        'completed': running.get('completed', 0),
        'count_requested': running.get('count_requested'),
    }), 409


# ══════════════════════════════════════════════════════════════════════════════
#  RETENÇÃO DE ARQUIVOS  —  ⚠️ PONTE, NÃO DESTINO
#
#  Isto existe porque hoje o estado do job (JSON) e os vídeos moram no disco
#  local do app. Foi essa escolha que encheu o disco do Render em 06/09/2026.
#
#  DESTINO PRETENDIDO (mantém tudo abaixo obsoleto, sem cirurgia):
#    · estado do job  -> tabela `jobs` no Supabase (fonte de verdade já existe lá
#                        pra usuários/créditos; resolve de quebra a corrida entre
#                        os 2 workers do gunicorn)
#    · vídeos         -> R2/S3 com lifecycle rule de N dias
#                        (a expiração vira config do bucket: zero código)
#
#  Quando essa migração acontecer, apague este bloco inteiro, as chamadas a
#  ensure_disk_space() em /analyze e /single/generate, e o start_sweeper() do
#  boot. Nada mais depende disto — a dependência foi deixada de propósito em um
#  ponto só de cada endpoint, pra sair limpo.
#
#  Enquanto a ponte existir, ela precisa ser: (a) segura com múltiplos workers,
#  (b) desligável sem deploy, (c) capaz de escalar a agressividade antes de
#  deixar o app cair.
# ══════════════════════════════════════════════════════════════════════════════

JOB_TTL_HOURS       = float(os.environ.get('VARVID_JOB_TTL_HOURS', '24'))
SWEEP_EVERY_SECONDS = float(os.environ.get('VARVID_SWEEP_SECONDS', '1800'))
# TTL de emergência: só entra em ação quando o disco já está no limite.
EMERGENCY_TTL_HOURS = float(os.environ.get('VARVID_EMERGENCY_TTL_HOURS', '2'))
# 'off' entrega a responsabilidade a um Render Cron Job ou ao lifecycle do bucket
# sem exigir mudança de código.
SWEEPER_ENABLED = (os.environ.get('VARVID_SWEEPER', 'on').strip().lower() != 'off')

_SWEEP_LOCK = os.path.join(DATA_DIR, '.sweep.lock')


def _acquire_sweep_lock(max_age=600):
    """Lock entre processos: com N workers do gunicorn, só um varre por vez.

    O.EXCL é atômico no filesystem. Um lock mais velho que max_age é considerado
    órfão (worker morto no meio) e recuperado — senão a limpeza pararia pra
    sempre depois de um crash.
    """
    try:
        fd = os.open(_SWEEP_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(_SWEEP_LOCK) > max_age:
                os.remove(_SWEEP_LOCK)          # lock órfão
                return _acquire_sweep_lock(max_age)
        except Exception:
            pass
        return False
    except Exception:
        return True                              # na dúvida, não trava a limpeza


def _release_sweep_lock():
    try:
        os.remove(_SWEEP_LOCK)
    except Exception:
        pass


def _is_job_active(jid, now):
    """Não apagar job em andamento — mas um job travado não é 'em andamento'.

    Usa a MESMA regra do bloqueio (_job_is_running). Se fossem regras
    diferentes, um job preso em 'queued' escaparia da limpeza pra sempre e
    ocuparia disco eternamente.
    """
    return _job_is_running(load_job(jid), now)


def sweep_old_jobs(ttl_hours=None, force=False):
    """Apaga jobs mais velhos que o TTL. Devolve quantos removeu.

    force=True ignora o lock (usado no caminho de emergência, onde esperar a
    próxima janela significaria devolver erro ao usuário).
    """
    ttl = JOB_TTL_HOURS if ttl_hours is None else ttl_hours
    if not force and not _acquire_sweep_lock():
        return 0
    now = time.time()
    cutoff = now - ttl * 3600
    removed = 0
    try:
        for entry in os.scandir(DATA_DIR):
            name = entry.name
            if name.startswith('.'):
                continue
            try:
                st = entry.stat()
                if entry.is_file() and name.endswith('.json'):
                    jid = name[:-5]
                    # JSON de tamanho zero é lixo definitivo (sobra do bug antigo
                    # de truncagem). Com o save atômico isso não se cria mais, mas
                    # os que já estão no disco precisam sair — cada um é um job
                    # inacessível ocupando espaço. Sem esperar o TTL.
                    if st.st_size == 0:
                        _purge_job(jid)
                        removed += 1
                        continue
                    if st.st_mtime >= cutoff:
                        continue
                    if _is_job_active(jid, now):
                        continue                 # ainda renderizando
                    _purge_job(jid)
                    removed += 1
                elif entry.is_file() and name.endswith(('.tmp', '.part')):
                    if st.st_mtime < cutoff:     # sobra de crash no meio da escrita
                        os.remove(entry.path)
                elif entry.is_dir():
                    # pasta sem JSON correspondente = órfã de um purge parcial
                    if not os.path.exists(os.path.join(DATA_DIR, name + '.json')) \
                            and st.st_mtime < cutoff:
                        shutil.rmtree(entry.path, ignore_errors=True)
                        removed += 1
            except Exception:
                continue
    except Exception as e:
        print('[SWEEP] erro:', e)
    finally:
        if not force:
            _release_sweep_lock()
    if removed:
        print('[SWEEP] %d job(s) removidos (TTL=%sh)' % (removed, ttl))
    return removed


def _sweep_loop():
    while True:
        time.sleep(SWEEP_EVERY_SECONDS)
        try:
            sweep_old_jobs()
        except Exception as e:
            print('[SWEEP] loop:', e)


def start_sweeper():
    if not SWEEPER_ENABLED:
        print('[SWEEP] desligado (VARVID_SWEEPER=off)')
        return
    threading.Thread(target=_sweep_loop, daemon=True).start()


# ─── GUARDA DE ESPAÇO EM DISCO ────────────────────────────────────────────────
# Em vez de deixar o os.makedirs estourar OSError (=> 500 em HTML => o front
# mostra "Unexpected token '<'"), checamos antes e devolvemos JSON legível.

MIN_FREE_MB = float(os.environ.get('VARVID_MIN_FREE_MB', '500'))


def free_space_mb():
    try:
        return shutil.disk_usage(DATA_DIR).free / (1024 * 1024)
    except Exception:
        return float('inf')          # não sabendo medir, não bloqueia


def ensure_disk_space():
    """(ok, livre_mb) — escalando antes de desistir.

    Três degraus, do menos ao mais destrutivo. A recusa educada é o último passo:
    é infinitamente melhor que o OSError que derrubou o app em 06/09, mas ainda
    assim significa usuário bloqueado — por isso tentamos liberar antes.
    """
    free = free_space_mb()
    if free >= MIN_FREE_MB:
        return True, free

    # 1) varredura normal (TTL padrão), ignorando o lock: alguém está esperando.
    print('[DISCO] %.0f MB livres (mínimo %.0f) — varredura' % (free, MIN_FREE_MB))
    sweep_old_jobs(force=True)
    free = free_space_mb()
    if free >= MIN_FREE_MB:
        return True, free

    # 2) TTL de emergência, bem mais curto. Nunca toca em job ativo (o
    #    _is_job_active protege), então ninguém perde uma geração em andamento.
    print('[DISCO] ainda %.0f MB — TTL de emergência (%sh)' % (free, EMERGENCY_TTL_HOURS))
    sweep_old_jobs(ttl_hours=EMERGENCY_TTL_HOURS, force=True)
    free = free_space_mb()
    if free >= MIN_FREE_MB:
        return True, free

    # 3) desiste — mas com JSON legível, e deixando rastro pro operador.
    print('[DISCO] ESGOTADO: %.0f MB livres após limpeza. Aumente o disco no '
          'Render ou antecipe a migração pra R2/S3.' % free)
    return False, free


def _owned_job(job_id, uid):
    """Carrega o job só se pertencer ao usuário (respeita o isolamento)."""
    job = load_job(job_id)
    if job is None:
        return None
    if AUTH_ENABLED and job.get('user_id') != uid:
        return None
    return job


@app.route('/')
def index():
    return _read_html('app.html', APP_HTML)      # lê na hora: editar o HTML não exige reiniciar


@app.route('/single')
def single_page():
    return _read_html('app.html', APP_HTML)       # mesmo app; a aba "Vídeo único" abre pelo caminho /single


@app.route('/classic')
def classic():
    return _read_html('ui.html', UI_HTML)         # interface antiga, como fallback


@app.route('/login')
def login_page():
    return _read_html('login.html', LOGIN_HTML)


@app.route('/auth-config.json')
def auth_config():
    return jsonify({
        'authEnabled': AUTH_ENABLED,
        'url': SUPABASE_URL if AUTH_ENABLED else '',
        'anonKey': SUPABASE_ANON_KEY if AUTH_ENABLED else '',
    })


@app.route('/me')
def me():
    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return jsonify({'error': 'unauthorized'}), 401
    out = {'email': current_user_email(), 'creditsEnabled': CREDITS_ENABLED,
           'plan': None, 'credits': None}
    if CREDITS_ENABLED:
        prof = get_or_create_profile(uid, out['email'])
        if prof:
            out['credits'] = prof.get('credits')
            out['plan'] = prof.get('plan')
    return jsonify(out)


@app.route('/billing/plans')
def billing_plans():
    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return jsonify({'error': 'unauthorized'}), 401
    current_plan, credits = 'free', None
    if CREDITS_ENABLED:
        prof = get_or_create_profile(uid, current_user_email())
        if prof:
            current_plan = prof.get('plan', 'free')
            credits = prof.get('credits')
    plans = []
    for key in ('starter', 'pro'):
        pid = STRIPE_PRICE_IDS.get(key)
        if STRIPE_ENABLED and pid:
            plans.append({'key': key, 'label': key.capitalize(),
                          'credits': PLANS[key], 'price_id': pid})
    return jsonify({'stripeEnabled': STRIPE_ENABLED, 'currentPlan': current_plan,
                    'credits': credits, 'plans': plans})


@app.route('/billing/checkout', methods=['POST'])
def billing_checkout():
    if not STRIPE_ENABLED:
        return jsonify({'error': 'stripe_desligado'}), 400
    uid = current_user_id()
    if not uid:
        return jsonify({'error': 'unauthorized'}), 401
    plan = (request.json or {}).get('plan')
    price_id = STRIPE_PRICE_IDS.get(plan)
    if not price_id:
        return jsonify({'error': 'plano_invalido'}), 400
    base = request.host_url.rstrip('/')
    try:
        session = stripe.checkout.Session.create(
            mode='subscription',
            line_items=[{'price': price_id, 'quantity': 1}],
            customer_email=current_user_email(),
            client_reference_id=uid,
            metadata={'uid': uid, 'plan': plan},
            success_url=base + '/billing/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base + '/?assinatura=cancelada',
        )
        return jsonify({'url': session.url})
    except Exception as e:
        print('[STRIPE] erro no checkout:', e)
        return jsonify({'error': str(e)}), 500


@app.route('/billing/success')
def billing_success():
    # Stripe redireciona o navegador pra cá após o pagamento.
    if not STRIPE_ENABLED:
        return redirect('/')
    sid = request.args.get('session_id')
    try:
        s = stripe.checkout.Session.retrieve(sid)
        sd = s.to_dict() if hasattr(s, 'to_dict') else dict(s)
        meta = sd.get('metadata') or {}
        if not isinstance(meta, dict):
            try:
                meta = dict(meta)
            except Exception:
                meta = {}
        if sd.get('payment_status') == 'paid':
            uid = sd.get('client_reference_id') or meta.get('uid')
            plan = meta.get('plan', 'free')
            if uid and plan in PLANS:
                extra = {}
                if sd.get('customer'):
                    extra['stripe_customer_id'] = sd['customer']
                if sd.get('subscription'):
                    extra['stripe_subscription_id'] = sd['subscription']
                set_plan(uid, plan, extra)
        return redirect('/?assinatura=ok')
    except Exception as e:
        print('[STRIPE] erro no success:', e)
        return redirect('/?assinatura=erro')


@app.route('/billing/webhook', methods=['POST'])
def billing_webhook():
    # Renovações e cancelamentos (importante em produção, com o app hospedado).
    if not STRIPE_ENABLED:
        return '', 200
    # FAIL-CLOSED: sem o signing secret, nenhum evento é processado.
    # Antes, com STRIPE_WEBHOOK_SECRET vazio, o `else` aceitava JSON não assinado —
    # qualquer POST com {"type":"invoice.paid",...} creditava créditos na tabela
    # `profiles` REAL. O modo teste do Stripe protege o dinheiro, não o banco.
    if not STRIPE_WEBHOOK_SECRET:
        print('[SEGURANCA] webhook recebido sem STRIPE_WEBHOOK_SECRET configurado — recusado')
        return jsonify({'error': 'webhook_nao_configurado'}), 400

    payload = request.get_data()
    sig = request.headers.get('Stripe-Signature', '')
    try:
        ev = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
        event = ev.to_dict() if hasattr(ev, 'to_dict') else dict(ev)
    except Exception as e:
        print('[STRIPE] webhook inválido (assinatura):', e)
        return '', 400
    etype = event.get('type')
    obj = (event.get('data') or {}).get('object') or {}
    try:
        if etype == 'invoice.paid':
            cust = obj.get('customer')
            rows = _sb_rest('GET', 'profiles?stripe_customer_id=eq.%s&select=id,plan' % cust)
            if rows:
                pl = rows[0].get('plan', 'free')
                _sb_rest('PATCH', 'profiles?id=eq.%s' % rows[0]['id'], {'credits': PLANS.get(pl, PLANS['free'])})
        elif etype == 'customer.subscription.deleted':
            cust = obj.get('customer')
            rows = _sb_rest('GET', 'profiles?stripe_customer_id=eq.%s&select=id' % cust)
            if rows:
                _sb_rest('PATCH', 'profiles?id=eq.%s' % rows[0]['id'],
                         {'plan': 'free', 'credits': PLANS['free']})
    except Exception as e:
        print('[STRIPE] erro ao processar webhook:', e)
    return '', 200


@app.route('/admin/clear', methods=['POST'])
def admin_clear():
    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return jsonify({'error': 'unauthorized'}), 401
    # force=True: o "Limpar" é a válvula de escape do usuário e precisa
    # funcionar mesmo com um job travado — senão o bloqueio vira uma prisão.
    user_jobs_sweep(uid, force=True)
    return jsonify({'ok': True})


@app.route('/analyze', methods=['POST'])
def analyze():
    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return jsonify({'error': 'unauthorized'}), 401
    # Antes, esta linha apagava TODOS os jobs do usuário — inclusive um que
    # estivesse renderizando. Bastava subir arquivo novo sem esperar (ou abrir
    # outra aba) pra matar a própria geração e perder os créditos já cobrados.
    bloqueio = _bloqueio_geracao_em_andamento(uid)
    if bloqueio:
        return bloqueio
    if 'files' not in request.files:
        return jsonify({'error': 'no files'}), 400

    ok, free = ensure_disk_space()
    if not ok:
        return jsonify({'error': 'sem_espaco', 'free_mb': round(free)}), 507

    files = request.files.getlist('files')
    job_id = uuid.uuid4().hex[:12]
    takes_dir = os.path.join(job_dir(job_id), 'takes')

    saved_paths = []
    try:
        os.makedirs(takes_dir, exist_ok=True)
        for f in files:
            if f.filename:
                path = os.path.join(takes_dir, secure_filename(f.filename))
                f.save(path)
                saved_paths.append(path)
        if not saved_paths:
            return jsonify({'error': 'no valid files'}), 400

        groups = group_takes(saved_paths)
        summary = summarize_groups(groups)

        avg_duration = 0.0
        try:
            total_dur = 0.0
            for block in BLOCK_ORDER:
                if block in groups:
                    variant_durs = [sum(get_duration(f) for f in vf)
                                    for vf in groups[block].values()]
                    total_dur += sum(variant_durs) / len(variant_durs)
            avg_duration = round(total_dur, 1)
        except Exception:
            avg_duration = 0.0

        max_unique = 1
        for b in BLOCK_ORDER:
            if b in groups and b in SWAPPABLE_BLOCKS:
                max_unique *= len(sorted(groups[b].keys()))

        save_job(job_id, {
            'status': 'ready', 'summary': summary, 'max_combinations': max_unique,
            'avg_duration': avg_duration, 'files': [], 'completed': 0, 'takes_map': {},
            'user_id': uid,
        })
        return jsonify({
            'job_id': job_id, 'summary': summary, 'max_combinations': max_unique,
            'avg_duration': avg_duration, 'blocks_found': list(summary.keys()),
        })
    except OSError as e:
        # disco cheio / erro de escrita: devolve JSON (nunca 500 em HTML)

        shutil.rmtree(job_dir(job_id), ignore_errors=True)
        if getattr(e, 'errno', None) == errno.ENOSPC:
            sweep_old_jobs()
            return jsonify({'error': 'sem_espaco'}), 507
        print('[ANALYZE] erro de I/O:', e)
        return jsonify({'error': 'falha_io'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()                       # trace vai pro log, não pro cliente
        shutil.rmtree(job_dir(job_id), ignore_errors=True)
        return jsonify({'error': str(e)}), 500


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json or {}
    job_id = data.get('job_id')
    count = int(data.get('count', 5))
    headline_text = (data.get('headline_text') or '').strip()
    headline_duration = int(data.get('headline_duration', 3))

    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return jsonify({'error': 'unauthorized'}), 401
    job = _owned_job(job_id, uid)
    if not job:
        return jsonify({'error': 'job not found'}), 404
    takes_dir = os.path.join(job_dir(job_id), 'takes')
    if not os.path.exists(takes_dir):
        return jsonify({'error': 'files not found, please re-upload'}), 404

    if CREDITS_ENABLED:
        ok, rem, err = charge_credits(uid, count)
        if err == 'sem_creditos':
            return jsonify({'error': 'sem_creditos', 'credits': rem}), 402
        # db_indisponivel: não trava o usuário — segue e loga

    out_dir = os.path.join(job_dir(job_id), 'output')
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    job.update({'status': 'queued', 'files': [], 'completed': 0,
                'count_requested': count, 'headline_text': headline_text,
                'headline_duration': headline_duration, 'takes_map': {}, 'progress': 0,
                'created_at': time.time()})   # base do "job travado" (JOB_STALE_MINUTES)
    save_job(job_id, job)

    if MODAL_ENABLED:
        dispatch_modal(job_id, count, headline_text, headline_duration, mode='remix')
    else:
        t = threading.Thread(target=run_job_local,
                             args=(job_id, count, headline_text, headline_duration))
        t.daemon = True
        t.start()
    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return jsonify({'status': 'unauthorized'}), 401
    job = load_job(job_id)
    if AUTH_ENABLED and (job is None or job.get('user_id') != uid):
        return jsonify({'status': 'not_found'}), 404
    out_dir = os.path.join(job_dir(job_id), 'output')
    if os.path.exists(out_dir):
        done = sorted([f for f in os.listdir(out_dir) if f.endswith('.mp4')])
        if job is None:
            job = {'status': 'rendering', 'files': [], 'completed': 0,
                   'count_requested': len(done) or 5, 'takes_map': {}}
        job['files'] = done
        job['completed'] = len(done)
        count_req = job.get('count_requested', 5)
        if len(done) >= count_req and job.get('status') != 'error':
            job['status'] = 'done'
            job['progress'] = 100
        elif job.get('status') not in ('error', 'done'):
            job['status'] = 'rendering'
            job['progress'] = max(5, int(len(done) / max(count_req, 1) * 95))
        save_job(job_id, job)
        return jsonify(job)
    if not job:
        return jsonify({'status': 'not_found'})
    return jsonify(job)


@app.route('/download/<job_id>/<filename>')
def download(job_id, filename):
    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return 'unauthorized', 401
    if AUTH_ENABLED and _owned_job(job_id, uid) is None:
        return 'not found', 404
    path = os.path.join(job_dir(job_id), 'output', secure_filename(filename))
    if not os.path.exists(path):
        return 'not found', 404
    return send_file(path, as_attachment=True, download_name=filename, mimetype='video/mp4')


# ─── ENDPOINTS DO MODAL (baixar takes / devolver vídeos) ──────────────────────
# Protegidos pelo MODAL_CALLBACK_SECRET quando definido. Usados só no modo modal,
# pelo próprio Modal — não pelo navegador do usuário.

def _check_modal_token():
    """FAIL-CLOSED: sem segredo definido no modo modal, ninguém entra.

    Antes isto devolvia True quando MODAL_CALLBACK_SECRET estava vazio — um typo
    no nome da env var (já aconteceu com SUBASE_URL) deixaria /files (ler takes de
    qualquer job) e /output (escrever arquivo arbitrário no disco) abertos na
    internet, sem nenhum aviso.
    """
    if not MODAL_CALLBACK_SECRET:
        if MODAL_ENABLED:
            print('[SEGURANCA] MODAL_CALLBACK_SECRET vazio — bloqueando callback')
            return False
        return True                    # modo local: o Modal nem é usado
    tok = request.args.get('token', '') or request.headers.get('X-Modal-Token', '')
    return tok == MODAL_CALLBACK_SECRET


@app.route('/files/<job_id>/<path:filename>')
def modal_files(job_id, filename):
    """O Modal baixa os takes daqui pra renderizar."""
    if not _check_modal_token():
        return 'forbidden', 403
    path = os.path.join(job_dir(job_id), 'takes', secure_filename(os.path.basename(filename)))
    if not os.path.exists(path):
        return 'not found', 404
    return send_file(path)


@app.route('/output/<job_id>/<filename>', methods=['PUT'])
def modal_output_put(job_id, filename):
    """O Modal devolve cada vídeo pronto por aqui."""
    if not _check_modal_token():
        return 'forbidden', 403
    out_dir = os.path.join(job_dir(job_id), 'output')
    path = os.path.join(out_dir, secure_filename(os.path.basename(filename)))
    tmp = path + '.part'
    # Escreve em .part e só então renomeia: o /status lista o out_dir e ofereceria
    # download de um arquivo ainda em transferência (o .part é ignorado no listdir).
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(tmp, 'wb') as f:
            f.write(request.get_data())
        os.replace(tmp, path)
    except OSError as e:

        try:
            os.remove(tmp)
        except Exception:
            pass
        if getattr(e, 'errno', None) == errno.ENOSPC:
            sweep_old_jobs()
            print('[MODAL] disco cheio ao receber', filename)
            return jsonify({'error': 'sem_espaco'}), 507
        print('[MODAL] erro de I/O ao receber %s: %s' % (filename, e))
        return jsonify({'error': 'falha_io'}), 500
    return jsonify({'ok': True})


@app.route('/output/<job_id>/meta/<filename>', methods=['PUT'])
def modal_output_meta(job_id, filename):
    """Metadados do Modal: takes_map (quais takes entraram) e _done (fim do job)."""
    if not _check_modal_token():
        return 'forbidden', 403
    # nome cru: é um único segmento da URL (sem barras); usado só p/ rotear a lógica,
    # não como caminho em disco. secure_filename() aqui removeria o '_' de '_done'.
    name = os.path.basename(filename)
    j = load_job(job_id)
    if j is None:
        return 'not found', 404
    try:
        body = json.loads(request.get_data() or b'{}')
    except Exception:
        body = {}
    if name.startswith('takes_map'):
        j['takes_map'] = body
    elif name.startswith('_done'):
        # o Modal terminou: fixa o status de forma autoritativa
        j['status'] = body.get('status', 'done')
        if body.get('error'):
            j['error'] = body['error']
        if body.get('takes_map'):
            j['takes_map'] = body['takes_map']
        j['progress'] = 100 if j['status'] == 'done' else j.get('progress', 0)
    save_job(job_id, j)
    return jsonify({'ok': True})


@app.route('/single/generate', methods=['POST'])
def single_generate():
    uid = current_user_id()
    if AUTH_ENABLED and not uid:
        return jsonify({'error': 'unauthorized'}), 401
    bloqueio = _bloqueio_geracao_em_andamento(uid)
    if bloqueio:
        return bloqueio
    if 'files' not in request.files:
        return jsonify({'error': 'no files'}), 400

    ok, free = ensure_disk_space()
    if not ok:
        return jsonify({'error': 'sem_espaco', 'free_mb': round(free)}), 507

    files = request.files.getlist('files')
    count = int(request.form.get('count', 5))
    headline_text = (request.form.get('headline_text') or '').strip()
    headline_duration = int(request.form.get('headline_duration', 3))

    job_id = uuid.uuid4().hex[:12]
    takes_dir = os.path.join(job_dir(job_id), 'takes')

    saved = []
    try:
        os.makedirs(takes_dir, exist_ok=True)
        for f in files:
            if f.filename:
                path = os.path.join(takes_dir, secure_filename(f.filename))
                f.save(path)
                saved.append(path)
    except OSError as e:

        shutil.rmtree(job_dir(job_id), ignore_errors=True)
        if getattr(e, 'errno', None) == errno.ENOSPC:
            sweep_old_jobs()
            return jsonify({'error': 'sem_espaco'}), 507
        print('[SINGLE] erro de I/O:', e)
        return jsonify({'error': 'falha_io'}), 500
    if not saved:
        shutil.rmtree(job_dir(job_id), ignore_errors=True)
        return jsonify({'error': 'no valid files'}), 400

    if CREDITS_ENABLED:
        ok, rem, err = charge_credits(uid, count)
        if err == 'sem_creditos':
            shutil.rmtree(job_dir(job_id), ignore_errors=True)
            return jsonify({'error': 'sem_creditos', 'credits': rem}), 402

    save_job(job_id, {
        'status': 'queued', 'mode': 'single', 'files': [], 'completed': 0,
        'count_requested': count, 'headline_text': headline_text,
        'headline_duration': headline_duration, 'progress': 0,
        'user_id': uid, 'created_at': time.time(),
    })

    if MODAL_ENABLED:
        dispatch_modal(job_id, count, headline_text, headline_duration, mode='single')
    else:
        t = threading.Thread(target=run_single_job,
                             args=(job_id, count, headline_text, headline_duration))
        t.daemon = True
        t.start()
    return jsonify({'ok': True, 'job_id': job_id})


# ─── BOOT ─────────────────────────────────────────────────────────────────────
# Fora do __main__ de propósito: em produção quem sobe o app é o gunicorn, que
# nunca executa o bloco __main__. Sem isto o TTL não rodaria justamente onde é
# necessário. Uma varredura já na subida limpa o que ficou de antes.

sweep_old_jobs()
start_sweeper()
print('[BOOT] TTL=%sh · varredura a cada %ss · espaço livre: %.0f MB'
      % (JOB_TTL_HOURS, int(SWEEP_EVERY_SECONDS), free_space_mb()))


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', '5001'))   # 5001 evita o conflito com o AirPlay do macOS
    print("=" * 60)
    print(" VarVid LOCAL")
    if MODAL_ENABLED:
        print(f"  render backend .. MODAL ({MODAL_APP_NAME}.{MODAL_FUNCTION})")
        print(f"  url pública ..... {PUBLIC_URL or 'FALTANDO — defina PUBLIC_URL/RENDER_EXTERNAL_URL!'}")
        print(f"  segredo modal ... {'definido' if MODAL_CALLBACK_SECRET else 'VAZIO (recomendado definir MODAL_CALLBACK_SECRET)'}")
    else:
        print(f"  render backend .. local (ffmpeg)")
    print(f"  ffmpeg .......... {'ok' if shutil.which('ffmpeg') else ('n/d — ok no modo modal' if MODAL_ENABLED else 'FALTANDO — instale ffmpeg!')}")
    print(f"  face detect ..... {'ativo (opencv+mediapipe)' if _FACE_OK else 'desligado (opcional)'}")
    print(f"  headline font ... {FONT_PATH or 'nao encontrada (headline desativado)'}")
    print(f"  login ........... {'ATIVO (Supabase)' if AUTH_ENABLED else 'desligado (modo local — sem senha)'}")
    print(f"  créditos ........ {'ATIVOS (planos: ' + ', '.join(PLANS) + ')' if CREDITS_ENABLED else 'desligados (geração ilimitada)'}")
    print(f"  stripe .......... {'ATIVO (assinaturas)' if STRIPE_ENABLED else 'desligado (sem cobrança)'}")
    print(f"  dados em ........ {DATA_DIR}")
    print(f"  disco livre ..... {free_space_mb():.0f} MB (mínimo exigido: {MIN_FREE_MB:.0f} MB)")
    print(f"  TTL dos jobs .... {JOB_TTL_HOURS}h")
    print(f"  abra ............ http://localhost:{PORT}/")
    print(f"  (vídeo único) ... http://localhost:{PORT}/single")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
