@echo off
echo Starting FLSUN UI...
echo.
cd /d "%~dp0"
call venv\Scripts\activate.bat
python app.py
pause
