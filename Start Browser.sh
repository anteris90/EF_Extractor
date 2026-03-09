#!/usr/bin/env bash
# Start Browser (Linux / macOS)
# Usage: ./Start\ Browser.sh [path/to/eve_universe.db]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BROWSER_DIR="$SCRIPT_DIR/browser"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

if [ ! -d "$BROWSER_DIR" ]; then
  echo "ERROR: browser directory not found at $BROWSER_DIR"
  exit 1
fi

if [ $# -gt 0 ] && [ -n "$1" ]; then
  export EF_DB_PATH="$1"
  echo "Using EF_DB_PATH=$EF_DB_PATH"
fi

if [ -x "$VENV_PYTHON" ]; then
  PYTHON_CMD="$VENV_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="$(command -v python)"
else
  echo "ERROR: Python was not found. Install python3 or create ./venv first."
  exit 1
fi

cd "$BROWSER_DIR"

echo "Using python: $PYTHON_CMD"
echo "Starting Browser app on http://127.0.0.1:5000 ..."

if [ "${OSTYPE:-}" = "darwin"* ] || [ "$(uname -s)" = "Darwin" ]; then
  (
    sleep 2
    open "http://127.0.0.1:5000" >/dev/null 2>&1 || true
  ) &
fi

exec "$PYTHON_CMD" -u app.py
