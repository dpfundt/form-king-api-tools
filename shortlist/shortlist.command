#!/usr/bin/env bash
# Double-click launcher for macOS / Linux.
# Runs from the directory this script lives in.

cd "$(dirname "$0")" || exit 1

# ── Activate virtual environment if one exists ────────────────────────────────
if [ -f ".venv/bin/activate" ]; then
    source ".venv/bin/activate"
elif [ -f "venv/bin/activate" ]; then
    source "venv/bin/activate"
fi

# ── Check Python is available ─────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo ""
    echo "ERROR: python3 was not found on your PATH."
    echo ""
    echo "Please install Python 3.9+ from https://www.python.org/downloads/"
    echo ""
    read -rp "Press Enter to close..."
    exit 1
fi

python3 shortlist.py

echo ""
read -rp "Press Enter to close..."
