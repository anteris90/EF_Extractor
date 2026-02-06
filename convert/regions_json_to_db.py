import json
import sqlite3
import os
from pathlib import Path

# ----- PATHS -----
ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
DB_DIR = ROOT_DIR / "db"

JSON_PATH = OUTPUT_DIR / "regions.json"
DB_PATH = DB_DIR / "regions.db"

# ----- ENSURE DB DIR EXISTS -----
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ----- LOAD JSON -----
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# ----- CONNECT SQLITE -----
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ----- DROP TABLES -----
cur.executescript("""
DROP TABLE IF EXISTS region_neighbours;
DROP TABLE IF EXISTS region_solar_systems;
DROP TABLE IF EXISTS region_constellations;
DROP TABLE IF EXISTS regions;
""")

# ----- CREATE TABLES -----
cur.executescript("""
CREATE TABLE IF NOT EXISTS regions (
    region_id INTEGER PRIMARY KEY,
    description_id INTEGER,
    name_id INTEGER,
    nebula_id INTEGER,
    nebula_path TEXT,
    potential REAL,
    region_level INTEGER,
    sector_id INTEGER,
    wormhole_class_id INTEGER,
    zone_level INTEGER
);

CREATE TABLE IF NOT EXISTS region_constellations (
    region_id INTEGER,
    constellation_id INTEGER,
    PRIMARY KEY (region_id, constellation_id)
);

CREATE TABLE IF NOT EXISTS region_solar_systems (
    region_id INTEGER,
    solar_system_id INTEGER,
    PRIMARY KEY (region_id, solar_system_id)
);

CREATE TABLE IF NOT EXISTS region_neighbours (
    region_id INTEGER,
    neighbour_region_id INTEGER,
    PRIMARY KEY (region_id, neighbour_region_id)
);
""")

# ----- INSERT DATA -----
for region_id_str, region in data.items():
    region_id = int(region_id_str)

    cur.execute("""
        INSERT OR REPLACE INTO regions (
            region_id,
            description_id,
            name_id,
            nebula_id,
            nebula_path,
            potential,
            region_level,
            sector_id,
            wormhole_class_id,
            zone_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        region_id,
        region.get("descriptionID"),
        region.get("nameID"),
        region.get("nebulaID"),
        region.get("nebulaPath"),
        region.get("potential"),
        region.get("regionLevel"),
        region.get("sectorID"),
        region.get("wormholeClassID"),
        region.get("zoneLevel"),
    ))

    # constellations
    for cid in region.get("constellationIDs", []):
        cur.execute("""
            INSERT OR IGNORE INTO region_constellations
            (region_id, constellation_id)
            VALUES (?, ?)
        """, (region_id, cid))

    # solar systems
    for sid in region.get("solarSystemIDs", []):
        cur.execute("""
            INSERT OR IGNORE INTO region_solar_systems
            (region_id, solar_system_id)
            VALUES (?, ?)
        """, (region_id, sid))

    # neighbours
    for nid in region.get("neighbours", []):
        cur.execute("""
            INSERT OR IGNORE INTO region_neighbours
            (region_id, neighbour_region_id)
            VALUES (?, ?)
        """, (region_id, nid))

# ----- COMMIT & CLOSE -----
conn.commit()
conn.close()

print("[OK] JSON successfully converted to SQLite database.")
print(f"[INFO] DB location: {DB_PATH}")
