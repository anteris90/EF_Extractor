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
CONTAINERS="locationcache,systems,regions,solarsystemcontent,types"
#CONTAINERS="types"

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

# CCP's macOS loaders need libpython3.12.dylib to be discoverable.
# Prefer an explicit shim dir if provided. Otherwise create a project-local shim
# and populate it from Homebrew python@3.12 when possible.
PROJECT_PYTHON_SHIM_DIR="$SCRIPT_DIR/.python-shim"
DYLD_PYTHON_LIB_DIR=""
BREW_PY312_LIB=""

if command -v brew >/dev/null 2>&1; then
  BREW_PY312_PREFIX="$(brew --prefix python@3.12 2>/dev/null || true)"
  for candidate in \
    "$BREW_PY312_PREFIX/Frameworks/Python.framework/Versions/3.12/lib/libpython3.12.dylib" \
    "$BREW_PY312_PREFIX/lib/libpython3.12.dylib"
  do
    if [ -f "$candidate" ]; then
      BREW_PY312_LIB="$candidate"
      break
    fi
  done
fi

if [ -n "${DYLD_PYTHON_SHIM:-}" ] && [ -f "$DYLD_PYTHON_SHIM/libpython3.12.dylib" ]; then
  DYLD_PYTHON_LIB_DIR="$DYLD_PYTHON_SHIM"
elif [ -f "$PROJECT_PYTHON_SHIM_DIR/libpython3.12.dylib" ]; then
  DYLD_PYTHON_LIB_DIR="$PROJECT_PYTHON_SHIM_DIR"
elif [ -n "$BREW_PY312_LIB" ]; then
  mkdir -p "$PROJECT_PYTHON_SHIM_DIR"
  ln -sf "$BREW_PY312_LIB" "$PROJECT_PYTHON_SHIM_DIR/libpython3.12.dylib"
  DYLD_PYTHON_LIB_DIR="$PROJECT_PYTHON_SHIM_DIR"
  echo "[INFO] Created project-local libpython shim: $PROJECT_PYTHON_SHIM_DIR"
elif [ -f "$HOME/eve_python_shim/libpython3.12.dylib" ]; then
  DYLD_PYTHON_LIB_DIR="$HOME/eve_python_shim"
fi

if [ -n "$DYLD_PYTHON_LIB_DIR" ]; then
  export DYLD_LIBRARY_PATH="$DYLD_PYTHON_LIB_DIR${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
  echo "[INFO] Using libpython3.12 from: $DYLD_PYTHON_LIB_DIR"
else
  echo "[WARN] libpython3.12.dylib was not found automatically."
  echo "       Install Homebrew python@3.12 or set DYLD_PYTHON_SHIM to a directory containing libpython3.12.dylib."
fi

echo "[INFO] Run Extractor..."
"$PY" EF_Extractor_V4.py \
  -e "$GAME_PATH" \
  -i "$RESINDEX" \
  -o "$OUT" \
  -c "$CONTAINERS"

echo
echo "[DONE] Output ready in: \"$OUT\" folder."
echo
read -p "Press Enter to exit..." -r