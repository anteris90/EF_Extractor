#!/bin/bash

printf "\n============================================\n"
printf "  EVE Frontier Staticdata Extractor (macOS)\n"
printf "============================================\n\n"

# --- Set the installation path to EVE Frontier ---
GAME_PATH="$HOME/Library/Application Support/EVE Frontier/SharedCache"

# --- Path of resfileindex.txt ---
RESINDEX="$GAME_PATH/stillness/EVE.app/Contents/Resources/build/resfileindex.txt"

# --- Output folder ---
OUT="output"

# --- List of containers ---
CONTAINERS="solarsystemcontent,systems"

printf "[INFO] Checking Python version...\n"
if ! command -v python3 >/dev/null 2>&1; then
    printf "[ERROR] Python3 is not installed or not in PATH.\n"
    exit 1
fi

printf "[INFO] Running extractor...\n"
python3 EF_Extractor_Win_MacOS.py \
    -e "$GAME_PATH" \
    -i "$RESINDEX" \
    -o "$OUT" \
    -c "$CONTAINERS"

printf "\n[DONE] Output ready in: \"%s\" folder.\n\n" "$OUT"
