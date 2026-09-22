@echo off
cd /d "%~dp0"

:: ── Check Python is available ────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python was not found on your PATH.
    echo.
    echo  Please install Python 3.9+ from https://www.python.org/downloads/
    echo  During installation, tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: ── Activate virtual environment if one exists ────────────────────────────────
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: ── Run the engine ─────────────────────────────────────────────────────────────
python shortlist.py

pause
