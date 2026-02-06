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
DROP TABLE IF EXISTS region_constellations;
DROP TABLE IF EXISTS regions;
""")

# ----- CREATE TABLES -----
cur.executescript("""
CREATE TABLE IF NOT EXISTS regions (
    regionId INTEGER PRIMARY KEY,
    descriptionId INTEGER,
    nameId INTEGER,
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

    cur.execute("""
        INSERT OR REPLACE INTO regions (
            regionId,
            descriptionId,
            nameId,
            nebulaId,
            nebulaPath,
            potential,
            regionLevel,
            sectorId,
            wormholeClassId,
            zoneLevel
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        regionId,
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
