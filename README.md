# FLSUN QQS-Pro Control Tool

Python tool for controlling the FLSUN QQS-Pro 3D printer via its built-in MKS WiFi module (ESP8266).

## Hardware

- **Printer**: FLSUN QQS-Pro
- **WiFi Module**: MKS WiFi (ESP8266)
- **Firmware**: MKS Robin WiFi

## Features

- Send G-code commands over TCP (port 8080)
- Query printer status, temperature, and position
- Upload G-code files via HTTP (port 80)
- Monitor print progress
- Control printer operations (home, move, heat, pause, resume, stop)

## Installation

1. **Clone or download this repository**

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### Web Interface (Recommended)

1. **Start the web server:**
   - Windows: Double-click [`runme.bat`](runme.bat)
   - Linux/Mac: `./start.sh` or `python app.py`

2. **Open your browser to:** http://localhost:5000

3. **Control your printer** through the web interface with:
   - Real-time status monitoring
   - Temperature control
   - Movement controls
   - File upload and management
   - G-code terminal

### Python API

```python
from flsun import FlsunClient

# Connect to printer
printer = FlsunClient('192.168.0.69')

# Get printer status
status = printer.get_status()
print(f"Printer state: {status}")

# Get temperature
temp = printer.get_temperature()
print(f"Bed: {temp['bed']}°C, Hotend: {temp['hotend']}°C")

# Set hotend temperature
printer.set_hotend_temp(200)

# Home all axes
printer.home()

# Upload and print a file
printer.upload_file('model.gcode')
printer.start_print('model.gcode')

# Disconnect
printer.close()
```

## Available Interfaces

### Port 8080 (TCP) - G-code Commands
Raw G-code command interface. All standard G-code commands are supported.

### Port 80 (HTTP) - Web Interface
- `/` - WiFi configuration page
- `/upload` - File upload (requires `X-Filename` header)
- `/update_cfg` - WiFi settings
- `/update_sketch` - Firmware update
- `/update_spiffs` - Web view update

## MKS WiFi Custom Commands

| Command | Description |
|---------|-------------|
| M115 | Get firmware information |
| M997 | Get printer state (IDLE/PRINTING/PAUSED) |
| M994 | Get current file name and size |
| M992 | Get elapsed print time |
| M991 | Get temperature (alternative to M105) |
| M20 [path] | List files in directory |

## API Reference

See [docs/api.md](docs/api.md) for full API documentation.

## CLI Usage

```bash
# Get printer status
python -m flsun status

# Home all axes
python -m flsun home

# Get temperature
python -m flsun temp

# Upload and print file
python -m flsun upload model.gcode --print

# Monitor print progress
python -m flsun monitor
```

## Network Configuration

The printer's IP address can be configured via:
1. The web interface at the printer's current IP
2. Connecting to the printer's AP mode (default: 192.168.0.1)

## License

MIT
