#!/usr/bin/env python3
"""Quick test of TCP port 8080 on the printer."""
import socket
import time

HOST = '192.168.0.69'
PORT = 8080

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3)

try:
    print(f"Connecting to {HOST}:{PORT}...")
    s.connect((HOST, PORT))
    print("Connected!")

    # Send M115 (firmware info)
    print("\nSending: M115")
    s.send(b'M115\n')
    time.sleep(0.5)

    data = s.recv(4096)
    print(f"Response: {data.decode('utf-8', errors='ignore')}")

    # Try M997 (printer state)
    print("\nSending: M997")
    s.send(b'M997\n')
    time.sleep(0.5)

    data = s.recv(4096)
    print(f"Response: {data.decode('utf-8', errors='ignore')}")

finally:
    s.close()
