#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EVE Frontier Staticdata Extractor – V3 FINAL
--------------------------------------------
• Cross-platform (Windows / macOS)
• BUILT loader → schema → raw fallback
• Deterministic extractors for known containers
• Universal auto-extractor fallback
"""

import argparse
import json
import sys
import importlib.util
from pathlib import Path
import pickle

# ============================================================
# PLATFORM
# ============================================================

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

# ============================================================
# PATH HELPERS
# ============================================================

def bin64_root(game_path: Path) -> Path:
    return game_path / "stillness" / "bin64"

def codeccp_root(game_path: Path) -> Path:
    return game_path / "stillness" / "code.ccp"

def resfiles_root(game_path: Path) -> Path:
    return game_path / "ResFiles"

# ============================================================
# MATERIALIZATION (CORE)
# ============================================================

def materialize(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # dict-like (DictLoader, cfsd.dict)
    if hasattr(obj, "items"):
        return {str(k): materialize(v) for k, v in obj.items()}

    # CCP object-like (ObjectLoader, metaGroup, stb.)
    try:
        cls_name = type(obj).__name__
    except Exception:
        cls_name = None

    if cls_name and cls_name not in ("list", "tuple"):
        out = {}
        for attr in dir(obj):
            if attr.startswith("_"):
                continue
            try:
                val = getattr(obj, attr)
                if callable(val):
                    continue
                out[attr] = materialize(val)
            except Exception:
                continue
        if out:
            return out

    # iterable fallback
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        try:
            return [materialize(x) for x in obj]
        except Exception:
            pass

    return str(obj)


def safe_get(obj, key, default=None):
    try:
        v = obj[key]
        return None if v == "-- not present --" else v
    except Exception:
        return default

# ============================================================
# BUILT / SCHEMA LOADERS
# ============================================================

def load_built_fsd(game_path: Path, container: str, fsd_file: Path):
    ext = ".pyd" if IS_WIN else ".so"
    wanted = f"{container}loader{ext}".lower()

    for p in bin64_root(game_path).rglob(f"*{ext}"):
        if p.name.lower() == wanted:
            sys.path.insert(0, str(p.parent))
            try:
                spec = importlib.util.spec_from_file_location(p.stem, p)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.load(str(fsd_file))
            finally:
                sys.path.remove(str(p.parent))

    return None

def load_schema_fsd(game_path: Path, fsd_file: Path, schema_file: Path | None):
    sys.path.insert(0, str(codeccp_root(game_path)))
    try:
        from fsd.schemas.binaryLoader import LoadFSDDataInPython
        return LoadFSDDataInPython(
            str(fsd_file),
            str(schema_file) if schema_file else None,
            False,
            None,
        )
    finally:
        sys.path.remove(str(codeccp_root(game_path)))

def load_fsd(game_path, container, fsd_file, schema_file):
    data = load_built_fsd(game_path, container, fsd_file)
    if data is not None:
        return data

    if schema_file:
        return load_schema_fsd(game_path, fsd_file, schema_file)

    return load_schema_fsd(game_path, fsd_file, None)

def load_fsd_data(game_path, container, fsd_file, schema_file):
    data = load_fsd(game_path, container, fsd_file, schema_file)
    if hasattr(data, "items"):
        return {k: v for k, v in data.items()}
    return data

# Localization extraction is Windows-only because the .pickle file is not present on macOS. The extractor will detect this and skip gracefully, but the localization data will be missing from macOS dumps. A future improvement could be to implement a macOS-compatible localization extractor that reads directly from the game's data files instead of relying on the .pickle dump.
# For now, users who want localization data on macOS would need to run the extractor on Windows to get the localization.json file, and then copy that file into their macOS dump directory for use in their projects.
#   

def extract_localization_pickle(game_path: Path, mapping: dict, out_dir: Path):
    """
    Windows-only localization dump.
    Dumps localization_fsd_en-us.pickle → localization.json
    """

    if IS_MAC:
        print("[INFO] macOS detected → skipping localization pickle dump")
        return

    LOC_KEY = "res:/localizationfsd/localization_fsd_en-us.pickle"

    if LOC_KEY not in mapping:
        print("[WARN] localization_fsd_en-us.pickle not found in resfileindex")
        return

    pickle_path = game_path / "ResFiles" / mapping[LOC_KEY]

    print("[INFO] Loading localization pickle:", pickle_path)

    with open(pickle_path, "rb") as f:
        raw = pickle.load(f)

    data = normalize_localization(raw)

    clean = {str(k): v for k, v in data.items()}



    out_path = out_dir / "localization.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    print(f"[OK] localization → {out_path}")

def normalize_localization(data):
    # Case 1: dict
    if isinstance(data, dict):
        return data

    # Case 2: tuple → próbáljuk az elemeit
    if isinstance(data, tuple):
        for item in data:
            if isinstance(item, dict):
                return item
            if isinstance(item, list):
                try:
                    return dict(item)
                except Exception:
                    pass

    # Case 3: list of pairs
    if isinstance(data, list):
        try:
            return dict(data)
        except Exception:
            pass

    raise RuntimeError(
        f"Unsupported localization pickle format: {type(data)}"
    )

# ============================================================
# RESFILEINDEX
# ============================================================

def load_resfileindex(index_path: Path):
    mapping = {}
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not( 
                line.startswith("res:/staticdata/") or line.startswith("res:/localizationfsd/")
            ):
                continue
            respath, folder, *_ = line.strip().split(",")
            name = respath.replace("res:/staticdata/", "")
            for ext in (".static", ".fsdbinary"):
                if name.endswith(ext):
                    name = name[:-len(ext)]
            mapping[name] = folder
    return mapping

def resolve_paths(game_path, mapping, container):
    if container not in mapping:
        raise RuntimeError(f"No FSD file for container: {container}")
    fsd_file = resfiles_root(game_path) / mapping[container]
    schema = None
    sk = f"{container}.schema"
    if sk in mapping:
        schema = resfiles_root(game_path) / mapping[sk]
    return fsd_file, schema

# ============================================================
# EXTRACTORS
# ============================================================

def extract_blueprints(data):
    out = {}
    for k, bp in data.items():
        out[str(k)] = {
            "primaryTypeID": bp.primaryTypeID,
            "runTime": bp.runTime,
            "inputs": [{"typeID": x.typeID, "quantity": x.quantity} for x in bp.inputs],
            "outputs": [{"typeID": x.typeID, "quantity": x.quantity} for x in bp.outputs],
        }
    return out

def extract_systems(data):
    out = {}
    for k, o in data.items():
        c = safe_get(o, "center")
        out[str(k)] = {
            "solarSystemID": safe_get(o, "solarSystemID"),
            "securityStatus": safe_get(o, "securityStatus"),
            "securityClass": safe_get(o, "securityClass"),
            "regionID": safe_get(o, "regionID"),
            "constellationID": safe_get(o, "constellationID"),
            "nameID": safe_get(o, "nameID"),
            "center": {"x": c.x, "y": c.y, "z": c.z} if c else None,
        }
    return out

def extract_solarsystemcontent(data):
    out = {}
    for k, o in data.items():
        c = safe_get(o, "center")
        star = safe_get(o, "star")
        stats = safe_get(star, "statistics", {}) if star else {}
        out[str(k)] = {
            "solarSystemID": safe_get(o, "solarSystemID"),
            "center": {"x": c.x, "y": c.y, "z": c.z} if c else None,
            "radius": safe_get(o, "radius"),
            "security": safe_get(o, "security"),
            "securityClass": safe_get(o, "securityClass"),
            "habitableZone": safe_get(o, "habitableZone"),
            "potential": safe_get(o, "potential"),
            "frostLine": safe_get(o, "frostLine"),
            "sunTypeID": safe_get(o, "sunTypeID"),
            "sunFlareGraphicID": safe_get(o, "sunFlareGraphicID"),
            "star": {
                "id": safe_get(star, "id"),
                "typeID": safe_get(star, "typeID"),
                "radius": safe_get(star, "radius"),
                "spectralClass": safe_get(stats, "spectralClass"),
                "temperature": safe_get(stats, "temperature"),
                "mass": safe_get(stats, "mass"),
                "luminosity": safe_get(stats, "luminosity"),
                "age": safe_get(stats, "age"),
                "life": safe_get(stats, "life"),
            } if star else None,
            "planets": materialize(safe_get(o, "planets", {})),
            "stargates": materialize(safe_get(o, "stargates", {})),
        }
    return out

# ============================================================
# MAIN
# ============================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-e", "--eve", required=True)
    ap.add_argument("-i", "--index", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("-c", "--containers", required=True)
    args = ap.parse_args()

    game_path = Path(args.eve)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    mapping = load_resfileindex(Path(args.index))
    containers = [c.strip().lower() for c in args.containers.split(",") if c.strip()]

    for container in containers:
        print(f"[INFO] Processing container: {container}")
        fsd_file, schema = resolve_paths(game_path, mapping, container)
        data = load_fsd_data(game_path, container, fsd_file, schema)

        if container == "industry_blueprints":
            clean = extract_blueprints(data)
        elif container == "systems":
            clean = extract_systems(data)
        elif container == "solarsystemcontent":
            clean = extract_solarsystemcontent(data)
        else:
            clean = materialize(data)

        out = out_dir / f"{container}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)

        print(f"[OK] {container} → {out}")

    # Localization extraction (Windows-only)
    extract_localization_pickle(game_path, mapping, out_dir)

if __name__ == "__main__":
    main()
