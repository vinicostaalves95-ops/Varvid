import os
import uuid
import threading
import shutil
import json

# Cria credenciais do Modal a partir das variáveis de ambiente
_modal_token_id = os.environ.get('MODAL_TOKEN_ID', '')
_modal_token_secret = os.environ.get('MODAL_TOKEN_SECRET', '')
if _modal_token_id and _modal_token_secret:
    os.makedirs(os.path.expanduser('~/.modal'), exist_ok=True)
    with open(os.path.expanduser('~/.modal/credentials.toml'), 'w') as _f:
        _f.write(f'[default]\ntoken_id = "{_modal_token_id}"\ntoken_secret = "{_modal_token_secret}"\n')

from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

_modal_cache = {}

def modal_fn(name):
    if name not in _modal_cache:
        import modal
        _modal_cache[name] = modal.Function.from_name("varvid", name)
    return _modal_cache[name]

UI_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')
UI_HTML = open(UI_HTML_PATH).read() if os.path.exists(UI_HTML_PATH) else '<h1>ui.html not found</h1>'

BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']
SWAPPABLE_BLOCKS = {'hook', 'story', 'cta'}
UPLOAD_DIR = '/tmp/varvid_uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_job(job_id, data):
    """Salva metadados do job no disco."""
    path = os.path.join(UPLOAD_DIR, job_id + '.json')
    with open(path, 'w') as f:
        json.dump(data, f)


def load_job(job_id):
    """Carrega metadados do job do disco."""
    path = os.path.join(UPLOAD_DIR, job_id + '.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


@app.route('/')
def index():
    return UI_HTML


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'files' not in request.files:
        return jsonify({'error': 'no files'}), 400

    files = request.files.getlist('files')
    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    saved_paths = []
    try:
        for f in files:
            if f.filename:
                fname = secure_filename(f.filename)
                path = os.path.join(job_dir, fname)
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
            'job_dir': job_dir,
            'summary': summary,
            'max_combinations': max_unique,
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
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    job_id = data.get('job_id')
    count = int(data.get('count', 10))

    job = load_job(job_id)
    if not job:
        return jsonify({'error': 'job not found'}), 404

    job_dir = job['job_dir']
    if not os.path.exists(job_dir):
        return jsonify({'error': 'upload files not found, please re-upload'}), 404

    job['status'] = 'queued'
    save_job(job_id, job)

    def run_modal():
        try:
            file_list = [f for f in os.listdir(job_dir) if not f.startswith('.') and not f.endswith('.json')]
            files_data = []
            for fname in file_list:
                path = os.path.join(job_dir, fname)
                with open(path, 'rb') as f:
                    files_data.append({'name': fname, 'data': list(f.read())})

            modal_fn("save_takes").remote(job_id, files_data)
            modal_fn("process_job").remote(job_id, count)
            shutil.rmtree(job_dir, ignore_errors=True)
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
    try:
        result = modal_fn("get_status").remote(job_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/download/<job_id>/<filename>')
def download(job_id, filename):
    try:
        video_bytes = modal_fn("get_video").remote(job_id, filename)
        if not video_bytes:
            return 'not found', 404
        import io
        return send_file(
            io.BytesIO(video_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
    except Exception as e:
        return str(e), 500


@app.route('/download/<job_id>/<int:idx>')
def download_by_idx(job_id, idx):
    filename = f'variation_{idx:02d}.mp4'
    return download(job_id, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
