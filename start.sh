#!/bin/bash
echo "Starting FLSUN UI..."
echo ""
cd "$(dirname "$0")"
source venv/bin/activate
python app.py
