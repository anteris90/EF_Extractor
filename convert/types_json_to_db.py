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

TYPES_JSON = OUTPUT_DIR / "types.json"
LOCALIZATION_JSON = OUTPUT_DIR / "localization.json"
SQLITE_DB = DB_DIR / "eve_universe.db"

# =====================
# HELPERS
# =====================

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

def resolve_type_name(type_data, localization_map):
    # Future-proof: prefer direct name if this field appears in output.
    direct_name = normalize_name(type_data.get("name"))
    if direct_name and not (isinstance(direct_name, str) and direct_name.isdigit()):
        return direct_name

    localized = resolve_localized_text(localization_map, type_data.get("typeNameID"))
    if localized:
        return localized

    return direct_name

# =====================
# LOAD JSON
# =====================

DB_DIR.mkdir(parents=True, exist_ok=True)

with TYPES_JSON.open("r", encoding="utf-8") as f:
    types = json.load(f)

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

cur.executescript("""
DROP TABLE IF EXISTS types;

CREATE TABLE types (
    typeID          INTEGER PRIMARY KEY,
    typeNameID      INTEGER,
    name            TEXT,
    groupID         INTEGER,
    volume          REAL,
    mass            REAL,
    capacity        REAL,
    radius          REAL,
    published       INTEGER,
    basePrice       REAL,
    descriptionID   INTEGER,
    graphicID       INTEGER,
    raceID          INTEGER,
    portionSize     INTEGER,
    platforms       INTEGER
);
""")

# =====================
# INSERT DATA
# =====================

missing_names = 0

for type_id_str, t in types.items():
    type_id = int(type_id_str)

    name_id = t.get("typeNameID")
    name = resolve_type_name(t, localization)

    if not name:
        missing_names += 1

    cur.execute("""
        INSERT INTO types VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        type_id,
        name_id,
        name,
        t.get("groupID"),
        t.get("volume"),
        t.get("mass"),
        t.get("capacity"),
        t.get("radius"),
        t.get("published"),
        t.get("basePrice"),
        t.get("descriptionID"),
        t.get("graphicID"),
        t.get("raceID"),
        t.get("portionSize"),
        t.get("platforms"),
    ))

conn.commit()
conn.close()

print("[OK] types imported into SQLite")
print("[INFO] types:", len(types))
print("[INFO] missing names:", missing_names)
