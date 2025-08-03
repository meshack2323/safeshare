import os
import uuid
import shutil
import threading
import time
from flask import Flask, request, render_template, send_file, after_this_request
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet

# --- Configuration ---
app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
SHARE_DATA = {}
FILE_LIFESPAN_SECONDS = 3600  # 1 hour

# --- Encryption Key ---
key = Fernet.generate_key()
cipher_suite = Fernet(key)


# --- Background cleaner for expired files/messages ---
def clean_expired():
    while True:
        now = time.time()
        expired = [sid for sid, data in SHARE_DATA.items() if now > data['expiry']]
        for sid in expired:
            if SHARE_DATA[sid]['type'] == 'file':
                try:
                    os.remove(SHARE_DATA[sid]['path'])
                except:
                    pass
            del SHARE_DATA[sid]
        time.sleep(60)


threading.Thread(target=clean_expired, daemon=True).start()


# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        passcode = request.form.get('passcode', '')
        encoded_pass = passcode.encode()
        share_id = str(uuid.uuid4())

        # Check for file upload
        uploaded_file = request.files.get('file')
        if uploaded_file and uploaded_file.filename != '':
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, f"{share_id}_{filename}")
            uploaded_file.save(filepath)

            SHARE_DATA[share_id] = {
                'type': 'file',
                'path': filepath,
                'filename': filename,
                'expiry': time.time() + FILE_LIFESPAN_SECONDS,
                'pass': cipher_suite.encrypt(encoded_pass)
            }

            return render_template('share.html', share_id=share_id)

        # Check for text message
        message = request.form.get('message', '').strip()
        if message != '':
            encrypted_msg = cipher_suite.encrypt(message.encode())

            SHARE_DATA[share_id] = {
                'type': 'text',
                'message': encrypted_msg,
                'expiry': time.time() + FILE_LIFESPAN_SECONDS,
                'pass': cipher_suite.encrypt(encoded_pass)
            }

            return render_template('share.html', share_id=share_id)

        # Neither file nor message was provided
        return "You must upload a file or enter a message.", 400

    return render_template('index.html')
    


@app.route('/view/<share_id>', methods=['GET', 'POST'])
def view(share_id):
    share_data = SHARE_DATA.get(share_id)
    if not share_data:
        return "This share link has expired or does not exist.", 404

    if request.method == 'POST':
        passcode_input = request.form.get('passcode') or ''
        try:
            # Verify passcode
            stored_pass = cipher_suite.decrypt(share_data['pass']).decode()
            if passcode_input != stored_pass:
                return "Invalid passcode.", 403
        except:
            return "Error verifying passcode.", 403

        # Handle text
        if share_data['type'] == 'text':
            try:
                decrypted_msg = cipher_suite.decrypt(share_data['message']).decode()
                del SHARE_DATA[share_id]
                return render_template("view.html", message=decrypted_msg)
            except:
                return "Message decryption failed.", 500

        # Handle file
        if share_data['type'] == 'file':
            filepath = share_data['path']
            filename = share_data['filename']

            @after_this_request
            def remove_file(response):
                try:
                    os.remove(filepath)
                except:
                    pass
                SHARE_DATA.pop(share_id, None)
                return response

            return send_file(filepath, as_attachment=True, download_name=filename)

    return render_template("passcode.html", share_id=share_id)


# --- Start server ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
            
