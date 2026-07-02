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

if LOCALIZATION_JSON.exists():
    with LOCALIZATION_JSON.open("r", encoding="utf-8") as f:
        localization = json.load(f)
else:
    localization = {}
    print("[WARN] localization.json not found; names will be missing")

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
        # Frontier localization: first element is usually the display name
        return value[0] if value else None
    return str(value)

def resolve_localized_text(localization_map, key):
    if key is None:
        return None

    text = normalize_name(localization_map.get(str(key)))
    if not text:
        return None

    # Some builds store an intermediate numeric token in localization.
    # Example: nameID -> "30089267"; if that token exists as a key, dereference once.
    if isinstance(text, str) and text.isdigit():
        indirect = normalize_name(localization_map.get(text))
        if indirect:
            return indirect

    return text

def resolve_system_name(system, localization_map):
    # New Frontier builds provide system names directly in systems.json.
    direct_name = normalize_name(system.get("name"))
    if direct_name and not (isinstance(direct_name, str) and direct_name.isdigit()):
        return direct_name

    name_id = system.get("nameID")
    localized = resolve_localized_text(localization_map, name_id)
    if localized:
        return localized

    if direct_name:
        return direct_name

    return None

for system in systems.values():
    system_id = system.get("solarSystemID")
    name_id = system.get("nameID")
    name = resolve_system_name(system, localization)

    if not name:
        missing_names += 1

    center = system.get("center") or {}

    # --- systems ---
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
