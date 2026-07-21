"""Quick test of the FLSUN client."""

from flsun import FlsunClient

# Create client
client = FlsunClient('192.168.0.69')

print("Testing FLSUN Client...")
print(f"Connected: {client.is_connected()}")

# Get status
print(f"\nStatus: {client.get_status()}")

# Get firmware
print(f"Firmware: {client.get_firmware_info()}")

# Get temperature
temps = client.get_temperature()
print(f"\nTemperature:")
print(f"  Hotend: {temps['hotend']}°C (target: {temps['hotend_target']}°C)")
print(f"  Bed: {temps['bed']}°C (target: {temps['bed_target']}°C)")

# Get position
pos = client.get_position()
print(f"\nPosition:")
print(f"  X: {pos['x']} mm")
print(f"  Y: {pos['y']} mm")
print(f"  Z: {pos['z']} mm")

# Close connection
client.close()
print("\nTest complete!")
