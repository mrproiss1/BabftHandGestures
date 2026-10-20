#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "  Roblox Build A Boat Hand Gesture Controller"
echo "========================================================"

PYTHON_BIN="python3"
if ! command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -f "requirements.txt" ]; then
    $PYTHON_BIN -m pip install -r requirements.txt --quiet 2>/dev/null || true
fi

echo "Starting controller..."
exec $PYTHON_BIN BabftHandGestures.py "$@"

