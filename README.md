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

## Requirements

- **Python 3.12** (mandatory for extractor - game loaders are compiled for 3.12)
- A working EVE Frontier installation
- **Python 3.x** (for converter)

## Usage

### Data Extraction

#### Windows (via .BAT launcher)
```
EXTRACT.bat
```

Or manually:
```bash
py -3.12 EF_Extractor_Win_MacOS_V3.3.py ^
    -e "C:\Program Files\EVE Frontier" ^
    -i "C:\Program Files\EVE Frontier\stillness\resfileindex.txt" ^
    -o "output" ^
    -c "systems,solarsystemcontent,types,regions,locationcache,localization"
```

#### macOS
**Note**: Native macOS extraction is currently not possible due to technical limitations. Although the game's code.ccp is precompiled on both platforms, Windows uses CCP's embedded C++ Python loader (.pyd) which bypasses Python's zipimport and magic number checks. On macOS, the same archive is loaded via Python's zipimport from an external interpreter, which strictly enforces bytecode ABI compatibility. As a result, Windows extraction works, but macOS native extraction does not.

However, once the JSON files are extracted (e.g., on Windows), the converter scripts work on macOS and can process the data into the SQLite database.

#### Debug Script
`debug_resfile.py` is a utility to inspect and debug resfile data before extraction. It helps detect the data format and safely introspect objects.

Usage:
```bash
py -3.12 debug_resfile.py ^
    -e "C:\Program Files\EVE Frontier" ^
    -i "C:\Program Files\EVE Frontier\stillness\resfileindex.txt" ^
    -c solarsystemcontent
```

### Database Browser

To run the web interface for browsing the database:

```bash
cd browser
python app.py
```

Then open http://localhost:5000 in your browser.

You can also set `EF_DB_PATH` to preselect a database path:

```bash
set EF_DB_PATH=..\db\eve_universe.db
python app.py
```

Notes:
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
- **stars**: Star data.
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

