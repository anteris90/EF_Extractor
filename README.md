# EVE Frontier Data Extractor and Converter

This project provides tools to extract static data from the EVE Frontier game client and convert it into a unified SQLite database.

## Project Components

### 1. Data Extractor
Extracts static data from the EVE Frontier game client into JSON files.

### 2. JSON to SQLite Converter
Converts the extracted JSON files into a unified SQLite database (`eve_universe.db`).

### 3. Database Browser (Web Interface)
A simple Flask web application to browse and query the `eve_universe.db` database.

## Features

- **Extractor**: Cross-platform tool for extracting game data (systems, solarsystemcontent, industry_blueprints, etc.)
- **Converter**: Processes JSON files into a comprehensive SQLite database with all EVE universe data
- **Unified Database**: Single `eve_universe.db` containing types, systems, planets, moons, stars, stargates, NPC stations, and regions
- **Web Browser**: Simple web interface to explore the database tables and run queries

## Files and Folders

- **convert/**: Conversion scripts
- **db/**: Output databases (`eve_universe.db`)
- **output/**: Extracted JSON files
- **browser/**: Web interface for database browsing
- **archive/**: Original scripts and documentation

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

**Note**: The web interface is currently a work in progress and may not function properly.

To run the web interface for browsing the database:

```bash
cd browser
python app.py
```

Then open http://localhost:5000 in your browser. Note: Update `DB_PATH` in `app.py` to point to `eve_universe.db` if needed.

## Database Structure (eve_universe.db)

### Tables and Records

- **types** (32,212 records): Type/item data.  
  Columns: typeID, typeNameID, name, groupID, volume, mass, capacity, radius, published, basePrice, descriptionID, graphicID, raceID, portionSize, platforms.

- **systems** (24,426 records): System basic data + statistics + station flag.  
  Columns: solarSystemID, nameID, name, securityStatus, securityClass, regionID, constellationID, center_x/y/z, sunTypeID, sunFlareGraphicID, station, + statistics (density, temperature, etc.).

- **planets** (83,257 records): Planet detailed data.  
  Columns: solarSystemID, planetID, celestialIndex, typeID, radius, + statistics.

- **moons** (147,060 records): Moon detailed data.  
  Columns: planetID, moonID, orbitID, typeID, radius, + statistics.

- **stargates** (6,876 records): Gate data.  
  Columns: solarSystemID, stargateID, destination, typeID, position_x/y/z.

- **npc_stations** (98 records): NPC stations.  
  Columns: celestialID, stationID, constructableTypeListID, isConquerable, lagrangePoint, operationID, orbitID, ownerID, reprocessingEfficiency, reprocessingHangarFlag, reprocessingStationsTake, solarSystemID, stationName, typeID, useOperationName.

- **stars** (24,426 records): Star data.  
  Columns: solarSystemID, starID, typeID, radius, spectralClass, temperature.

- **regions** (284 records): Region data.  
  Columns: region_id, description_id, name_id, nebula_id, nebula_path, potential, region_level, sector_id, wormhole_class_id, zone_level.

- **region_constellations, region_solar_systems, region_neighbours**: Region connections.

- **system_planets** (old, for compatibility, 83,257 records): planetID list per system.

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

