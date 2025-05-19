from flask import Flask, request, jsonify
import os
import subprocess
import threading

app = Flask(__name__)
# Where to store the last UUID
UUID_FILE = os.getenv('UUID_FILE', '/data/last_uuid.txt')
# Paths and credentials for analysis
GET_URL_BASE = os.getenv('GET_URL_BASE')
POST_URL_BASE = os.getenv('POST_URL_BASE')
ALLURE_USER = os.getenv('ALLURE_USER')
ALLURE_PASS = os.getenv('ALLURE_PASS')
MODEL_HOST = os.getenv('MODEL_HOST', 'localhost')
MODEL_PORT = os.getenv('MODEL_PORT', '11434')


def run_analysis(uuid):
    cmd = [
        'python', '/app/daily_report.py',
        '--uuid', uuid,
        '--user', ALLURE_USER,
        '--password', ALLURE_PASS,
        '--host', MODEL_HOST,
        '--port', MODEL_PORT
    ]
    env = os.environ.copy()
    env['GET_URL_BASE']  = GET_URL_BASE
    env['POST_URL_BASE'] = POST_URL_BASE

    # один поток, не блокирующий Flask
    threading.Thread(
        target=lambda: subprocess.run(cmd, env=env),
        daemon=True
    ).start()


@app.route('/uuid', methods=['POST'])
def set_uuid():
    payload = request.get_json(silent=True)
    if not payload or 'uuid' not in payload:
        return jsonify({'error': 'Missing uuid field'}), 400

    uuid = payload['uuid']
    # save to file
    os.makedirs(os.path.dirname(UUID_FILE), exist_ok=True)
    with open(UUID_FILE, 'w', encoding='utf-8') as f:
        f.write(uuid)

    # trigger analysis immediately
    if GET_URL_BASE and POST_URL_BASE and ALLURE_USER and ALLURE_PASS:
        run_analysis(uuid)

    return jsonify({'status': 'ok', 'uuid': uuid}), 200

if __name__ == '__main__':
    # start Flask server
    app.run(host='0.0.0.0', port=5000)
