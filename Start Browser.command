#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: venv not found at $VENV_DIR"
    echo "Please create it with:"
    echo "  python3 -m venv venv"
    exit 1
fi

# venv aktiválás
source "$VENV_DIR/bin/activate"

cd "$SCRIPT_DIR/browser" || exit 1

echo "Using python: $(which python)"
echo "Starting Browser app..."

python -u app.py
