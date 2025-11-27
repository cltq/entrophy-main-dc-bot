from flask import Flask, send_from_directory, send_file, jsonify
from threading import Thread
import os
import datetime

app = Flask(__name__, static_folder=None)

# Paths to the dashboard static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASH_STATIC = os.path.join(BASE_DIR, 'dashboard', 'static')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'entrophy.log')


@app.route('/')
def home():
    """Serve the dashboard main page (index.html)."""
    index_path = os.path.join(DASH_STATIC, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    return "Dashboard not built", 404


@app.route('/log')
def logs_page():
    """Serve the full logs page (logs.html)."""
    logs_path = os.path.join(DASH_STATIC, 'logs.html')
    if os.path.exists(logs_path):
        return send_file(logs_path)
    return "Logs page not found", 404


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static assets for the dashboard."""
    return send_from_directory(DASH_STATIC, filename)


@app.route('/status')
def status():
    """Return a simple JSON status and a few recent log lines for quick checks."""
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    recent = []
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.read().splitlines()
                recent = lines[-10:]
    except Exception:
        recent = []

    return jsonify({
        'status': 'online',
        'timestamp': now,
        'recent_logs': recent[::-1]
    })


def run():
    # Bind to the PORT env var if present (Render uses $PORT)
    port = int(os.getenv('PORT', '8080'))
    host = os.getenv('KEEPALIVE_HOST', '0.0.0.0')
    # Flask in Render should use 0.0.0.0 and the provided PORT
    app.run(host=host, port=port)


def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
