@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo First-time setup — installing dependencies...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
    pause
)
start "" "venv\Scripts\pythonw.exe" main.py
exit