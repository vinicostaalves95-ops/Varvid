import os
import uuid
import threading
import tempfile
import shutil

from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

# Funções do Modal — carregadas lazy para não travar o startup
_modal_cache = {}

def modal_fn(name):
    if name not in _modal_cache:
        import modal
        _modal_cache[name] = modal.Function.lookup("varvid", name)
    return _modal_cache[name]

UI_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')
UI_HTML = open(UI_HTML_PATH).read() if os.path.exists(UI_HTML_PATH) else '<h1>ui.html not found</h1>'

jobs = {}

BLOCK_ORDER = ['hook', 'story', 'revelacao', 'prova', 'cta']
SWAPPABLE_BLOCKS = {'hook', 'story', 'cta'}


@app.route('/')
def index():
    return UI_HTML


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'files' not in request.files:
        return jsonify({'error': 'no files'}), 400

    files = request.files.getlist('files')
    job_id = uuid.uuid4().hex[:12]

    files_data = []
    for f in files:
        if f.filename:
            fname = secure_filename(f.filename)
            data = list(f.read())
            files_data.append({'name': fname, 'data': data})

    if not files_data:
        return jsonify({'error': 'no valid files'}), 400

    # Salva no Modal Volume
    modal_fn("save_takes").remote(job_id, files_data)

    # Analisa estrutura localmente para UI
    from engine import group_takes, summarize_groups

    tmp_dir = tempfile.mkdtemp()
    saved = []
    try:
        for fd in files_data:
            path = os.path.join(tmp_dir, fd['name'])
            with open(path, 'wb') as wf:
                wf.write(bytes(fd['data']))
            saved.append(path)

        groups = group_takes(saved)
        summary = summarize_groups(groups)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    swappable_options = []
    for b in BLOCK_ORDER:
        if b in groups and b in SWAPPABLE_BLOCKS:
            swappable_options.append(sorted(groups[b].keys()))
    max_unique = 1
    for opts in swappable_options:
        max_unique *= len(opts)

    jobs[job_id] = {
        'status': 'ready',
        'summary': summary,
        'max_combinations': max_unique,
    }

    return jsonify({
        'job_id': job_id,
        'summary': summary,
        'max_combinations': max_unique,
        'blocks_found': list(summary.keys()),
    })


@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    job_id = data.get('job_id')
    count = int(data.get('count', 10))

    if job_id not in jobs:
        return jsonify({'error': 'job not found'}), 404

    jobs[job_id]['status'] = 'queued'

    def run_modal():
        modal_fn("process_job").remote(job_id, count)

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
