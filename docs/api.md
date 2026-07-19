# API Documentation

## FlsunClient API

### Connection Management

#### `FlsunClient(host, port, timeout, auto_connect)`
Create a new client instance.

**Parameters:**
- `host` (str): Printer IP address (default: '192.168.0.69')
- `port` (int): TCP port (default: 8080)
- `timeout` (float): Socket timeout in seconds (default: 5.0)
- `auto_connect` (bool): Auto-connect on init (default: True)

**Example:**
```python
client = FlsunClient('192.168.0.69')
```

#### `connect()`
Manually connect to the printer.

#### `disconnect()` / `close()`
Close connection to the printer.

#### `is_connected()`
Check if connected.

**Returns:** bool

---

### Status & Information

#### `get_status()`
Get current printer state.

**Returns:** str - 'IDLE', 'PRINTING', or 'PAUSED'

#### `get_firmware_info()`
Get firmware information.

**Returns:** str - Firmware name and version

#### `get_temperature()`
Get current temperatures.

**Returns:** dict with keys:
- `hotend`: Current hotend temp
- `hotend_target`: Target hotend temp
- `bed`: Current bed temp
- `bed_target`: Target bed temp

#### `get_position()`
Get current position.

**Returns:** dict with keys: `x`, `y`, `z` (all in mm)

#### `get_file_list(path='')`
Get list of files on SD card.

**Parameters:**
- `path` (str): Directory path (default: root)

**Returns:** list of filenames

#### `get_current_file()`
Get current file being printed.

**Returns:** dict with `filename` and `size`

#### `get_print_time()`
Get elapsed print time.

**Returns:** str in format HH:MM:SS

---

### Temperature Control

#### `set_hotend_temp(temp, wait=False)`
Set hotend temperature.

**Parameters:**
- `temp` (float): Target temperature in Celsius
- `wait` (bool): Wait for temperature to be reached

**Example:**
```python
client.set_hotend_temp(200)  # Set to 200°C
client.set_hotend_temp(200, wait=True)  # Set and wait
```

#### `set_bed_temp(temp, wait=False)`
Set bed temperature.

**Parameters:**
- `temp` (float): Target temperature in Celsius
- `wait` (bool): Wait for temperature to be reached

---

### Movement Control

#### `home(axes=None)`
Home printer axes.

**Parameters:**
- `axes` (str): Axes to home ('X', 'Y', 'Z', or combinations). None = all axes

**Examples:**
```python
client.home()  # Home all axes
client.home('Z')  # Home Z only
client.home('XY')  # Home X and Y
```

#### `move(x=None, y=None, z=None, feedrate=None)`
Move to absolute position.

**Parameters:**
- `x`, `y`, `z` (float): Target positions in mm
- `feedrate` (float): Movement speed in mm/min

**Example:**
```python
client.move(x=100, y=100, z=50, feedrate=3000)
```

---

### Print Control

#### `start_print(filename=None)`
Start printing.

**Parameters:**
- `filename` (str): Optional filename to select and start

#### `pause_print()`
Pause current print.

#### `resume_print()`
Resume paused print.

#### `stop_print()`
Stop current print.

#### `emergency_stop()`
Emergency stop (M112).

**Warning:** Halts printer immediately!

---

### File Operations

#### `select_file(filename)`
Select a file for printing.

**Parameters:**
- `filename` (str): Name of file to select

#### `upload_file(filepath, filename=None)`
Upload G-code file to printer via HTTP.

**Parameters:**
- `filepath` (str|Path): Path to file to upload
- `filename` (str): Optional name to save as on printer

**Returns:** bool - True if successful

**Example:**
```python
client.upload_file('model.gcode')
client.upload_file('/path/to/file.gcode', filename='print.gcode')
```

---

### Raw Commands

#### `send_command(command, wait_for_ok=True, timeout=None)`
Send raw G-code command.

**Parameters:**
- `command` (str): G-code command (without newline)
- `wait_for_ok` (bool): Wait for 'ok' response
- `timeout` (float): Custom timeout for this command

**Returns:** str - Response from printer

**Example:**
```python
response = client.send_command('M115')
```

---

## Flask API Endpoints

All endpoints return JSON with `status` field ('ok' or 'error').

### GET Endpoints

| Endpoint | Description | Response Fields |
|----------|-------------|-----------------|
| `/api/status` | Get printer status | `printer_status` |
| `/api/temperature` | Get temperatures | `temperature` (dict) |
| `/api/position` | Get position | `position` (dict) |
| `/api/firmware` | Get firmware info | `firmware` |
| `/api/files` | Get file list | `files` (array) |

### POST Endpoints

| Endpoint | Description | Body Parameters |
|----------|-------------|-----------------|
| `/api/home` | Home axes | `axes` (optional) |
| `/api/move` | Move printer | `x`, `y`, `z`, `feedrate` |
| `/api/temperature/hotend` | Set hotend temp | `temp`, `wait` |
| `/api/temperature/bed` | Set bed temp | `temp`, `wait` |
| `/api/print/start` | Start print | `filename` |
| `/api/print/pause` | Pause print | - |
| `/api/print/resume` | Resume print | - |
| `/api/print/stop` | Stop print | - |
| `/api/command` | Send raw command | `command` |
| `/api/upload` | Upload file | multipart/form-data |
| `/api/emergency-stop` | Emergency stop | - |

### Examples

**Get temperature:**
```bash
curl http://localhost:5000/api/temperature
```

**Set hotend temperature:**
```bash
curl -X POST http://localhost:5000/api/temperature/hotend \
  -H "Content-Type: application/json" \
  -d '{"temp": 200}'
```

**Upload file:**
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@model.gcode"
```

**Send raw command:**
```bash
curl -X POST http://localhost:5000/api/command \
  -H "Content-Type: application/json" \
  -d '{"command": "M115"}'
```
