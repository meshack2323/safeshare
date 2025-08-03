# SafeShare - Flask Backend (with Text & File Encryption)

from flask import Flask, request, jsonify, send_file, abort, render_template
from werkzeug.utils import secure_filename
import os, uuid, time
from threading import Thread
from cryptography.fernet import Fernet

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')

# Configurations
UPLOAD_FOLDER = 'temp_files'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
LIFETIME = 3600  # 1 hour in seconds
CLEANUP_INTERVAL = 300  # Clean every 5 mins

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Store metadata in memory (message_id: info)
storage = {}

# Background file/message cleaner
def cleaner():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        now = time.time()
        expired = [key for key, info in storage.items() if now > info['timestamp'] + LIFETIME]
        for key in expired:
            if 'filepath' in storage[key]:
                try: os.remove(storage[key]['filepath'])
                except: pass
            del storage[key]

Thread(target=cleaner, daemon=True).start()

@app.route('/')
def home():
    return render_template('index.html')

# Generate encryption key
@app.route('/api/key', methods=['GET'])
def get_key():
    key = Fernet.generate_key().decode()
    return jsonify({"key": key})

# Upload message or file
@app.route('/api/upload', methods=['POST'])
def upload():
    data_type = request.form.get('type')  # 'text' or 'file'
    encrypted = request.form.get('encrypted')  # encrypted string (for text)
    passcode = request.form.get('passcode')

    msg_id = str(uuid.uuid4())

    info = {
        'timestamp': time.time(),
        'passcode': passcode or ''
    }

    if data_type == 'text':
        info['encrypted'] = encrypted

    elif data_type == 'file':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        f = request.files['file']
        if f.filename == '':
            return jsonify({'error': 'Empty filename'}), 400

        filename = secure_filename(f.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], msg_id + '_' + filename)
        f.save(path)
        info['filepath'] = path
        info['filename'] = filename
    else:
        return jsonify({'error': 'Invalid type'}), 400

    storage[msg_id] = info
    return jsonify({'link': f'/view/{msg_id}'})

# View and auto-destroy
@app.route('/view/<msg_id>', methods=['GET'])
def view_page(msg_id):
    return render_template('view.html', msg_id=msg_id)

@app.route('/api/view/<msg_id>', methods=['POST'])
def view(msg_id):
    if msg_id not in storage:
        return jsonify({'error': 'Expired or invalid link'}), 404

    input_passcode = request.form.get('passcode', '')
    info = storage[msg_id]

    if info['passcode'] and input_passcode != info['passcode']:
        return jsonify({'error': 'Incorrect passcode'}), 403

    result = {}

    if 'encrypted' in info:
        result['type'] = 'text'
        result['data'] = info['encrypted']

    elif 'filepath' in info:
        result['type'] = 'file'
        result['filename'] = info['filename']

    # Auto-delete after retrieval
    if 'filepath' in info:
        try: os.remove(info['filepath'])
        except: pass
    del storage[msg_id]

    return jsonify(result)

# Serve file download (not shown on UI directly)
@app.route('/api/download/<msg_id>', methods=['GET'])
def download(msg_id):
    return abort(403)  # Downloads not allowed via direct link

if __name__ == '__main__':

    import os

    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)
