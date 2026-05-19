import os
import uuid
import threading
from itertools import product as iterproduct

from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename

import modal

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

# Carrega funções do Modal
modal_app = modal.App.lookup("varvid")
_save_takes   = modal.Function.lookup("varvid", "save_takes")
_process_job  = modal.Function.lookup("varvid", "process_job")
_get_status   = modal.Function.lookup("varvid", "get_status")
_get_video    = modal.Function.lookup("varvid", "get_video")
_cleanup_job  = modal.Function.lookup("varvid", "cleanup_job")

UI_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')
UI_HTML = open(UI_HTML_PATH).read() if os.path.exists(UI_HTML_PATH) else '<h1>ui.html not found</h1>'

# Cache local de jobs (só metadados, não vídeos)
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

    # Envia arquivos para o Modal Volume
    files_data = []
    for f in files:
        if f.filename:
            fname = secure_filename(f.filename)
            data = list(f.read())  # converte bytes para list (serializable)
            files_data.append({'name': fname, 'data': data})

    if not files_data:
        return jsonify({'error': 'no valid files'}), 400

    # Salva no Modal (síncrono, rápido)
    _save_takes.remote(job_id, files_data)

    # Analisa estrutura localmente para UI
    from engine import group_takes, summarize_groups
    import tempfile

    tmp_dir = tempfile.mkdtemp()
    saved = []
    for fd in files_data:
        path = os.path.join(tmp_dir, fd['name'])
        with open(path, 'wb') as wf:
            wf.write(bytes(fd['data']))
        saved.append(path)

    groups = group_takes(saved)
    summary = summarize_groups(groups)

    swappable_options = []
    for b in BLOCK_ORDER:
        if b in groups and b in SWAPPABLE_BLOCKS:
            swappable_options.append(sorted(groups[b].keys()))
    max_unique = 1
    for opts in swappable_options:
        max_unique *= len(opts)

    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

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
    jobs[job_id]['count_requested'] = count

    # Dispara processamento no Modal em background
    def run_modal():
        _process_job.remote(job_id, count)

    t = threading.Thread(target=run_modal)
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    try:
        result = _get_status.remote(job_id)
        if job_id in jobs:
            jobs[job_id].update(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500


@app.route('/download/<job_id>/<filename>')
def download(job_id, filename):
    try:
        video_bytes = _get_video.remote(job_id, filename)
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
