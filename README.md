# EVE Frontier Static Data Extractor

A unified, cross‑platform Python tool for extracting static data from the **EVE Frontier** game client.  
Supports both **Windows** and **macOS** installations.

---

## Features

- Extracts:
  - `systems`
  - `solarsystemcontent`
  - `industry_blueprints`
- Uses CCP’s built‑in FSD loaders (`.pyd` on Windows, `.so` on macOS)
- Automatically falls back to schema‑based decoding via `code.ccp`
- Outputs clean, structured JSON files

---

## Requirements

- **Python 3.12**  
  (Mandatory — the game’s loader modules are compiled for Python 3.12.)
- A working EVE Frontier installation:
  - **Windows:** `C:\Program Files\EVE Frontier`
  - **macOS:** `~/Library/Application Support/EVE Frontier/SharedCache`

---

## Usage

### Windows (via .BAT launcher)

```
run_extractor.bat
```

Or manually:

```bash
py -3.12 EF_Extractor_Win_MacOS.py ^
    -e "C:\Program Files\EVE Frontier" ^
    -i "C:\Program Files\EVE Frontier\stillness\resfileindex.txt" ^
    -o "output" ^
    -c "systems,solarsystemcontent"
```

---

### macOS (via .sh launcher)

```
./run_extractor.sh
```

Or manually:

```bash
python3 EF_Extractor_Win_MacOS.py \
    -e "$HOME/Library/Application Support/EVE Frontier/SharedCache" \
    -i "$HOME/Library/Application Support/EVE Frontier/SharedCache/stillness/resfileindex.txt" \
    -o "output" \
    -c "systems,solarsystemcontent"
```

---

## Arguments

| Flag | Description |
|------|-------------|
| `-e` / `--eve` | Path to the game root (the folder containing `stillness/`) |
| `-i` / `--index` | Path to `resfileindex.txt` |
| `-o` / `--out` | Output directory for JSON files |
| `-c` / `--containers` | Comma‑separated list of FSD containers to extract |

Example:

```
-c systems,solarsystemcontent,industry_blueprints
```

---

## Output

All extracted data is written to the directory specified by `--out`, e.g.:

```
output/
  systems.json
  solarsystemcontent.json
  industry_blueprints.json
```

---

## Notes

- The extractor works identically on Windows and macOS because the real FSD decoding logic lives in `stillness/code.ccp`.
- The script automatically detects and loads the correct platform‑specific loader modules (`.pyd` or `.so`).
- No reverse engineering is required — all decoding uses CCP’s official runtime.

