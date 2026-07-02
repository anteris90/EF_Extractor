import json
import sqlite3
from pathlib import Path

# ----- PATHS -----
def find_repo_root(start_dir: Path) -> Path:
    for candidate in (start_dir, *start_dir.parents):
        if (candidate / "convert").is_dir() and (candidate / "db").is_dir():
            return candidate
    return start_dir.parent

ROOT_DIR = find_repo_root(Path(__file__).resolve().parent)
OUTPUT_DIR = ROOT_DIR / "output"
DB_DIR = ROOT_DIR / "db"

JSON_PATH = OUTPUT_DIR / "regions.json"
LOCALIZATION_JSON = OUTPUT_DIR / "localization.json"
DB_PATH = DB_DIR / "regions.db"

# ----- ENSURE DB DIR EXISTS -----
DB_DIR.mkdir(parents=True, exist_ok=True)

# ----- LOAD JSON -----
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

if LOCALIZATION_JSON.exists():
    with open(LOCALIZATION_JSON, "r", encoding="utf-8") as f:
        localization = json.load(f)
else:
    localization = {}
    print("[WARN] localization.json not found; names will be missing")

def normalize_name(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return value[0] if value else None
    return str(value)

def resolve_localized_text(localization_map, key):
    if key is None:
        return None

    text = normalize_name(localization_map.get(str(key)))
    if not text:
        return None

    # Some builds return an intermediate numeric token.
    if isinstance(text, str) and text.isdigit():
        indirect = normalize_name(localization_map.get(text))
        if indirect:
            return indirect

    return text

def resolve_region_name(region_data, localization_map):
    # Prefer the region name embedded in regions.json.
    direct_name = normalize_name(region_data.get("name"))
    if direct_name and not (isinstance(direct_name, str) and direct_name.isdigit()):
        return direct_name

    localized = resolve_localized_text(localization_map, region_data.get("nameID"))
    if localized:
        return localized

    return direct_name

# ----- CONNECT SQLITE -----
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ----- DROP TABLES -----
cur.executescript("""
DROP TABLE IF EXISTS region_constellations;
DROP TABLE IF EXISTS regions;
""")

# ----- CREATE TABLES -----
cur.executescript("""
CREATE TABLE IF NOT EXISTS regions (
    regionId INTEGER PRIMARY KEY,
    descriptionId INTEGER,
    nameId INTEGER,
    name TEXT,
    nebulaId INTEGER,
    nebulaPath TEXT,
    potential REAL,
    regionLevel INTEGER,
    sectorId INTEGER,
    wormholeClassId INTEGER,
    zoneLevel INTEGER
);

CREATE TABLE IF NOT EXISTS region_constellations (
    regionId INTEGER,
    constellationId INTEGER,
    PRIMARY KEY (regionId, constellationId)
);
""")

# ----- INSERT DATA -----
for regionId_str, region in data.items():
    regionId = int(regionId_str)

    name_id = region.get("nameID")
    name = resolve_region_name(region, localization)

    cur.execute("""
        INSERT OR REPLACE INTO regions (
            regionId,
            descriptionId,
            nameId,
            name,
            nebulaId,
            nebulaPath,
            potential,
            regionLevel,
            sectorId,
            wormholeClassId,
            zoneLevel
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        regionId,
        region.get("descriptionID"),
        name_id,
        name,
        region.get("nebulaID"),
        region.get("nebulaPath"),
        region.get("potential"),
        region.get("regionLevel"),
        region.get("sectorID"),
        region.get("wormholeClassID"),
        region.get("zoneLevel"),
    ))

    # constellations
    for cid in region.get("constellationIDs", region.get("regionLevels", [])):
        cur.execute("""
            INSERT OR IGNORE INTO region_constellations
            (regionId, constellationId)
            VALUES (?, ?)
        """, (regionId, cid))


# ----- COMMIT & CLOSE -----
conn.commit()
conn.close()

print("[OK] JSON successfully converted to SQLite database.")
print(f"[INFO] DB location: {DB_PATH}")
