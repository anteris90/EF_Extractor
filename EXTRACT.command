#!/usr/bin/env bash
set -euo pipefail

# Ensure we run from the script's directory so relative paths resolve
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  EVE Frontier Staticdata Extractor"
echo "============================================"
echo

# --- Default Frontier SharedCache path (override with GAME_PATH env) ---
GAME_PATH="${GAME_PATH:-$HOME/Library/Application Support/EVE Frontier/SharedCache}"

# --- Path to resfileindex.txt ---
RESINDEX="$GAME_PATH/stillness/EVE.app/Contents/Resources/build/resfileindex.txt"

# --- Output folder ---
OUT=output

# --- Containers to extract ---
CONTAINERS="locationcache,systems,regions,solarsystemcontent"

# ------------------------------------------------------------

echo "[INFO] Game path: $GAME_PATH"

if [ ! -f "$RESINDEX" ]; then
  echo "[ERROR] resfileindex.txt not found:"
  echo "        $RESINDEX"
  echo
  echo "Make sure EVE Frontier has been launched at least once."
  exit 1
fi

echo "[INFO] Python version check ..."
if command -v python3.12 >/dev/null 2>&1; then
  PY=python3.12
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  echo "[ERROR] Python not found in PATH."
  exit 1
fi

echo "[INFO] Run Extractor..."
"$PY" EF_Extractor.py \
  -e "$GAME_PATH" \
  -i "$RESINDEX" \
  -o "$OUT" \
  -c "$CONTAINERS"

echo
echo "[DONE] Output ready in: \"$OUT\" folder."
echo
read -p "Press Enter to exit..." -r