@echo off
cd /d "%~dp0"

if not exist ".venv-py313\Scripts\python.exe" (
    echo Setting up Jarvis for the first run...
    py -3.13 -m venv .venv-py313
    if errorlevel 1 (
        echo Python 3.13 was not found. Install Python 3.13 and try again.
        pause
        exit /b 1
    )
    ".venv-py313\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Could not install Jarvis requirements.
        pause
        exit /b 1
    )
)

".venv-py313\Scripts\python.exe" main.py
pause
