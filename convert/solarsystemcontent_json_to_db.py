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

SOLARSYSTEMCONTENT_JSON = OUTPUT_DIR / "solarsystemcontent.json"
LOCALIZATION_JSON = OUTPUT_DIR / "localization.json"
SQLITE_DB = DB_DIR / "eve_universe.db"

# =====================
# LOAD JSON FILES
# =====================

DB_DIR.mkdir(parents=True, exist_ok=True)

with SOLARSYSTEMCONTENT_JSON.open("r", encoding="utf-8") as f:
    solarsystemcontent = json.load(f)

if LOCALIZATION_JSON.exists():
    with LOCALIZATION_JSON.open("r", encoding="utf-8") as f:
        localization = json.load(f)
else:
    localization = {}
    print("[WARN] localization.json not found; names will be missing")

# Load systems.json for nameID etc.
SYSTEMS_JSON = OUTPUT_DIR / "systems.json"
with SYSTEMS_JSON.open("r", encoding="utf-8") as f:
    systems_data = json.load(f)

# =====================
# SQLITE SETUP
# =====================

conn = sqlite3.connect(SQLITE_DB)
cur = conn.cursor()

# --- DROP ---
cur.execute("DROP TABLE IF EXISTS system_planets")
cur.execute("DROP TABLE IF EXISTS stars")
cur.execute("DROP TABLE IF EXISTS stargates")
cur.execute("DROP TABLE IF EXISTS planets")
cur.execute("DROP TABLE IF EXISTS moons")
cur.execute("DROP TABLE IF EXISTS npc_stations")
cur.execute("DROP TABLE IF EXISTS systems")
cur.execute("DROP TABLE IF EXISTS regions")
cur.execute("DROP TABLE IF EXISTS region_constellations")
cur.execute("DROP TABLE IF EXISTS region_solar_systems")
cur.execute("DROP TABLE IF EXISTS region_neighbours")

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

CREATE TABLE stargates (
    solarSystemID INTEGER,
    stargateID INTEGER,
    destination INTEGER,
    typeID INTEGER,
    position_x REAL,
    position_y REAL,
    position_z REAL,
    PRIMARY KEY (solarSystemID, stargateID)
);

CREATE TABLE planets (
    solarSystemID INTEGER,
    planetID INTEGER,
    celestialIndex INTEGER,
    typeID INTEGER,
    radius REAL,
    density REAL,
    eccentricity REAL,
    escapeVelocity REAL,
    fragmented INTEGER,
    life REAL,
    locked INTEGER,
    massDust REAL,
    massGas REAL,
    orbitClockwise INTEGER,
    orbitPeriod REAL,
    orbitRadius REAL,
    pressure REAL,
    rotationRate REAL,
    spectralClass TEXT,
    surfaceGravity REAL,
    temperature REAL,
    typeDescription TEXT,
    PRIMARY KEY (solarSystemID, planetID)
);

CREATE TABLE moons (
    planetID INTEGER,
    moonID INTEGER,
    orbitID INTEGER,
    typeID INTEGER,
    radius REAL,
    density REAL,
    eccentricity REAL,
    escapeVelocity REAL,
    fragmented INTEGER,
    life REAL,
    locked INTEGER,
    massDust REAL,
    massGas REAL,
    orbitClockwise INTEGER,
    orbitPeriod REAL,
    orbitRadius REAL,
    pressure REAL,
    rotationRate REAL,
    spectralClass TEXT,
    surfaceGravity REAL,
    temperature REAL,
    typeDescription TEXT,
    PRIMARY KEY (planetID, moonID)
);

CREATE TABLE npc_stations (
    celestialID INTEGER,  -- planetID or moonID
    stationID INTEGER,
    constructableTypeListID INTEGER,
    isConquerable INTEGER,
    lagrangePoint INTEGER,
    operationID INTEGER,
    orbitID INTEGER,
    ownerID INTEGER,
    reprocessingEfficiency REAL,
    reprocessingHangarFlag INTEGER,
    reprocessingStationsTake REAL,
    solarSystemID INTEGER,
    stationName TEXT,
    typeID INTEGER,
    useOperationName INTEGER,
    PRIMARY KEY (celestialID, stationID)
);

CREATE TABLE regions (
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

CREATE TABLE region_constellations (
    regionId INTEGER,
    constellationId INTEGER,
    PRIMARY KEY (regionId, constellationId)
);

CREATE TABLE stars (
    solarSystemID INTEGER PRIMARY KEY,
    starID        INTEGER,
    typeID        INTEGER,
    radius        REAL,
    spectralClass TEXT,
    temperature   REAL
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

for system in solarsystemcontent.values():
    system_id = system.get("solarSystemID")
    system_basic = systems_data.get(str(system_id), {})
    name_id = system_basic.get("nameID")
    region_id = system_basic.get("regionID")
    constellation_id = system_basic.get("constellationID")
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
        system.get("security"),
        system.get("securityClass"),
        region_id,
        constellation_id,
        center.get("x"),
        center.get("y"),
        center.get("z"),
        system.get("sunTypeID"),
        system.get("sunFlareGraphicID"),
    ))


    # --- system_planets ---
    for planet_id in system.get("planets", {}):
        planet_data = system["planets"][planet_id]
        stats = planet_data.get("statistics", {})
        cur.execute("""
            INSERT INTO planets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            system_id,
            int(planet_id),
            planet_data.get("celestialIndex"),
            planet_data.get("typeID"),
            planet_data.get("radius"),
            stats.get("density"),
            stats.get("eccentricity"),
            stats.get("escapeVelocity"),
            1 if stats.get("fragmented") else 0,
            stats.get("life"),
            1 if stats.get("locked") else 0,
            stats.get("massDust"),
            stats.get("massGas"),
            1 if stats.get("orbitClockwise") else 0,
            stats.get("orbitPeriod"),
            stats.get("orbitRadius"),
            stats.get("pressure"),
            stats.get("rotationRate"),
            stats.get("spectralClass"),
            stats.get("surfaceGravity"),
            stats.get("temperature"),
            stats.get("typeDescription"),
        ))
        # --- npcStations on planet ---
        for station_id in planet_data.get("npcStations", {}):
            station_data = planet_data["npcStations"][station_id]
            cur.execute("""
                INSERT INTO npc_stations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(planet_id),
                int(station_id),
                station_data.get("constructableTypeListID"),
                1 if station_data.get("isConquerable") else 0,
                station_data.get("lagrangePoint"),
                station_data.get("operationID"),
                station_data.get("orbitID"),
                station_data.get("ownerID"),
                station_data.get("reprocessingEfficiency"),
                station_data.get("reprocessingHangarFlag"),
                station_data.get("reprocessingStationsTake"),
                station_data.get("solarSystemID"),
                station_data.get("stationName"),
                station_data.get("typeID"),
                1 if station_data.get("useOperationName") else 0,
            ))
        # --- moons ---
        for moon_id in planet_data.get("moons", {}):
            moon_data = planet_data["moons"][moon_id]
            stats_m = moon_data.get("statistics", {})
            cur.execute("""
                INSERT INTO moons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(planet_id),
                int(moon_id),
                moon_data.get("orbitID"),
                moon_data.get("typeID"),
                moon_data.get("radius"),
                stats_m.get("density"),
                stats_m.get("eccentricity"),
                stats_m.get("escapeVelocity"),
                1 if stats_m.get("fragmented") else 0,
                stats_m.get("life"),
                1 if stats_m.get("locked") else 0,
                stats_m.get("massDust"),
                stats_m.get("massGas"),
                1 if stats_m.get("orbitClockwise") else 0,
                stats_m.get("orbitPeriod"),
                stats_m.get("orbitRadius"),
                stats_m.get("pressure"),
                stats_m.get("rotationRate"),
                stats_m.get("spectralClass"),
                stats_m.get("surfaceGravity"),
                stats_m.get("temperature"),
                stats_m.get("typeDescription"),
            ))
            # --- npcStations on moon ---
            for station_id in moon_data.get("npcStations", {}):
                station_data = moon_data["npcStations"][station_id]
                cur.execute("""
                    INSERT INTO npc_stations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(moon_id),
                    int(station_id),
                    station_data.get("constructableTypeListID"),
                    1 if station_data.get("isConquerable") else 0,
                    station_data.get("lagrangePoint"),
                    station_data.get("operationID"),
                    station_data.get("orbitID"),
                    station_data.get("ownerID"),
                    station_data.get("reprocessingEfficiency"),
                    station_data.get("reprocessingHangarFlag"),
                    station_data.get("reprocessingStationsTake"),
                    station_data.get("solarSystemID"),
                    station_data.get("stationName"),
                    station_data.get("typeID"),
                    1 if station_data.get("useOperationName") else 0,
                ))

    # --- stargates ---
    for stargate_id in system.get("stargates", {}):
        stargate_data = system["stargates"][stargate_id]
        position = stargate_data.get("position", {})
        cur.execute("""
            INSERT INTO stargates VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            system_id,
            int(stargate_id),
            stargate_data.get("destination"),
            stargate_data.get("typeID"),
            position.get("x"),
            position.get("y"),
            position.get("z"),
        ))

    # --- stars ---
    star = system.get("star")
    if star:
        cur.execute("""
            INSERT INTO stars VALUES (?, ?, ?, ?, ?, ?)
        """, (
            system_id,
            star.get("id"),
            star.get("typeID"),
            star.get("radius"),
            star.get("spectralClass"),
            star.get("temperature"),
        ))

conn.commit()

# --- Add station column and populate from locationcache.db ---
cur.execute("ALTER TABLE systems ADD COLUMN station INTEGER DEFAULT 0")
locationcache_db_path = DB_DIR / "locationcache.db"
if locationcache_db_path.exists():
    locationcache_conn = sqlite3.connect(locationcache_db_path)
    locationcache_cur = locationcache_conn.cursor()
    locationcache_cur.execute("SELECT DISTINCT solar_system_id FROM locationcache_typed WHERE location_type = 'Station'")
    for row in locationcache_cur:
        solar_system_id = row[0]
        cur.execute("UPDATE systems SET station = 1 WHERE solarSystemID = ?", (solar_system_id,))
    locationcache_conn.close()

# --- Import regions.db tables into eve_universe.db ---
regions_db_path = DB_DIR / "regions.db"
if regions_db_path.exists():
    regions_conn = sqlite3.connect(regions_db_path)
    regions_cur = regions_conn.cursor()
    
    # Copy regions table
    regions_cur.execute("SELECT * FROM regions")
    regions_data = regions_cur.fetchall()
    cur.executemany("INSERT OR REPLACE INTO regions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", regions_data)
    
    # Copy region_constellations
    regions_cur.execute("SELECT * FROM region_constellations")
    constellations_data = regions_cur.fetchall()
    cur.executemany("INSERT OR REPLACE INTO region_constellations VALUES (?, ?)", constellations_data)
    
    regions_conn.close()

conn.commit()
conn.close()

print("[OK] SQLite DB updated:", SQLITE_DB)
print("[INFO] Systems:", len(solarsystemcontent))
print("[INFO] Missing names:", missing_names)
