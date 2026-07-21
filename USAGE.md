# FLSUN QQS-Pro UI - Detailed Usage Guide

> For quick start instructions, see [README.md](README.md)

## Overview

This is a web-based control interface for the FLSUN QQS-Pro 3D printer that communicates via the built-in MKS WiFi module (ESP8266). Version 2 includes improved upload reliability, progress tracking, and configurable transfer rates.

## First-Time Setup

1. **Start the server:**
   - Windows: Double-click `runme.bat`
   - Linux/Mac: `./start.sh` or `python app.py`

2. **Open browser:** http://localhost:5000

3. **Configure printer IP:**
   - Find your printer's IP address (check LCD screen or router)
   - Enter it in the "Printer IP" field in the Status panel
   - Click "Save" - this persists to `config2.json`

4. **Test connection:**
   - The firmware info should appear automatically
   - Status should show "IDLE" or current state

## Web Interface Features

### Status Panel
- **Printer State**: Real-time display of IDLE/PRINTING/PAUSED
- **Firmware Info**: Automatically detected on connection
- **Printer IP**: Configurable and persisted across restarts
- **Position**: Live X, Y, Z coordinates
- **Auto-refresh**: Updates every 2 seconds (pauses during uploads)

### Temperature Control
- Set hotend (0-300°C) and bed (0-120°C) temperatures
- Shows current/target temps (e.g., "205°C / 210°C")
- Quick "Off" buttons to set temp to 0
- Real-time updates

### Movement Controls
- **Homing**: Home all axes or individually (X, Y, Z)
- **Quick Z movements**: ±10mm, ±1mm, ±0.1mm buttons
- **Extrusion**: Extrude/retract filament in 1mm, 5mm, 10mm increments

### File Upload & Management
- **Drag-and-drop** or click to select .gcode/.gco/.g files
- **Progress bar** showing transfer speed and completion
- **Transfer options** (expandable):
  - Chunk size: 1-64 KB (default: 8KB)
  - Chunk delay: 0-2000ms (default: 20ms)
- **Upload protection**: Refuses uploads during active prints
- **Automatic file list refresh** after successful upload

### Print Control
- Browse files on printer SD card
- Start, pause, resume, stop prints
- Confirmation dialogs for destructive actions

### G-code Terminal
- Send any G-code command directly
- View command responses
- Terminal history with scrollback
- Clear button

## Python API

Use the `FlsunClient` class directly in your Python scripts:

```python
from flsun import FlsunClient

# Connect
printer = FlsunClient('192.168.0.69')

# Monitor
print(printer.get_status())
print(printer.get_temperature())
print(printer.get_position())

# Control
printer.set_hotend_temp(200)
printer.set_bed_temp(60)
printer.home()
printer.move(z=50, feedrate=1000)

# Print
printer.upload_file('model.gcode')
printer.start_print('model.gcode')

# Disconnect
printer.close()
```

## Configuration

### Printer IP Address

**Recommended:** Use the web interface Status panel to set and save the IP.

**Alternative:** Use environment variables:
```bash
# Windows
set FLSUN_HOST=192.168.0.123
python app.py

# Linux/Mac
export FLSUN_HOST=192.168.0.123
python app.py
```

**Precedence:** Web UI setting (config2.json) > Environment variable > Default (192.168.0.69)

### Web Server Port

Default: `5000`

To change, edit [app.py](app.py#L567) line 567:
```python
app.run(host='0.0.0.0', port=5000, ...)
```

### Upload Transfer Settings

Configure via the **Transfer options** section in the Upload card:

- **Chunk size (KB)**: Amount of data sent in each chunk
  - Lower = slower but more reliable
  - Higher = faster but may overwhelm WiFi module
  - Range: 1-64 KB, default: 8 KB

- **Chunk delay (ms)**: Pause between chunks
  - Lower = faster transfers
  - Higher = more reliable on slow networks
  - Range: 0-2000ms, default: 20ms

**Recommendation:** If uploads fail with "transfer error", increase delay to 50-100ms.

## Troubleshooting

### Can't connect to printer
1. **Check printer is powered on** and WiFi module is active
2. **Verify IP address**:
   - Check printer LCD screen for WiFi settings
   - Check router DHCP client list
   - Try ping: `ping 192.168.0.69`
3. **Network connection**:
   - Ensure printer WiFi is connected to your network
   - Verify computer and printer are on same network/VLAN
   - Check firewall isn't blocking ports 80 or 8080

### Upload fails with "transfer error"
**Symptoms:** Upload starts but fails partway through, or printer shows error.

**Causes:** The ESP8266 WiFi module can't keep up with the transfer rate.

**Solutions:**
1. **Increase chunk delay**: Try 50ms, then 100ms, then higher
2. **Reduce chunk size**: Try 4KB or 2KB
3. **Check WiFi signal**: Move printer closer to router
4. **Don't use the printer** during upload (no manual control, no print running)
5. **Verify printer is IDLE**: The upload endpoint checks and refuses if printing

### Upload says "Printer is PRINTING — uploads during a print always fail"
**Cause:** The mainboard can't write to the SD card while reading G-code from it.

**Solution:** Wait for the print to finish, then upload.

### Status shows "UPLOAD IN PROGRESS" but I'm not uploading
**Cause:** Another browser tab or user is uploading.

**Solution:** Wait for the other upload to complete, or close all browser tabs and refresh.

### Commands not responding
1. **Check status**: Look for error states or "HALT" condition
2. **Try emergency stop**: May clear a halted state (be careful!)
3. **Check terminal**: Send `M997` to verify connection
4. **Restart printer**: Power cycle if unresponsive
5. **Reconnect web UI**: Refresh the browser page

### Temperature not updating
- Check status isn't showing "busy" or "upload in progress"
- Verify printer is responding in terminal with `M105`
- Auto-refresh pauses during uploads — wait for upload to complete

### File list is empty
1. Click "Refresh File List" button
2. Check SD card is inserted in printer
3. Upload a file — this triggers SD card re-initialization
4. Send `M21` in terminal to re-init SD card manually

## Technical Details

### Ports Used
- **80** (HTTP): Printer web interface, file uploads
- **8080** (TCP): G-code command interface
- **5000** (HTTP): This Flask web UI

### Supported Commands
All standard G-code plus MKS custom commands:
- `M997` - Get printer state
- `M994` - Get current file
- `M992` - Get print time
- `M991` - Get temperature
- `M20` - List files

See [`docs/api.md`](docs/api.md) for full API documentation.

## Advanced Usage

### Monitoring Upload Progress

The UI shows real-time progress with:
- **Percent complete** (0-100%)
- **Bytes transferred** (sent / total)
- **Transfer rate** (KB/s or MB/s)
- **Stage indicators**: saving, preparing, uploading, finalizing

The server tracks progress server-side, so the progress bar reflects the actual printer upload, not just the browser upload.

### Using the Python API

See [README.md](README.md#python-api) for Python API examples.

### Custom G-code Sequences

Use the terminal to send multiple commands:
```
G28        ; Home all axes
G1 Z50     ; Move to Z=50mm
M104 S210  ; Set hotend to 210°C
M140 S60   ; Set bed to 60°C
```

### Environment Variables

Available environment variables:
- `FLSUN_HOST`: Printer IP (default: 192.168.0.69)
- `FLSUN_PORT`: Printer G-code port (default: 8080)
- `FLSUN_CHUNK_KB`: Default upload chunk size (default: 8)
- `FLSUN_CHUNK_DELAY_MS`: Default upload chunk delay (default: 20)

## File Structure

```
flsun_ui/
├── app.py              # Flask web server (v2 with upload improvements)
├── flsun/              # Python library
│   ├── __init__.py
│   ├── client.py       # Main FlsunClient class
│   └── exceptions.py   # Custom exceptions
├── templates/
│   └── index.html      # Web interface with progress tracking
├── docs/
│   └── api.md          # API documentation
├── uploads/            # Temporary upload folder (auto-created, gitignored)
├── config2.json        # Persisted settings (gitignored)
├── requirements.txt    # Python dependencies
├── runme.bat           # Windows startup script
├── start.sh            # Linux/Mac startup script
├── README.md           # Quick start and features
└── USAGE.md            # This detailed usage guide
```

## Support

For issues or questions:
1. Check the logs in console where Flask is running
2. Try commands directly via TCP (port 8080)
3. Verify printer firmware is MKS WiFi compatible

Happy printing!
