from flask import Flask, send_from_directory, send_file, jsonify
from threading import Thread
import os
import datetime

app = Flask(__name__, static_folder=None)

# เส้นทางไปยังไฟล์ static ของแดชบอร์ด
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASH_STATIC = os.path.join(BASE_DIR, 'dashboard', 'static')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'entrophy.log')


@app.route('/')
def home():
    """แสดงหน้าแรกของแดชบอร์ด (index.html)"""
    index_path = os.path.join(DASH_STATIC, 'index.html')
    if os.path.exists(index_path):
        return send_file(index_path)
    return "ไม่ได้สร้างแดชบอร์ด", 404


@app.route('/log')
def logs_page():
    """แสดงหน้า Logs (logs.html)"""
    logs_path = os.path.join(DASH_STATIC, 'logs.html')
    if os.path.exists(logs_path):
        return send_file(logs_path)
    return "ไม่พบหน้า Logs", 404


@app.route('/static/<path:filename>')
def static_files(filename):
    """ให้บริการไฟล์ static ของแดชบอร์ด"""
    return send_from_directory(DASH_STATIC, filename)


@app.route('/status')
def status():
    """คืนค่า JSON สถานะและ log ล่าสุดสองสามบรรทัดเพื่อตรวจสอบอย่างรวดเร็ว"""
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
    # ใช้ PORT จาก environment variable ถ้ามี (Render ใช้ $PORT)
    port = int(os.getenv('PORT', '8080'))
    host = os.getenv('KEEPALIVE_HOST', '0.0.0.0')
    # Flask บน Render ควรใช้ 0.0.0.0 และ PORT ที่ให้มา
    app.run(host=host, port=port)


def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
