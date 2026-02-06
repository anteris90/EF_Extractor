import json
import sqlite3
from pathlib import Path

# =====================
# PATHS
# =====================

def find_repo_root(start_dir: Path) -> Path:
    for candidate in (start_dir, *start_dir.parents):
        if (candidate / "convert").is_dir() and (candidate / "db").is_dir():
            return candidate
    return start_dir.parent

ROOT_DIR = find_repo_root(Path(__file__).resolve().parent)
DB_DIR = ROOT_DIR / "db"
OUTPUT_DIR = ROOT_DIR / "output"

SYSTEMS_JSON = OUTPUT_DIR / "systems.json"
LOCALIZATION_JSON = OUTPUT_DIR / "localization.json"
SQLITE_DB = DB_DIR / "eve_universe.db"

# =====================
# LOAD JSON FILES
# =====================

DB_DIR.mkdir(parents=True, exist_ok=True)

with SYSTEMS_JSON.open("r", encoding="utf-8") as f:
    systems = json.load(f)

with LOCALIZATION_JSON.open("r", encoding="utf-8") as f:
    localization = json.load(f)

# =====================
# SQLITE SETUP
# =====================

conn = sqlite3.connect(SQLITE_DB)
cur = conn.cursor()

# --- DROP ---
cur.executescript("""
DROP TABLE IF EXISTS system_planets;
DROP TABLE IF EXISTS systems;
""")

# --- CREATE ---
cur.executescript("""
CREATE TABLE systems (
    solarSystemID      INTEGER PRIMARY KEY,
    nameID             INTEGER,
    name               TEXT,
    securityStatus     REAL,
    securityClass      TEXT,
    regionID           INTEGER,
    constellationID    INTEGER,
    center_x           REAL,
    center_y           REAL,
    center_z           REAL,
    sunTypeID          INTEGER,
    sunFlareGraphicID  INTEGER
);

CREATE TABLE system_planets (
    solarSystemID INTEGER,
    planetItemID  INTEGER,
    PRIMARY KEY (solarSystemID, planetItemID)
);
""")

# =====================
# INSERT DATA
# =====================



missing_names = 0

def normalize_name(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        # Frontier localization: első elem a "display name"
        return value[0] if value else None
    return str(value)

for system in systems.values():
    system_id = system.get("solarSystemID")
    name_id = system.get("nameID")
    name = localization.get(str(name_id)) if name_id else None

    if name_id and name is None:
        missing_names += 1

    center = system.get("center") or {}

    # --- systems ---
    raw_name = localization.get(str(name_id))
    name = normalize_name(raw_name)

    cur.execute("""
        INSERT INTO systems VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, (
        system_id,
        name_id,
        name,
        system.get("securityStatus"),
        system.get("securityClass"),
        system.get("regionID"),
        system.get("constellationID"),
        center.get("x"),
        center.get("y"),
        center.get("z"),
        system.get("sunTypeID"),
        system.get("sunFlareGraphicID"),
    ))


    # --- system_planets ---
    for planet_id in system.get("planetItemIDs", []):
        cur.execute("""
            INSERT INTO system_planets VALUES (?, ?)
        """, (system_id, planet_id))

conn.commit()
conn.close()

print("[OK] SQLite DB created:", SQLITE_DB)
print("[INFO] Systems:", len(systems))
print("[INFO] Missing names:", missing_names)
