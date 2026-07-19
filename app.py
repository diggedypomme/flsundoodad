"""Flask web interface for FLSUN QQS-Pro control."""

from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from pathlib import Path
import os
from flsun import FlsunClient
from flsun.exceptions import FlsunError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'flsun-ui-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = Path(__file__).parent / 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

# Ensure upload folder exists
app.config['UPLOAD_FOLDER'].mkdir(exist_ok=True)

# Global printer client (will be created on first request)
printer = None

# Printer configuration
PRINTER_HOST = os.environ.get('FLSUN_HOST', '192.168.0.69')
PRINTER_PORT = int(os.environ.get('FLSUN_PORT', '8080'))


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


@app.route('/')
def index():
    """Main control interface."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get printer status."""
    try:
        p = get_printer()
        status = p.get_status()
        return jsonify({'status': 'ok', 'printer_status': status})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/temperature')
def api_temperature():
    """Get current temperatures."""
    try:
        p = get_printer()
        temps = p.get_temperature()
        return jsonify({'status': 'ok', 'temperature': temps})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/position')
def api_position():
    """Get current position."""
    try:
        p = get_printer()
        pos = p.get_position()
        return jsonify({'status': 'ok', 'position': pos})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/firmware')
def api_firmware():
    """Get firmware info."""
    try:
        p = get_printer()
        info = p.get_firmware_info()
        return jsonify({'status': 'ok', 'firmware': info})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/files')
def api_files():
    """Get file list from printer."""
    try:
        p = get_printer()
        files = p.get_file_list()
        return jsonify({'status': 'ok', 'files': files})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/home', methods=['POST'])
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
def api_extrude():
    """Extrude or retract filament."""
    try:
        p = get_printer()
        data = request.get_json()
        amount = float(data.get('amount', 0))

        # Set to relative positioning for extrusion
        p.send_command('M83')
        # Extrude (G1 E with amount)
        p.send_command(f'G1 E{amount} F300')
        # Back to absolute positioning
        p.send_command('M82')

        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/temperature/hotend', methods=['POST'])
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
def api_pause_print():
    """Pause current print."""
    try:
        p = get_printer()
        p.pause_print()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/print/resume', methods=['POST'])
def api_resume_print():
    """Resume paused print."""
    try:
        p = get_printer()
        p.resume_print()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/print/stop', methods=['POST'])
def api_stop_print():
    """Stop current print."""
    try:
        p = get_printer()
        p.stop_print()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/command', methods=['POST'])
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


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Upload G-code file to printer."""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400

        # Validate file extension
        if not file.filename.lower().endswith(('.gcode', '.gco', '.g')):
            return jsonify({'status': 'error', 'message': 'Invalid file type. Only .gcode, .gco, .g allowed'}), 400

        # Save temporarily
        filename = secure_filename(file.filename)
        temp_path = app.config['UPLOAD_FOLDER'] / filename
        file.save(temp_path)

        # Upload to printer
        p = get_printer()
        p.upload_file(temp_path, filename=filename)

        # Clean up temp file
        temp_path.unlink()

        return jsonify({'status': 'ok', 'filename': filename})

    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Upload error: {str(e)}'}), 500


@app.route('/api/emergency-stop', methods=['POST'])
def api_emergency_stop():
    """Emergency stop."""
    try:
        p = get_printer()
        p.emergency_stop()
        return jsonify({'status': 'ok'})
    except FlsunError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    print(f"Starting FLSUN UI server...")
    print(f"Printer: {PRINTER_HOST}:{PRINTER_PORT}")
    print(f"Access at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
