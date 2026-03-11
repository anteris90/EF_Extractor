# Frontier Data Extractor and Converter

This project provides tools to extract static data from the EVE Frontier game client and convert it into a unified SQLite database.

## Project Components

### 1. Data Extractor
Extracts static data from the EVE Frontier game client into JSON files.

### 2. JSON to SQLite Converter
Converts the extracted JSON files into a unified SQLite database (`eve_universe.db`).

### 3. Database Browser (Web Interface)
A simple Flask web application to browse and query a SQLite database (raw SQL, read-only).

## Features

- **Extractor**: Cross-platform tool for extracting game data (systems, solarsystemcontent, industry_blueprints, etc.)
- **Converter**: Processes JSON files into a comprehensive SQLite database with all EVE universe data
- **Unified Database**: Single `eve_universe.db` containing types, systems, planets, moons, stars, stargates, NPC stations, and regions
- **Web Browser**: Simple web interface to explore the database tables and run queries
- **Read-only SQL**: Only `SELECT` queries are allowed
- **Saved queries**: Store/edit/delete named queries (persisted in `browser/saved_queries.json`)
- **Query history**: Last 100 queries with a scrollable list
- **Table tools**: Per-column filtering and column hide/show controls
- **AI prompt helper**: Built-in prompt with table/column details for external AI tools

## Files and Folders

- **convert/**: Conversion scripts
- **db/**: Output database (`eve_universe.db`)
- **output/**: Extracted JSON files
- **browser/**: Web interface for database browsing

## Git LFS (required for output JSON)

The large JSON files in **output/** are stored with Git LFS. If you see tiny files that contain
`version https://git-lfs.github.com/spec/v1`, your LFS objects were not downloaded and the
converter will fail with JSON decode errors.

Install and pull LFS objects:

```bash
git lfs install
git lfs pull
```

If Git LFS is not installed yet (macOS):

```bash
brew install git-lfs
git lfs install
git lfs pull
```

## Requirements

- **Python 3.12** (mandatory for extractor - CCP's loaders are compiled for 3.12). On macOS, install Homebrew Python 3.12:

```bash
brew install python@3.12
```

- On macOS, the extractor also needs `libpython3.12.dylib` to be discoverable at runtime. `EXTRACT.command` will try to find it automatically from Homebrew and create a project-local shim in `.python-shim/` when needed.
- A working EVE Frontier installation
- **Python 3.x** (for converter)
- Git LFS (required if you want the full JSON files from this repository)

### macOS Prerequisites

- Launch EVE Frontier at least once so the SharedCache is initialized.
- Default game path used by `EXTRACT.command`:

```text
~/Library/Application Support/EVE Frontier/SharedCache
```

- Default `resfileindex.txt` path expected by the launcher:

```text
~/Library/Application Support/EVE Frontier/SharedCache/stillness/EVE.app/Contents/Resources/build/resfileindex.txt
```

- If `libpython3.12.dylib` is not found automatically, either install `python@3.12` via Homebrew or set `DYLD_PYTHON_SHIM` to a directory that already contains `libpython3.12.dylib`.

## Usage

### Data Extraction

#### Windows (via .BAT launcher)
```
EXTRACT.bat
```

Or manually:
```bash
py -3.12 EF_Extractor_V4.py ^
    -e "C:\Program Files\EVE Frontier" ^
    -i "C:\Program Files\EVE Frontier\stillness\resfileindex.txt" ^
    -o "output" ^
    -c "systems,solarsystemcontent,types,regions,locationcache,localization"
```

#### macOS
Native macOS extraction is supported via the included launcher `EXTRACT.command`.

Usage (from the project root):

```bash
./EXTRACT.command
```

Notes:
- `EXTRACT.command` runs from the repo root, defaults `GAME_PATH` to `~/Library/Application Support/EVE Frontier/SharedCache`, and resolves `resfileindex.txt` automatically inside the app bundle.
- The launcher prefers `python3.12`, then falls back to `python3`.
- The launcher tries to auto-configure `DYLD_LIBRARY_PATH` so CCP's macOS loaders can find `libpython3.12.dylib`. If Homebrew Python 3.12 is installed, it will create `.python-shim/libpython3.12.dylib` automatically.
- You can override the detected EVE installation path by exporting `GAME_PATH` before running, for example:

```bash
export GAME_PATH="$HOME/Library/Application Support/EVE Frontier/SharedCache"
./EXTRACT.command
```

If your installation lives somewhere else, point `GAME_PATH` at the SharedCache directory that contains `stillness/` and `ResFiles/`.

If `libpython3.12.dylib` still is not detected automatically, you can point the launcher at an existing shim directory explicitly:

```bash
export DYLD_PYTHON_SHIM="/path/to/directory/containing/libpython3.12.dylib"
./EXTRACT.command
```

The launcher currently requests these container dumps:

```text
locationcache,systems,regions,solarsystemcontent,types
```

After that, `EF_Extractor_V4.py` also attempts localization extraction and writes `output/localization.json` when the localization resource is present and readable.

If you still prefer extracting on Windows, the JSON output can be copied to macOS and the converter/browser tooling will work normally.

#### Debug Script
`debug_resfile.py` is a utility to inspect and debug resfile data before extraction. It helps detect the data format and safely introspect objects.

Usage:
```bash
py -3.12 debug_resfile.py ^
    -e "C:\Program Files\EVE Frontier" ^
    -i "C:\Program Files\EVE Frontier\stillness\resfileindex.txt" ^
    -c solarsystemcontent
```

### JSON to SQLite Converter
The project includes a launcher for converting extracted JSON into the SQLite database.

Windows (BAT):
```
CONVERT2DB.bat
```

macOS (command):

```bash
./CONVERT2DB.command
```

Notes:
- The converter uses `python3` if available, then falls back to `python`.
- The converter script runs `convert/json_to_sqlite_main.py` from the repo root, so path handling works correctly on macOS.
- Output is written to `db/eve_universe.db`.

### Database Browser

To run the web interface for browsing the database:

```bash
cd browser
python app.py
```

On macOS or Linux, you can use the launcher from the project root instead:

```bash
./Start\ Browser.sh
```

On macOS, you can also double-click `Start Browser.command` in Finder.

Then open http://localhost:5000 in your browser.

You can also set `EF_DB_PATH` to preselect a database path:

Windows:

```bat
set EF_DB_PATH=..\db\eve_universe.db
python app.py
```

macOS / Linux:

```bash
export EF_DB_PATH="$(pwd)/db/eve_universe.db"
./Start\ Browser.sh
```

Notes:
- `Start Browser.sh` prefers `./venv/bin/python` if present, otherwise it uses `python3` or `python`.
- On macOS, the launcher attempts to open `http://127.0.0.1:5000` automatically.
- The browser's database chooser can use AppleScript (`osascript`) on macOS when tkinter is unavailable.
- The template is served from `browser/index.html` (Flask template).
- Saved queries and history persist in `browser/saved_queries.json`.
- Column hide settings are stored locally in your browser (localStorage).

## Database Structure (eve_universe.db)

### Tables (current schema)

- **types**: Type/item data.
- **systems**: System data + statistics + station flag.
- **planets**: Planet data.
- **moons**: Moon data.
- **stargates**: Gate data.
- **npc_stations**: NPC stations.
- **stars**: Star data, including nested `star.statistics` fields such as age, life, luminosity, mass, metallicity, spectral class, and temperature.
- **regions**: Region data (includes `name`).
- **region_constellations**: Region connections.
- **system_planets**: Planet list per system.

### Key Notes

- All data is complete: statistics, types, positions, connections.
- The station column (in systems table) is 1 if there is a Station type location in the system.
- Data is cross-referenced: names from localization.json, meta data from systems.json, details from solarsystemcontent.json.

## Dependencies

- Python 3.x
- pathlib, json, sqlite3 (built-in modules)

## Maintenance

- If new JSON files come, update the scripts.
- Scripts robustly handle missing data (None values).
- In case of error, check JSON files and paths.

## Contact


If you have questions, review the scripts or ask.

