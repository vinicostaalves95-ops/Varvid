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
SWAPPABLE_BLOCKS = {'hook', 'cta'}
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


def cleanup_all():
    """Apaga tudo no disco — chamado antes de cada novo upload."""
    try:
        for entry in os.scandir(DATA_DIR):
            if entry.is_dir():
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                os.remove(entry.path)
    except Exception:
        pass


@app.route('/admin/clear', methods=['POST'])
def admin_clear():
    cleanup_all()
    return jsonify({'ok': True, 'msg': 'Disco limpo com sucesso'})


@app.route('/')
def index():
    return UI_HTML


@app.route('/files/<job_id>/<filename>')
def serve_file(job_id, filename):
    path = os.path.join(job_dir(job_id), 'takes', secure_filename(filename))
    if not os.path.exists(path):
        abort(404)
    return send_file(path)


@app.route('/output/<job_id>/<filename>', methods=['PUT'])
def receive_output(job_id, filename):
    out_dir = os.path.join(job_dir(job_id), 'output')
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, secure_filename(filename))
    with open(path, 'wb') as f:
        f.write(request.data)

    job = load_job(job_id)
    if job:
        files = job.get('files', [])
        if filename not in files:
            files.append(filename)
            files.sort()
        job['files'] = files
        job['completed'] = len(files)
        save_job(job_id, job)

    return jsonify({'ok': True})


@app.route('/analyze', methods=['POST'])
def analyze():
    # Limpa tudo antes de cada novo job
    cleanup_all()

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
            'files': [],
            'completed': 0,
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
    count = int(data.get('count', 5))

    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'job not found'}), 404

    takes_dir = os.path.join(job_dir(job_id), 'takes')
    if not os.path.exists(takes_dir):
        return jsonify({'error': 'files not found, please re-upload'}), 404

    # Limpa outputs anteriores deste job
    out_dir = os.path.join(job_dir(job_id), 'output')
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    job['status'] = 'queued'
    job['files'] = []
    job['completed'] = 0
    job['count_requested'] = count
    save_job(job_id, job)

    file_urls = [
        f"{RENDER_URL}/files/{job_id}/{fname}"
        for fname in os.listdir(takes_dir)
        if not fname.startswith('.')
    ]
    output_base_url = f"{RENDER_URL}/output/{job_id}"

    def run_modal():
        try:
            modal_fn("process_job_http").remote(job_id, file_urls, output_base_url, count)
            # Apaga takes após enviar URLs ao Modal — libera espaço
            shutil.rmtree(takes_dir, ignore_errors=True)
            j = load_job(job_id)
            if j and j.get('status') != 'error':
                j['status'] = 'done'
                j['progress'] = 100
                save_job(job_id, j)
        except Exception as e:
            j = load_job(job_id)
            if j:
                j['status'] = 'error'
                j['error'] = str(e)
                save_job(job_id, j)

    t = threading.Thread(target=run_modal)
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    job = load_job(job_id)
    if not job:
        return jsonify({'status': 'not_found'})

    out_dir = os.path.join(job_dir(job_id), 'output')
    if os.path.exists(out_dir):
        done = sorted([f for f in os.listdir(out_dir) if f.endswith('.mp4')])
        job['files'] = done
        job['completed'] = len(done)
        count_req = job.get('count_requested', 5)
        if len(done) >= count_req:
            job['status'] = 'done'
            job['progress'] = 100
        elif job.get('status') not in ('error', 'done'):
            job['progress'] = max(5, int(len(done) / count_req * 95))
        save_job(job_id, job)

    return jsonify(job)


@app.route('/download/<job_id>/<filename>')
def download(job_id, filename):
    path = os.path.join(job_dir(job_id), 'output', secure_filename(filename))
    if not os.path.exists(path):
        return 'not found', 404

    # Serve o arquivo e apaga depois para liberar espaço
    def send_and_delete():
        try:
            os.remove(path)
            # Se pasta output ficou vazia, apaga o job inteiro
            out_dir = os.path.join(job_dir(job_id), 'output')
            if os.path.exists(out_dir) and not os.listdir(out_dir):
                shutil.rmtree(job_dir(job_id), ignore_errors=True)
                json_path = os.path.join(DATA_DIR, job_id + '.json')
                if os.path.exists(json_path):
                    os.remove(json_path)
        except Exception:
            pass

    response = send_file(path, as_attachment=True, download_name=filename, mimetype='video/mp4')
    # Apaga após resposta ser enviada
    threading.Thread(target=send_and_delete).start()
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
