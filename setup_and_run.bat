@echo off
title Audio File Scanner
echo.
echo  ============================================
echo   Audio File Scanner — One-Click Launcher
echo  ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed.
    echo.
    echo  Download from: https://www.python.org/downloads/
    echo  IMPORTANT: Tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo  [OK] Python found.
echo.

REM Create virtual environment if needed
if not exist "venv\" (
    echo  First time setup...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created.
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install packages if needed
pip show mutagen >nul 2>&1
if errorlevel 1 (
    echo  Installing packages (first time only, may take a minute)...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo  [ERROR] Failed to install packages.
        pause
        exit /b 1
    )
    echo  [OK] Packages installed.
    echo.
)

echo  Starting scanner...
echo  ============================================
echo.

python extract_audio.py

echo.
echo  ============================================
echo  Done! Check this folder for your CSV file.
echo  ============================================
echo.
pause
