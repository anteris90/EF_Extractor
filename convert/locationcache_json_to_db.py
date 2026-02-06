import json
import sqlite3
from pathlib import Path

# -------- PATHS --------
def find_repo_root(start_dir: Path) -> Path:
    for candidate in (start_dir, *start_dir.parents):
        if (candidate / "convert").is_dir() and (candidate / "db").is_dir():
            return candidate
    return start_dir.parent

ROOT_DIR = find_repo_root(Path(__file__).resolve().parent)
OUTPUT_DIR = ROOT_DIR / "output"
DB_DIR = ROOT_DIR / "db"

JSON_PATH = OUTPUT_DIR / "locationcache.json"
DB_PATH = DB_DIR / "locationcache.db"

DB_DIR.mkdir(parents=True, exist_ok=True)

# -------- LOAD JSON --------
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# -------- CONNECT DB --------
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# -------- CREATE TABLE --------
cur.execute("""
CREATE TABLE IF NOT EXISTS locationcache_typed (
    location_id INTEGER PRIMARY KEY,
    solar_system_id INTEGER,
    location_type TEXT
)
""")

# -------- CLASSIFICATION --------
def classify(location_id: int) -> str:
    if 30000000 <= location_id < 40000000:
        return "SolarSystem"
    if 40000000 <= location_id < 40100000:
        return "Planet"
    if 40100000 <= location_id < 40200000:
        return "Moon"
    if 50000000 <= location_id < 60000000:
        return "Stargate"
    if 60000000 <= location_id < 70000000:
        return "Station"
    return "Other"

# -------- INSERT DATA --------
rows = []

if isinstance(data, dict):
    # {"location_id": solar_system_id}
    for loc_id_str, sys_id in data.items():
        loc_id = int(loc_id_str)
        rows.append((
            loc_id,
            int(sys_id),
            classify(loc_id)
        ))
elif isinstance(data, list):
    # [[location_id, solar_system_id], ...]
    for loc_id, sys_id in data:
        rows.append((
            int(loc_id),
            int(sys_id),
            classify(int(loc_id))
        ))
else:
    raise ValueError("Unknown JSON structure")

cur.executemany("""
INSERT OR REPLACE INTO locationcache_typed (
    location_id,
    solar_system_id,
    location_type
) VALUES (?, ?, ?)
""", rows)

# -------- INDEXES --------
cur.execute("CREATE INDEX IF NOT EXISTS idx_lct_type ON locationcache_typed(location_type)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_lct_system ON locationcache_typed(solar_system_id)")

conn.commit()
conn.close()

print("[OK] locationcache JSON imported and classified")
print(f"[INFO] DB: {DB_PATH}")
