@echo off
title ShadowForge Launcher
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo First time? Double-click INSTALL_AND_RUN.bat instead.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo main.py not found. Open the ShadowForge project folder first.
    pause
    exit /b 1
)

start "" "venv\Scripts\pythonw.exe" main.py
exit