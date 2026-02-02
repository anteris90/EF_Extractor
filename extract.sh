#!/bin/bash

echo "============================================"
echo "  EVE Frontier Staticdata Extractor (macOS)"
echo "============================================"
echo

# --- Set the installation path to EVE Frontier ---
# NOTE: This is the default SharedCache location on macOS.
GAME_PATH="$HOME/Library/Application Support/EVE Frontier/SharedCache"

# --- Path of resfileindex.txt ---
RESINDEX="$GAME_PATH/stillness/resfileindex.txt"

# --- Output folder ---
OUT="output"

# --- List of containers ---
# Examples:
#   types,groups,dogmaattributes
#   industry_blueprints
#   solarsystemcontent
CONTAINERS="solarsystemcontent,systems"

echo "[INFO] Checking Python version..."
python3 --version >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "[ERROR] Python3 is not installed or not in PATH."
    exit 1
fi

echo "[INFO] Running extractor..."
python3 UNI.py \
    -e "$GAME_PATH" \
    -i "$RESINDEX" \
    -o "$OUT" \
    -c "$CONTAINERS"

echo
echo "[DONE] Output ready in: \"$OUT\" folder."
echo
