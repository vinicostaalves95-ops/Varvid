import os
import uuid
import threading
import shutil
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
from engine import group_takes, summarize_groups, build_combinations, run_job, BLOCK_ORDER, SWAPPABLE_BLOCKS

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

BASE_DIR = '/tmp/varvid'
os.makedirs(BASE_DIR, exist_ok=True)

jobs = {}  # job_id -> job dict


@app.route('/')
def index():
    ui_path = os.path.join(os.path.dirname(__file__), 'ui.html')
    return render_template_string(open(ui_path).read())


@app.route('/analyze', methods=['POST'])
def analyze():
    """Receive takes folder, analyze and return structure"""
    if 'files' not in request.files:
        return jsonify({'error': 'no files'}), 400

    files = request.files.getlist('files')
    job_id = uuid.uuid4().hex[:12]
    upload_dir = os.path.join(BASE_DIR, job_id, 'takes')
    os.makedirs(upload_dir, exist_ok=True)

    saved = []
    for f in files:
        if f.filename:
            fname = secure_filename(f.filename)
            path = os.path.join(upload_dir, fname)
            f.save(path)
            saved.append(path)

    if not saved:
        return jsonify({'error': 'no valid files'}), 400

    groups = group_takes(saved)
    summary = summarize_groups(groups)

    # Count combinations
    from itertools import product as iproduct
    swappable_options = []
    for b in BLOCK_ORDER:
        if b in groups and b in SWAPPABLE_BLOCKS:
            swappable_options.append(sorted(groups[b].keys()))
    
    max_unique = 1
    for opts in swappable_options:
        max_unique *= len(opts)

    jobs[job_id] = {
        'status': 'ready',
        'upload_dir': upload_dir,
        'groups': groups,
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

    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'job not found'}), 404

    output_dir = os.path.join(BASE_DIR, job_id, 'output')
    os.makedirs(output_dir, exist_ok=True)

    file_list = []
    for fname in os.listdir(job['upload_dir']):
        file_list.append(os.path.join(job['upload_dir'], fname))

    job['status'] = 'queued'
    job['progress'] = 0
    job['completed'] = 0
    job['total'] = count
    job['files'] = []
    job['output_dir'] = output_dir

    t = threading.Thread(target=run_job, args=(job, file_list, count, output_dir))
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/status/<job_id>')
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'not found'}), 404

    return jsonify({
        'status': job.get('status'),
        'progress': job.get('progress', 0),
        'completed': job.get('completed', 0),
        'total': job.get('total', 0),
        'count': job.get('count', 0),
        'last_combo': job.get('last_combo', ''),
        'error': job.get('error', ''),
        'summary': job.get('summary', {}),
        'max_combinations': job.get('max_combinations', 1),
    })


@app.route('/download/<job_id>/<int:idx>')
def download(job_id, idx):
    job = jobs.get(job_id)
    if not job or not job.get('files'):
        return 'not found', 404

    files = job['files']
    if idx < 1 or idx > len(files):
        return 'invalid', 404

    path = files[idx - 1]
    if not os.path.exists(path):
        return 'missing', 404

    return send_file(path, as_attachment=True,
                     download_name=f'varvid_{idx:02d}.mp4',
                     mimetype='video/mp4')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
