#!/usr/bin/env bash
# Start Browser (Linux / macOS)
# Usage: ./Start\ Browser.sh [path/to/eve_universe.db]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/browser" || exit 1

# If an argument is provided, use it as EF_DB_PATH
if [ -n "$1" ]; then
  export EF_DB_PATH="$1"
  echo "Using EF_DB_PATH=$EF_DB_PATH"
fi

echo "Starting Browser app..."

if command -v python3 >/dev/null 2>&1; then
  python3 -u app.py
else
  python -u app.py
fi
