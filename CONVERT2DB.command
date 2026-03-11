#!/usr/bin/env bash
set -euo pipefail

# Run from script directory so relative paths resolve
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  EVE Frontier JSON to DB Converter"
echo "============================================"
echo

echo "[INFO] Python version check ..."
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[ERROR] Python is not installed or not defined in PATH."
  exit 1
fi

echo "[INFO] Run Converter..."
"$PY" convert/json_to_sqlite_main.py

echo
echo "[DONE] Output ready in: \"output\" folder."
echo
read -p "Press Enter to exit..." -r
