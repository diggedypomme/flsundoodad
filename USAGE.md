# FLSUN QQS-Pro UI Usage Guide

## What You Have

A complete web-based control interface for your FLSUN QQS-Pro 3D printer that communicates via the built-in MKS WiFi module.

## Quick Start

1. **Start the server:**
   ```bash
   # Double-click runme.bat (Windows)
   # Or run: python app.py
   ```

2. **Open in browser:**
   ```
   http://localhost:5000
   ```

3. **Use the interface:**
   - **Status monitoring** updates every 2 seconds automatically
   - **Temperature control** - set and monitor hotend/bed temps
   - **Movement** - home axes, move Z up/down
   - **Print control** - pause, resume, stop prints
   - **File management** - upload gcode files, browse files on printer
   - **Terminal** - send raw G-code commands

## Features

### Real-time Monitoring
- Printer state (IDLE/PRINTING/PAUSED)
- Current temperatures (hotend & bed)
- Current position (X, Y, Z)
- Firmware info

### Temperature Control
- Set hotend temperature (0-300°C)
- Set bed temperature (0-120°C)
- Quick off buttons

### Movement
- Home all axes or individually (X, Y, Z)
- Quick Z movement (+/- 10mm, 1mm, 0.1mm)

### Print Management
- Upload G-code files (drag & drop or click)
- List files on printer SD card
- Start, pause, resume, stop prints

### G-code Terminal
- Send any G-code command
- View responses
- Command history

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

### Change Printer IP
Set environment variable:
```bash
# Windows
set FLSUN_HOST=192.168.0.123
python app.py

# Linux/Mac
export FLSUN_HOST=192.168.0.123
python app.py
```

Or edit [`app.py`](app.py:22) line 22:
```python
PRINTER_HOST = '192.168.0.123'  # Change this
```

### Change Port
Default port for web interface: `5000`
Default port for printer TCP: `8080`

To change web interface port, edit [`app.py`](app.py:260) line 260:
```python
app.run(host='0.0.0.0', port=5000, debug=True)  # Change port here
```

## Troubleshooting

### Can't connect to printer
1. Check printer is on
2. Verify IP address (check printer LCD or router)
3. Ensure printer WiFi is connected to same network
4. Test with: `ping 192.168.0.69`

### Upload fails
- Make sure file is .gcode, .gco, or .g
- Check printer is IDLE (not printing)
- File size under 100MB

### Commands not working
- Check printer status is not in error state
- Try emergency stop if printer is halted
- Restart printer if needed

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

## File Structure

```
flsun_ui/
├── app.py              # Flask web server
├── flsun/              # Python library
│   ├── __init__.py
│   ├── client.py       # Main FlsunClient class
│   └── exceptions.py   # Custom exceptions
├── templates/
│   └── index.html      # Web interface
├── docs/
│   └── api.md          # API documentation
├── uploads/            # Temporary upload folder
├── requirements.txt    # Python dependencies
├── runme.bat           # Windows startup script
├── start.sh            # Linux/Mac startup script
└── README.md           # Project readme
```

## Support

For issues or questions:
1. Check the logs in console where Flask is running
2. Try commands directly via TCP (port 8080)
3. Verify printer firmware is MKS WiFi compatible

Happy printing!
