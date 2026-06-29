@echo off
title ShadowForge - First Time Setup and Run
color 0B
echo.
echo  ============================================
echo    SHADOWFORGE - Setup and Launch
echo  ============================================
echo.

cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo.
    echo Please install Python 3.10+ from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ERROR] main.py not found.
    echo Make sure you are inside the ShadowForge folder.
    echo This folder should contain: main.py, README.md, requirements.txt
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [2/3] Installing dependencies (first time only, may take 1-2 minutes)...
venv\Scripts\pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [3/3] Launching ShadowForge...
echo.
echo  The app window should open in a few seconds.
echo  If nothing happens, run RUN_SHADOWFORGE.bat instead.
echo.
start "" "venv\Scripts\pythonw.exe" main.py
timeout /t 3 >nul
exit