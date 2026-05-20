import os
import uuid
import threading
import shutil
import json

# Credenciais Modal hardcoded
os.environ.setdefault('MODAL_TOKEN_ID', 'ak-NoYwGctnzXxAYNDyxOmgxG')
os.environ.setdefault('MODAL_TOKEN_SECRET', 'as-2Ni7YID6KeVHVSeEQelpLi')

import modal
from flask import Flask, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

_modal_cache = {}

def modal_fn(name):
    if name not in _modal_cache:
        _modal_cache[name] = modal.Function.from_name("varvid", name)
    return _modal_cache[name]

UI_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')
UI_HTML = open(UI_HTML_PATH).read() if os.path.exists(UI_HTML_PATH) else '<h1>ui.html not found</h1>'

BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']
SWAPPABLE_BLOCKS = {'hook', 'story', 'cta'}
DATA_DIR = '/data/varvid'
os.makedirs(DATA_DIR, exist_ok=True)

RENDER_URL = 'https://varvid.onrender.com'


def job_dir(job_id):
    return os.path.join(DATA_DIR, job_id)


def save_job(job_id, data):
    path = os.path.join(DATA_DIR, job_id + '.json')
    with open(path, 'w') as f:
        json.dump(data, f)


def load_job(job_id):
    path = os.path.join(DATA_DIR, job_id + '.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


@app.route('/')
def index():
    return UI_HTML


# ── Rota para o Modal buscar os arquivos de input ──────────────────────────
@app.route('/files/<job_id>/<filename>')
def serve_file(job_id, filename):
    path = os.path.join(job_dir(job_id), 'takes', secure_filename(filename))
    if not os.path.exists(path):
        abort(404)
    return send_file(path)


# ── Rota para o Modal salvar os outputs ────────────────────────────────────
@app.route('/output/<job_id>/<filename>', methods=['PUT'])
def receive_output(job_id, filename):
    out_dir = os.path.join(job_dir(job_id), 'output')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, secure_filename(filename))
    request.stream_to_file(path) if hasattr(request, 'stream_to_file') else open(path, 'wb').write(request.data)
    return jsonify({'ok': True})


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'files' not in request.files:
        return jsonify({'error': 'no files'}), 400

    files = request.files.getlist('files')
    job_id = uuid.uuid4().hex[:12]
    takes_dir = os.path.join(job_dir(job_id), 'takes')
    os.makedirs(takes_dir, exist_ok=True)

    saved_paths = []
    try:
        for f in files:
            if f.filename:
                fname = secure_filename(f.filename)
                path = os.path.join(takes_dir, fname)
                f.save(path)
                saved_paths.append(path)

        if not saved_paths:
            return jsonify({'error': 'no valid files'}), 400

        from engine import group_takes, summarize_groups
        groups = group_takes(saved_paths)
        summary = summarize_groups(groups)

        swappable_options = []
        for b in BLOCK_ORDER:
            if b in groups and b in SWAPPABLE_BLOCKS:
                swappable_options.append(sorted(groups[b].keys()))
        max_unique = 1
        for opts in swappable_options:
            max_unique *= len(opts)

        job_data = {
            'status': 'ready',
            'summary': summary,
            'max_combinations': max_unique,
            'files': [os.path.basename(p) for p in saved_paths],
        }
        save_job(job_id, job_data)

        return jsonify({
            'job_id': job_id,
            'summary': summary,
            'max_combinations': max_unique,
            'blocks_found': list(summary.keys()),
        })

    except Exception as e:
        import traceback
        shutil.rmtree(job_dir(job_id), ignore_errors=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    job_id = data.get('job_id')
    count = int(data.get('count', 10))

    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'job not found'}), 404

    takes_dir = os.path.join(job_dir(job_id), 'takes')
    if not os.path.exists(takes_dir):
        return jsonify({'error': 'files not found, please re-upload'}), 404

    job['status'] = 'queued'
    save_job(job_id, job)

    # Monta lista de URLs para o Modal buscar
    file_urls = [
        f"{RENDER_URL}/files/{job_id}/{fname}"
        for fname in os.listdir(takes_dir)
        if not fname.startswith('.')
    ]
    output_base_url = f"{RENDER_URL}/output/{job_id}"

    def run_modal():
        try:
            modal_fn("process_job_http").remote(job_id, file_urls, output_base_url, count)
        except Exception as e:
            job['status'] = 'error'
            job['error'] = str(e)
            save_job(job_id, job)

    t = threading.Thread(target=run_modal)
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    job = load_job(job_id)
    if not job:
        return jsonify({'status': 'not_found'})

    # Conta outputs prontos
    out_dir = os.path.join(job_dir(job_id), 'output')
    if os.path.exists(out_dir):
        done = [f for f in os.listdir(out_dir) if f.endswith('.mp4')]
        job['completed'] = len(done)
        job['files'] = done
        if len(done) >= job.get('count_requested', 1):
            job['status'] = 'done'
            job['progress'] = 100
        save_job(job_id, job)

    return jsonify(job)


@app.route('/download/<job_id>/<filename>')
def download(job_id, filename):
    path = os.path.join(job_dir(job_id), 'output', secure_filename(filename))
    if not os.path.exists(path):
        return 'not found', 404
    return send_file(path, as_attachment=True, download_name=filename, mimetype='video/mp4')


@app.route('/download/<job_id>/<int:idx>')
def download_by_idx(job_id, idx):
    filename = f'variation_{idx:02d}.mp4'
    return download(job_id, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
