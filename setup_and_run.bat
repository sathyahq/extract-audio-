@echo off
title Audio File Scanner — Setup and Run
echo.
echo  ============================================
echo   Audio File Scanner — One-Click Launcher
echo  ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed on this computer.
    echo.
    echo  Please download and install Python first:
    echo.
    echo     https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During installation, check the box that says:
    echo     "Add Python to PATH"
    echo.
    echo  After installing Python, close this window and double-click
    echo  this file again.
    echo.
    pause
    exit /b 1
)

echo  [OK] Python found:
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo  Setting up for first time use...
    echo  Creating virtual environment...
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

REM Install dependencies if needed
pip show mutagen >nul 2>&1
if errorlevel 1 (
    echo  Installing required packages...
    echo  (this includes ffmpeg — may take a minute on first run)
    pip install -r requirements.txt
    if errorlevel 1 (
        echo  [ERROR] Failed to install packages.
        pause
        exit /b 1
    )
    echo  [OK] All packages installed.
    echo.
)

echo  Running Audio File Scanner...
echo  ============================================
echo.

python extract_audio.py

echo.
echo  ============================================
echo  Done! Check this folder for your CSV files.
echo  ============================================
echo.
pause
