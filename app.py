"""Flask web interface for FLSUN QQS-Pro control — v2.

Differences from app.py, based on cross-referencing the proven
MKS_WIFI_PS_upload.pyw tool (documentation/PRINTERUPLOAD/uploader/):

- Uploads are refused while a print is running (the mainboard writes the SD
  card over the same serial link it reads gcode from, so mid-print uploads
  always end in a transfer error on the printer).
- Every printer-touching endpoint is gated while an upload is in progress,
  not just status/temperature/position. Emergency stop is deliberately left
  ungated.
- The gcode TCP connection is closed for the duration of the upload and
  reopened afterwards, matching the old tool which only connected to port
  8080 after the transfer finished.
- The file is streamed to the printer in paced chunks (size and delay are
  configurable per-upload) instead of one full-speed blob, mimicking the old
  tool's throttled BufferReader that the ESP8266 module could keep up with.
- No more fixed 120s upload timeout.
- Server-side upload progress is exposed at /api/upload/progress for the UI's
  progress bar (the browser->Flask leg is instant on a LAN; the Flask->printer
  leg is the slow part worth showing).
- Debug mode off, so the auto-reloader can't restart the server mid-print.
"""

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from functools import wraps
from pathlib import Path
import json
import os
import threading
import time
import requests
from flsun import FlsunClient
from flsun.exceptions import FlsunError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'flsun-ui-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Global printer client (created on first request)
printer = None

# Set while a file upload is in progress. The MKS WiFi module and the gcode
# TCP port both talk to the mainboard over one serial link, so any traffic
# during a large SD write can corrupt the transfer ("transfer error").
upload_active = threading.Event()

# Progress of the current (or last) upload, read by /api/upload/progress.
# Guarded by _progress_lock; the upload runs in one Flask worker thread while
# the UI polls from others.
_progress_lock = threading.Lock()
upload_progress = {
    'active': False,
    'stage': 'idle',      # idle|saving|preparing|uploading|finalizing|done|error
    'filename': '',
    'total': 0,
    'sent': 0,
    'started': 0.0,
    'error': None,
}

# Printer configuration. Precedence: config2.json (set from the UI) beats the
# environment, which beats the built-in default.
CONFIG_PATH = Path(__file__).parent / 'config2.json'

PRINTER_HOST = os.environ.get('FLSUN_HOST', '192.168.0.69')
PRINTER_PORT = int(os.environ.get('FLSUN_PORT', '8080'))


def _load_config():
    """Apply persisted settings on top of the env/default values."""
    global PRINTER_HOST, PRINTER_PORT
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
        PRINTER_HOST = str(cfg.get('printer_host', PRINTER_HOST)).strip() or PRINTER_HOST
        PRINTER_PORT = int(cfg.get('printer_port', PRINTER_PORT))
    except FileNotFoundError:
        pass
    except (ValueError, OSError) as e:
        print(f"Warning: could not read {CONFIG_PATH.name}: {e}")


def _save_config():
    CONFIG_PATH.write_text(json.dumps(
        {'printer_host': PRINTER_HOST, 'printer_port': PRINTER_PORT}, indent=2))


_load_config()

# Upload pacing defaults (overridable per-upload from the UI form)
DEFAULT_CHUNK_KB = int(os.environ.get('FLSUN_CHUNK_KB', '8'))
DEFAULT_CHUNK_DELAY_MS = int(os.environ.get('FLSUN_CHUNK_DELAY_MS', '20'))


def _set_progress(**fields):
    with _progress_lock:
        upload_progress.update(fields)


def get_printer():
    """Get or create printer client."""
    global printer
    if printer is None:
        printer = FlsunClient(host=PRINTER_HOST, port=PRINTER_PORT, auto_connect=False)
    if not printer.is_connected():
        try:
            printer.connect()
        except FlsunError:
            pass
    return printer


def blocked_during_upload(f):
    """Reject printer-touching requests while an upload is running."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if upload_active.is_set():
            return jsonify({'status': 'busy', 'message': 'upload in progress'}), 503
        return f(*args, **kwargs)
    return wrapper


class PacedReader:
    """File-like wrapper that feeds bytes to requests in paced chunks.

    Defines __len__ so requests sends a normal Content-Length body (the MKS
    module does not understand chunked transfer encoding), but hands the data
    out at most chunk_size bytes per read with a sleep between chunks — the
    same accidental throttling the old Tk uploader got from redrawing its
    progress bar every 8KB, which the ESP8266's WiFi->serial bridge needs.
    """

    def __init__(self, data, chunk_size, delay, progress_cb):
        self._buf = memoryview(data)
        self._len = len(data)
        self._pos = 0
        self._chunk = max(1, chunk_size)
        self._delay = max(0.0, delay)
        self._since_sleep = 0
        self._cb = progress_cb

    def __len__(self):
        return self._len

    def read(self, size=-1):
        if self._pos >= self._len:
            return b''
        if size is None or size < 0:
            size = self._len - self._pos
        n = min(size, self._chunk, self._len - self._pos)
        chunk = bytes(self._buf[self._pos:self._pos + n])
        self._pos += n
        self._cb(self._pos)
        self._since_sleep += n
        if self._delay > 0 and self._pos < self._len and self._since_sleep >= self._chunk:
            time.sleep(self._delay)
            self._since_sleep = 0
        return chunk


@app.route('/')
def index():
    """Main control interface."""
    return render_template('index2.html',
                           default_chunk_kb=DEFAULT_CHUNK_KB,
                           default_chunk_delay_ms=DEFAULT_CHUNK_DELAY_MS)


@app.route('/api/status')
@blocked_during_upload
def api_status():
    """Get printer status."""
    try:
        p = get_printer()
        status = p.get_status()
        return jsonify({'status': 'ok', 'printer_status': status})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/temperature')
@blocked_during_upload
def api_temperature():
    """Get current temperatures."""
    try:
        p = get_printer()
        temps = p.get_temperature()
        return jsonify({'status': 'ok', 'temperature': temps})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/position')
@blocked_during_upload
def api_position():
    """Get current position."""
    try:
        p = get_printer()
        pos = p.get_position()
        return jsonify({'status': 'ok', 'position': pos})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/firmware')
@blocked_during_upload
def api_firmware():
    """Get firmware info."""
    try:
        p = get_printer()
        info = p.get_firmware_info()
        return jsonify({'status': 'ok', 'firmware': info})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/files')
@blocked_during_upload
def api_files():
    """Get file list from printer."""
    try:
        p = get_printer()
        files = p.get_file_list()
        return jsonify({'status': 'ok', 'files': files})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/home', methods=['POST'])
@blocked_during_upload
def api_home():
    """Home printer axes."""
    try:
        p = get_printer()
        data = request.get_json() or {}
        axes = data.get('axes', None)
        p.home(axes=axes)
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/move', methods=['POST'])
@blocked_during_upload
def api_move():
    """Move printer."""
    try:
        p = get_printer()
        data = request.get_json()
        x = data.get('x')
        y = data.get('y')
        z = data.get('z')
        feedrate = data.get('feedrate')
        p.move(x=x, y=y, z=z, feedrate=feedrate)
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/extrude', methods=['POST'])
@blocked_during_upload
def api_extrude():
    """Extrude or retract filament."""
    try:
        p = get_printer()
        data = request.get_json()
        amount = float(data.get('amount', 0))

        # Set to relative positioning for extrusion
        p.send_command('M83')
        p.send_command(f'G1 E{amount} F300')
        p.send_command('M82')

        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/temperature/hotend', methods=['POST'])
@blocked_during_upload
def api_set_hotend_temp():
    """Set hotend temperature."""
    try:
        p = get_printer()
        data = request.get_json()
        temp = float(data.get('temp', 0))
        wait = data.get('wait', False)
        p.set_hotend_temp(temp, wait=wait)
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/temperature/bed', methods=['POST'])
@blocked_during_upload
def api_set_bed_temp():
    """Set bed temperature."""
    try:
        p = get_printer()
        data = request.get_json()
        temp = float(data.get('temp', 0))
        wait = data.get('wait', False)
        p.set_bed_temp(temp, wait=wait)
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/print/start', methods=['POST'])
@blocked_during_upload
def api_start_print():
    """Start printing file."""
    try:
        p = get_printer()
        data = request.get_json()
        filename = data.get('filename')
        p.start_print(filename=filename)
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/print/pause', methods=['POST'])
@blocked_during_upload
def api_pause_print():
    """Pause current print."""
    try:
        p = get_printer()
        p.pause_print()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/print/resume', methods=['POST'])
@blocked_during_upload
def api_resume_print():
    """Resume paused print."""
    try:
        p = get_printer()
        p.resume_print()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/print/stop', methods=['POST'])
@blocked_during_upload
def api_stop_print():
    """Stop current print."""
    try:
        p = get_printer()
        p.stop_print()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/command', methods=['POST'])
@blocked_during_upload
def api_send_command():
    """Send raw G-code command."""
    try:
        p = get_printer()
        data = request.get_json()
        command = data.get('command', '')
        response = p.send_command(command)
        return jsonify({'status': 'ok', 'response': response})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Current printer connection settings."""
    return jsonify({'status': 'ok',
                    'settings': {'printer_host': PRINTER_HOST,
                                 'printer_port': PRINTER_PORT}})


@app.route('/api/settings', methods=['POST'])
@blocked_during_upload
def api_set_settings():
    """Change printer IP/port and persist to config2.json."""
    global printer, PRINTER_HOST, PRINTER_PORT
    data = request.get_json() or {}

    host = str(data.get('printer_host', PRINTER_HOST)).strip()
    if not host:
        return jsonify({'status': 'error', 'message': 'Printer IP/hostname cannot be empty'}), 400
    try:
        port = int(data.get('printer_port', PRINTER_PORT))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Port must be a number'}), 400
    if not 1 <= port <= 65535:
        return jsonify({'status': 'error', 'message': 'Port must be 1-65535'}), 400

    PRINTER_HOST = host
    PRINTER_PORT = port
    try:
        _save_config()
    except OSError as e:
        return jsonify({'status': 'error', 'message': f'Could not save config: {e}'}), 500

    # Drop the old connection; the next request reconnects to the new address.
    if printer is not None:
        printer.disconnect()
        printer = None

    return jsonify({'status': 'ok',
                    'settings': {'printer_host': PRINTER_HOST,
                                 'printer_port': PRINTER_PORT}})


@app.route('/api/upload/progress')
def api_upload_progress():
    """Progress of the current upload (does not touch the printer)."""
    with _progress_lock:
        prog = dict(upload_progress)
    percent = (prog['sent'] * 100.0 / prog['total']) if prog['total'] else 0.0
    elapsed = (time.time() - prog['started']) if prog['started'] else 0.0
    rate = (prog['sent'] / elapsed) if elapsed > 0.5 else 0.0
    prog.update({'percent': round(percent, 1), 'rate_bps': int(rate)})
    return jsonify({'status': 'ok', 'progress': prog})


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Upload G-code file to printer, paced for the MKS WiFi module."""
    if upload_active.is_set():
        return jsonify({'status': 'error', 'message': 'Another upload is already in progress'}), 409

    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        if not file.filename.lower().endswith(('.gcode', '.gco', '.g')):
            return jsonify({'status': 'error', 'message': 'Invalid file type. Only .gcode, .gco, .g allowed'}), 400

        # Per-upload pacing options (fall back to server defaults)
        try:
            chunk_kb = int(request.form.get('chunk_kb', DEFAULT_CHUNK_KB))
            chunk_delay_ms = int(request.form.get('chunk_delay_ms', DEFAULT_CHUNK_DELAY_MS))
        except ValueError:
            return jsonify({'status': 'error', 'message': 'chunk_kb and chunk_delay_ms must be integers'}), 400
        chunk_kb = min(max(chunk_kb, 1), 64)
        chunk_delay_ms = min(max(chunk_delay_ms, 0), 2000)

        filename = secure_filename(file.filename)
        temp_path = app.config['UPLOAD_FOLDER'] / filename

        _set_progress(active=True, stage='saving', filename=filename,
                      total=0, sent=0, started=time.time(), error=None)
        file.save(temp_path)

        upload_active.set()
        try:
            _set_progress(stage='preparing')

            # Never upload mid-print: the mainboard can't write the SD card it
            # is printing from, so the transfer always ends in an error.
            p = get_printer()
            try:
                state = p.get_status()
            except FlsunError:
                # One retry after a reconnect before giving up.
                p.disconnect()
                p = get_printer()
                state = p.get_status()  # raises FlsunError if still unreachable
            if state.upper() in ('PRINTING', 'PAUSED'):
                return jsonify({'status': 'error',
                                'message': f'Printer is {state} — uploads during a print always fail. '
                                           'Wait for the print to finish.'}), 409

            # Close the gcode TCP connection for the transfer. The proven old
            # uploader had no port-8080 connection open while uploading, and
            # the ESP8266 copes best serving a single connection.
            p.disconnect()

            file_content = temp_path.read_bytes()
            total = len(file_content)
            _set_progress(stage='uploading', total=total, sent=0, started=time.time())

            reader = PacedReader(
                file_content,
                chunk_size=chunk_kb * 1024,
                delay=chunk_delay_ms / 1000.0,
                progress_cb=lambda sent: _set_progress(sent=sent),
            )

            # Same request shape as the proven MKS-WIFI_PS_uploader: POST to
            # /upload with the target name in the X-Filename query parameter.
            # Generous read timeout instead of the old fixed 120s — the module
            # transfers at tens of KB/s, so big files legitimately take many
            # minutes.
            url = f'http://{PRINTER_HOST}/upload'
            response = requests.post(
                url,
                params={'X-Filename': filename},
                data=reader,
                headers={'Content-Type': 'application/octet-stream',
                         'Connection': 'keep-alive'},
                timeout=(10, 600),
            )

            if response.status_code != 200:
                try:
                    error_msg = response.json().get('err', f'HTTP {response.status_code}')
                except Exception:
                    error_msg = f'HTTP {response.status_code}'
                raise FlsunError(f'Upload failed: {error_msg}')

            # Reconnect and re-init the SD card so the fresh file shows up in
            # M20 immediately (the mainboard caches the directory).
            _set_progress(stage='finalizing')
            p = get_printer()
            try:
                p.send_command('M21')
            except FlsunError:
                pass

        finally:
            upload_active.clear()
            if temp_path.exists():
                temp_path.unlink()

        _set_progress(active=False, stage='done')
        return jsonify({'status': 'ok', 'filename': filename})

    except requests.RequestException as e:
        _set_progress(active=False, stage='error', error=str(e))
        return jsonify({'status': 'error', 'message': f'Upload failed: {e}'}), 500
    except FlsunError as e:
        _set_progress(active=False, stage='error', error=str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        _set_progress(active=False, stage='error', error=str(e))
        return jsonify({'status': 'error', 'message': f'Upload error: {str(e)}'}), 500


@app.route('/api/emergency-stop', methods=['POST'])
def api_emergency_stop():
    """Emergency stop. Deliberately NOT gated during uploads — if you need to
    stop the printer, a corrupted upload is the lesser problem."""
    try:
        p = get_printer()
        p.emergency_stop()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print("Starting FLSUN UI server (v2)...")
    print(f"Printer: {PRINTER_HOST}:{PRINTER_PORT}")
    print("Access at: http://localhost:5000")
    # debug=False: the auto-reloader must never restart this server mid-print,
    # and mid-upload a restart would corrupt the transfer.
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
