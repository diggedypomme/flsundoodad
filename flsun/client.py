"""FLSUN QQS-Pro client for communicating with MKS WiFi module."""

import socket
import time
import re
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from .exceptions import FlsunConnectionError, FlsunCommandError, FlsunTimeoutError


class FlsunClient:
    """Client for controlling FLSUN QQS-Pro via MKS WiFi module.

    The printer exposes two interfaces:
    - Port 8080 (TCP): Raw G-code commands
    - Port 80 (HTTP): Web interface and file uploads

    Args:
        host: IP address of the printer (default: 192.168.0.69)
        port: TCP port for G-code commands (default: 8080)
        timeout: Socket timeout in seconds (default: 5)
        auto_connect: Automatically connect on instantiation (default: True)

    Example:
        >>> client = FlsunClient('192.168.0.69')
        >>> status = client.get_status()
        >>> print(status)
        'IDLE'
        >>> client.close()
    """

    DEFAULT_HOST = '192.168.0.69'
    DEFAULT_PORT = 8080
    DEFAULT_TIMEOUT = 5.0

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        auto_connect: bool = True
    ):
        """Initialize the FLSUN client."""
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._connected = False

        if auto_connect:
            self.connect()

    def connect(self) -> None:
        """Establish TCP connection to the printer.

        Raises:
            FlsunConnectionError: If connection fails
        """
        if self._connected:
            return

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self._connected = True
        except socket.error as e:
            self._socket = None
            self._connected = False
            raise FlsunConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}")

    def disconnect(self) -> None:
        """Close the connection to the printer."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            finally:
                self._socket = None
                self._connected = False

    def close(self) -> None:
        """Alias for disconnect()."""
        self.disconnect()

    def is_connected(self) -> bool:
        """Check if connected to printer."""
        return self._connected

    def send_command(
        self,
        command: str,
        wait_for_ok: bool = True,
        timeout: Optional[float] = None
    ) -> str:
        """Send a G-code command to the printer.

        Args:
            command: G-code command to send (without newline)
            wait_for_ok: Wait for 'ok' response (default: True)
            timeout: Custom timeout for this command (default: use socket timeout)

        Returns:
            Response from printer (excluding 'ok')

        Raises:
            FlsunConnectionError: If not connected
            FlsunCommandError: If command fails
            FlsunTimeoutError: If command times out

        Example:
            >>> client.send_command('M115')
            'FIRMWARE_NAME:Robin'
        """
        if not self._connected or not self._socket:
            raise FlsunConnectionError("Not connected to printer")

        # Set custom timeout if provided
        original_timeout = None
        if timeout is not None:
            original_timeout = self._socket.gettimeout()
            self._socket.settimeout(timeout)

        try:
            # Send command
            cmd_bytes = f"{command}\n".encode('utf-8')
            self._socket.sendall(cmd_bytes)

            if not wait_for_ok:
                return ""

            # Read response
            response = self._read_response()
            return response

        except socket.timeout:
            raise FlsunTimeoutError(f"Command '{command}' timed out")
        except socket.error as e:
            self._connected = False
            raise FlsunConnectionError(f"Socket error: {e}")
        finally:
            # Restore original timeout
            if original_timeout is not None and self._socket:
                self._socket.settimeout(original_timeout)

    def _read_response(self, max_lines: int = 100) -> str:
        """Read response from printer until 'ok' is received.

        Args:
            max_lines: Maximum number of lines to read

        Returns:
            Response text (without 'ok')
        """
        if not self._socket:
            raise FlsunConnectionError("Socket not initialized")

        lines = []
        for _ in range(max_lines):
            try:
                data = self._socket.recv(4096)
                if not data:
                    break

                text = data.decode('utf-8', errors='ignore')
                lines.append(text)

                # Check if we received 'ok'
                if 'ok' in text:
                    break
            except socket.timeout:
                break

        # Join all received text
        full_response = ''.join(lines)

        # Remove 'ok' and clean up
        response = full_response.replace('ok', '').strip()
        return response

    def get_status(self) -> str:
        """Get current printer state.

        Returns:
            Printer state: 'IDLE', 'PRINTING', or 'PAUSED'

        Example:
            >>> client.get_status()
            'IDLE'
        """
        response = self.send_command('M997')
        # Response format: "M997 IDLE" or "M997 PRINTING" or "M997 PAUSED"
        match = re.search(r'M997\s+(\w+)', response)
        if match:
            return match.group(1)
        return response.strip()

    def get_firmware_info(self) -> str:
        """Get firmware information.

        Returns:
            Firmware name and version

        Example:
            >>> client.get_firmware_info()
            'FIRMWARE_NAME:Robin'
        """
        return self.send_command('M115').strip()

    def get_temperature(self) -> Dict[str, float]:
        """Get current temperatures.

        Returns:
            Dictionary with 'hotend' and 'bed' temperatures

        Example:
            >>> client.get_temperature()
            {'hotend': 25.0, 'bed': 23.5, 'hotend_target': 0.0, 'bed_target': 0.0}
        """
        # Use M991 (MKS custom) or M105 (standard)
        response = self.send_command('M105')

        temps = {
            'hotend': 0.0,
            'bed': 0.0,
            'hotend_target': 0.0,
            'bed_target': 0.0
        }

        # Parse response like: "T:25.0 /0.0 B:23.5 /0.0"
        # T is hotend, B is bed, /X is target temp
        t_match = re.search(r'T:(\d+\.?\d*)\s*/(\d+\.?\d*)', response)
        b_match = re.search(r'B:(\d+\.?\d*)\s*/(\d+\.?\d*)', response)

        if t_match:
            temps['hotend'] = float(t_match.group(1))
            temps['hotend_target'] = float(t_match.group(2))
        if b_match:
            temps['bed'] = float(b_match.group(1))
            temps['bed_target'] = float(b_match.group(2))

        return temps

    def set_hotend_temp(self, temp: float, wait: bool = False) -> None:
        """Set hotend temperature.

        Args:
            temp: Target temperature in Celsius
            wait: Wait for temperature to be reached (default: False)

        Example:
            >>> client.set_hotend_temp(200)  # Set to 200C
            >>> client.set_hotend_temp(200, wait=True)  # Set and wait
        """
        if wait:
            self.send_command(f'M109 S{temp}', timeout=300)
        else:
            self.send_command(f'M104 S{temp}')

    def set_bed_temp(self, temp: float, wait: bool = False) -> None:
        """Set bed temperature.

        Args:
            temp: Target temperature in Celsius
            wait: Wait for temperature to be reached (default: False)

        Example:
            >>> client.set_bed_temp(60)  # Set to 60C
            >>> client.set_bed_temp(60, wait=True)  # Set and wait
        """
        if wait:
            self.send_command(f'M190 S{temp}', timeout=300)
        else:
            self.send_command(f'M140 S{temp}')

    def home(self, axes: Optional[str] = None) -> None:
        """Home printer axes.

        Args:
            axes: Axes to home ('X', 'Y', 'Z', or combinations like 'XY')
                  If None, homes all axes (default: None)

        Example:
            >>> client.home()  # Home all axes
            >>> client.home('Z')  # Home Z only
            >>> client.home('XY')  # Home X and Y
        """
        if axes is None:
            self.send_command('G28', timeout=60)
        else:
            axes_str = ' '.join([ax for ax in axes.upper() if ax in 'XYZ'])
            self.send_command(f'G28 {axes_str}', timeout=60)

    def move(self, x: Optional[float] = None, y: Optional[float] = None,
             z: Optional[float] = None, feedrate: Optional[float] = None) -> None:
        """Move to absolute position.

        Args:
            x: X position in mm (default: current position)
            y: Y position in mm (default: current position)
            z: Z position in mm (default: current position)
            feedrate: Movement speed in mm/min (default: current feedrate)

        Example:
            >>> client.move(x=100, y=100, z=50, feedrate=3000)
        """
        # Set to absolute positioning
        self.send_command('G90')

        # Build move command
        parts = ['G1']
        if x is not None:
            parts.append(f'X{x}')
        if y is not None:
            parts.append(f'Y{y}')
        if z is not None:
            parts.append(f'Z{z}')
        if feedrate is not None:
            parts.append(f'F{feedrate}')

        if len(parts) > 1:
            self.send_command(' '.join(parts))

    def get_position(self) -> Dict[str, float]:
        """Get current position.

        Returns:
            Dictionary with 'x', 'y', 'z' positions

        Example:
            >>> client.get_position()
            {'x': 100.0, 'y': 100.0, 'z': 50.0}
        """
        response = self.send_command('M114')

        pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}

        # Parse response like: "X:100.00 Y:100.00 Z:50.00 E:0.00"
        x_match = re.search(r'X:(-?\d+\.?\d*)', response)
        y_match = re.search(r'Y:(-?\d+\.?\d*)', response)
        z_match = re.search(r'Z:(-?\d+\.?\d*)', response)

        if x_match:
            pos['x'] = float(x_match.group(1))
        if y_match:
            pos['y'] = float(y_match.group(1))
        if z_match:
            pos['z'] = float(z_match.group(1))

        return pos

    def emergency_stop(self) -> None:
        """Emergency stop (M112).

        Warning: This will halt the printer immediately.
        """
        self.send_command('M112')

    def pause_print(self) -> None:
        """Pause current print (M25)."""
        self.send_command('M25')

    def resume_print(self) -> None:
        """Resume paused print (M24)."""
        self.send_command('M24')

    def stop_print(self) -> None:
        """Stop current print (M0)."""
        self.send_command('M0')

    def get_file_list(self, path: str = '') -> List[str]:
        """Get list of files on SD card.

        Args:
            path: Directory path (default: root)

        Returns:
            List of filenames

        Example:
            >>> client.get_file_list()
            ['model1.gcode', 'model2.gcode', 'calibration.gcode']
        """
        cmd = f'M20 {path}'.strip()
        response = self.send_command(cmd)

        # Parse file list from response
        files = []

        # Skip if response is just "0" or empty
        if not response or response.strip() == '0':
            return files

        for line in response.split('\n'):
            line = line.strip()
            # Skip empty lines, "Begin file list", "End file list", and "0"
            if (line and
                not line.startswith('Begin') and
                not line.startswith('End') and
                line != '0'):
                files.append(line)

        return files

    def select_file(self, filename: str) -> None:
        """Select a file for printing.

        Args:
            filename: Name of the file to select

        Example:
            >>> client.select_file('model.gcode')
        """
        self.send_command(f'M23 {filename}')

    def start_print(self, filename: Optional[str] = None) -> None:
        """Start printing selected file or start specified file.

        Args:
            filename: Optional filename to select and start

        Example:
            >>> client.start_print('model.gcode')
            >>> client.start_print()  # Start previously selected file
        """
        if filename:
            self.select_file(filename)
        self.send_command('M24')

    def get_print_time(self) -> str:
        """Get elapsed print time (M992 - MKS custom).

        Returns:
            Print time as string (format: HH:MM:SS)

        Example:
            >>> client.get_print_time()
            '01:23:45'
        """
        response = self.send_command('M992')
        # Response format: "M992 10:30:20"
        match = re.search(r'M992\s+(\d+:\d+:\d+)', response)
        if match:
            return match.group(1)
        return response.strip()

    def get_current_file(self) -> Dict[str, Any]:
        """Get current file being printed (M994 - MKS custom).

        Returns:
            Dictionary with 'filename' and 'size'

        Example:
            >>> client.get_current_file()
            {'filename': 'model.gcode', 'size': 1024000}
        """
        response = self.send_command('M994')
        # Parse filename and size from response
        info = {'filename': '', 'size': 0}

        # Response format varies, extract what we can
        lines = response.split('\n')
        for line in lines:
            if line.strip():
                info['filename'] = line.strip()
                break

        return info

    def upload_file(self, filepath: Union[str, Path], filename: Optional[str] = None) -> bool:
        """Upload a G-code file to the printer via HTTP.

        Args:
            filepath: Path to the file to upload
            filename: Name to save as on printer (default: use original filename)

        Returns:
            True if upload successful, False otherwise

        Raises:
            FlsunError: If upload fails

        Example:
            >>> client.upload_file('model.gcode')
            >>> client.upload_file('/path/to/file.gcode', filename='print.gcode')
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FlsunCommandError(f"File not found: {filepath}")

        if filename is None:
            filename = filepath.name

        # Read file content
        with open(filepath, 'rb') as f:
            file_content = f.read()

        # Upload via HTTP POST to /upload with X-Filename as URL parameter
        url = f"http://{self.host}/upload"
        params = {
            'X-Filename': filename
        }

        try:
            response = requests.post(url, params=params, data=file_content, timeout=60)

            if response.status_code == 200:
                return True
            else:
                # Try to parse error message
                try:
                    error_data = response.json()
                    error_msg = error_data.get('err', f'HTTP {response.status_code}')
                except Exception:
                    error_msg = f'HTTP {response.status_code}'

                raise FlsunCommandError(f"Upload failed: {error_msg}")

        except requests.RequestException as e:
            raise FlsunConnectionError(f"Upload failed: {e}")

    def __enter__(self):
        """Context manager entry."""
        if not self._connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._connected else "disconnected"
        return f"FlsunClient(host={self.host}, port={self.port}, {status})"
