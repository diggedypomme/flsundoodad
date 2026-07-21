# FLSUN QQS-Pro Control Tool

Python tool for controlling the FLSUN QQS-Pro 3D printer via its built-in MKS WiFi module (ESP8266).

## Hardware

- **Printer**: FLSUN QQS-Pro
- **WiFi Module**: MKS WiFi (ESP8266)
- **Firmware**: MKS Robin WiFi

## Features

### Core Functionality
- Send G-code commands over TCP (port 8080)
- Query printer status, temperature, and position
- Upload G-code files via HTTP (port 80) with throttled transfers
- Monitor print progress with real-time updates
- Control printer operations (home, move, heat, pause, resume, stop)

### Web Interface
- Real-time status monitoring (updates every 2 seconds)
- Temperature control for hotend and bed
- Movement controls with quick Z-axis adjustments
- File upload with progress bar and configurable transfer rate
- Drag-and-drop file upload support
- File management (browse and print files on SD card)
- G-code terminal for direct command input
- Configurable printer IP address (persisted to config2.json)

### Upload Reliability
- **Paced file transfers** to prevent ESP8266 WiFi module overload
- **Upload progress tracking** showing transfer speed and completion
- **Print-state detection** - refuses uploads during active prints
- **Configurable chunk size and delay** for optimal transfer speed
- **Automatic retry** with reconnection on transient errors

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

3. **Configure printer IP:** Enter your printer's IP address in the Status panel and click Save

4. **Control your printer** through the web interface:
   - Real-time status monitoring (auto-updates every 2 seconds)
   - Temperature control with presets
   - Movement controls and quick Z-axis adjustments
   - File upload with progress bar (drag & drop supported)
   - Browse and print files from SD card
   - G-code terminal for direct commands

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

## Configuration

### Printer IP Address

Configure the printer IP in the web interface (Status panel) or via environment variable:

```bash
# Windows
set FLSUN_HOST=192.168.0.123
python app.py

# Linux/Mac
export FLSUN_HOST=192.168.0.123
python app.py
```

The IP address set in the web UI is saved to `config2.json` and persists across restarts.

### Upload Transfer Rate

If uploads fail or are unreliable, adjust the transfer settings in the web interface:
- **Chunk size**: Amount of data sent at once (default: 8KB)
- **Chunk delay**: Pause between chunks (default: 20ms)

Increase the delay (e.g., 50-100ms) if the printer's WiFi module can't keep up.

## License

MIT
