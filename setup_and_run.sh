#!/usr/bin/env bash
# Audio File Scanner — One-Click Launcher (Mac / Linux)

set -e

echo ""
echo "  ============================================"
echo "   Audio File Scanner — One-Click Launcher"
echo "  ============================================"
echo ""

# Move to the folder where this script lives
cd "$(dirname "$0")"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "  [ERROR] Python 3 is not installed on this computer."
    echo ""
    echo "  To install Python:"
    echo ""
    echo "    Mac:   brew install python3"
    echo "           (or download from https://www.python.org/downloads/)"
    echo ""
    echo "    Linux: sudo apt install python3 python3-venv python3-pip"
    echo ""
    echo "  After installing Python, run this script again."
    echo ""
    exit 1
fi

echo "  [OK] Python found: $(python3 --version)"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "  Setting up for first time use..."
    echo "  Creating virtual environment..."
    python3 -m venv venv
    echo "  [OK] Virtual environment created."
    echo ""
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import mutagen" 2>/dev/null; then
    echo "  Installing required packages..."
    pip install -r requirements.txt
    echo "  [OK] Packages installed."
    echo ""
fi

echo "  Running Audio File Scanner..."
echo "  ============================================"
echo ""

python extract_audio.py

echo ""
echo "  ============================================"
echo "  Done! Check this folder for your CSV files."
echo "  ============================================"
echo ""
