#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
from pathlib import Path
import sys
import importlib.util
import platform


# ============================================================
# PLATFORM DETECTION
# ============================================================

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")


# ============================================================
# FSD LOADERS
# ============================================================

def materialize(obj):
    # primitive
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # CCP DictLoader
    if hasattr(obj, "items"):
        return {str(k): materialize(v) for k, v in obj.items()}

    # CCP ObjectLoader
    if obj.__class__.__name__ == "ObjectLoader":
        out = {}
        for key in dir(obj):
            if key.startswith("_"):
                continue
            try:
                val = obj[key]
                out[key] = materialize(val)
            except Exception:
                continue
        return out

    # CCP ListLoader / iterable
    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        try:
            return [materialize(x) for x in obj]
        except Exception:
            pass

    # fallback
    return obj


def safe_get(obj, key, default=None):
    try:
        val = obj[key]
        if val == "-- not present --":
            return default
        return val
    except Exception:
        return default


def extract_vector(v):
    try:
        return {"x": v.x, "y": v.y, "z": v.z}
    except Exception:
        return None


def extract_star(star):
    if not star:
        return None

    stats = safe_get(star, "statistics", {})

    return {
        "id": safe_get(star, "id"),
        "typeID": safe_get(star, "typeID"),
        "radius": safe_get(star, "radius"),
        "spectralClass": safe_get(stats, "spectralClass"),
        "temperature": safe_get(stats, "temperature"),
        "mass": safe_get(stats, "mass"),
        "luminosity": safe_get(stats, "luminosity"),
        "age": safe_get(stats, "age"),
        "life": safe_get(stats, "life"),
    }


def _bin64_root(game_path: Path) -> Path:
    """
    game_path is expected to be the directory that contains 'stillness'.
    On Windows:   <Program Files>/EVE Frontier
    On macOS:     ~/Library/Application Support/EVE Frontier/SharedCache
    """
    return game_path / "stillness" / "bin64"


def _codeccp_root(game_path: Path) -> Path:
    """
    code.ccp lives under stillness on both platforms.
    """
    return game_path / "stillness" / "code.ccp"


def load_built_fsd(game_path: Path, container: str, fsd_file: Path):
    bin64 = _bin64_root(game_path)
    loader_ext = ".pyd" if IS_WIN else ".so"
    loader_name = f"{container}Loader{loader_ext}"
    loader_path = next(bin64.rglob(loader_name))

    sys.path.insert(0, str(loader_path.parent))
    try:
        spec = importlib.util.spec_from_file_location(loader_path.stem, loader_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.load(str(fsd_file))
    finally:
        sys.path.remove(str(loader_path.parent))


def load_schema_fsd(game_path: Path, fsd_file: Path, schema_file: Path | None):
    codeccp = _codeccp_root(game_path)
    sys.path.insert(0, str(codeccp))
    try:
        from fsd.schemas.binaryLoader import LoadFSDDataInPython
        return LoadFSDDataInPython(
            str(fsd_file),
            str(schema_file) if schema_file else None,
            False,
            None,
        )
    finally:
        sys.path.remove(str(codeccp))


def load_fsd_auto(game_path: Path, container: str, fsd_file: Path, schema_file: Path | None):
    bin64 = _bin64_root(game_path)

    # 1️⃣ BUILT loader (case-insensitive, .pyd on Windows, .so on macOS)
    loader_ext = ".pyd" if IS_WIN else ".so"
    wanted = f"{container}loader{loader_ext}".lower()
    for p in bin64.rglob(f"*{loader_ext}"):
        if p.name.lower() == wanted:
            sys.path.insert(0, str(p.parent))
            try:
                spec = importlib.util.spec_from_file_location(p.stem, p)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.load(str(fsd_file))
            finally:
                sys.path.remove(str(p.parent))

    # 2️⃣ SCHEMA loader
    if schema_file is not None:
        return load_schema_fsd(game_path, fsd_file, schema_file)

    # 3️⃣ RAW fallback via code.ccp
    codeccp = _codeccp_root(game_path)
    sys.path.insert(0, str(codeccp))
    try:
        from fsd.schemas.binaryLoader import LoadFSDDataInPython
        return LoadFSDDataInPython(str(fsd_file), None, False, None)
    finally:
        sys.path.remove(str(codeccp))


def load_fsd_data(game_path, container, fsd_file, schema_file):
    fsd_container = load_fsd_auto(
        game_path=game_path,
        container=container,
        fsd_file=fsd_file,
        schema_file=schema_file,
    )

    # CCP DictLoader → materialize
    if hasattr(fsd_container, "items"):
        return {k: v for k, v in fsd_container.items()}

    return fsd_container


# ============================================================
# RESFILEINDEX
# ============================================================

def load_resfileindex(index_path: Path):
    """
    mapping: container_name -> ResFiles hash path
    """
    mapping = {}
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.startswith("res:/staticdata/"):
                continue

            respath, folder, *_ = line.strip().split(",")
            container = respath.replace("res:/staticdata/", "")

            for ext in (".static", ".fsdbinary"):
                if container.endswith(ext):
                    container = container[: -len(ext)]

            mapping[container] = folder

    return mapping


def resolve_resfiles_root(game_path: Path) -> Path:
    """
    ResFiles is a sibling of 'stillness' on both platforms if game_path points
    to the directory that contains 'stillness'.
    """
    return game_path / "ResFiles"


def resolve_paths(game_path: Path, mapping: dict, container: str):
    if container not in mapping:
        raise RuntimeError(f"No FSD file for container: {container}")

    resfiles_root = resolve_resfiles_root(game_path)
    fsd_file = resfiles_root / mapping[container]

    schema_file = None
    schema_key = f"{container}.schema"
    if schema_key in mapping:
        schema_file = resfiles_root / mapping[schema_key]

    return fsd_file, schema_file


# ============================================================
# SYSTEMS / STELLAR EXTRACTORS
# ============================================================

def extract_system(obj):
    def g(field):
        try:
            val = obj[field]
            return None if val == "-- not present --" else val
        except Exception:
            return None

    center = g("center")
    if center:
        center = {"x": center.x, "y": center.y, "z": center.z}

    return {
        "solarSystemID": g("solarSystemID"),
        "securityStatus": g("securityStatus"),
        "securityClass": g("securityClass"),
        "regionID": g("regionID"),
        "constellationID": g("constellationID"),
        "nameID": g("nameID"),
        "center": center,
        "sunTypeID": g("sunTypeID"),
        "sunFlareGraphicID": g("sunFlareGraphicID"),
        "planetItemIDs": g("planetItemIDs"),
    }


def extract_systems(data: dict):
    return {str(k): extract_system(v) for k, v in data.items()}


def extract_solarsystemcontent(data: dict):
    out = {}

    for system_id, obj in data.items():
        center = extract_vector(safe_get(obj, "center"))
        hz = safe_get(obj, "habitableZone")

        out[str(system_id)] = {
            "solarSystemID": safe_get(obj, "solarSystemID"),
            "center": center,
            "radius": safe_get(obj, "radius"),
            "security": safe_get(obj, "security"),
            "securityClass": safe_get(obj, "securityClass"),
            "habitableZone": hz,
            "potential": safe_get(obj, "potential"),
            "frostLine": safe_get(obj, "frostLine"),
            "sunTypeID": safe_get(obj, "sunTypeID"),
            "sunFlareGraphicID": safe_get(obj, "sunFlareGraphicID"),
            "star": extract_star(safe_get(obj, "star")),
            "planets": materialize(safe_get(obj, "planets", {})),
            "stargates": materialize(safe_get(obj, "stargates", {})),
        }

    return out


# ============================================================
# BLUEPRINT EXTRACTOR
# ============================================================

def extract_blueprints(data: dict):
    def io(x):
        return {"typeID": x.typeID, "quantity": x.quantity}

    out = {}
    for k, bp in data.items():
        out[str(k)] = {
            "primaryTypeID": bp.primaryTypeID,
            "runTime": bp.runTime,
            "inputs": [io(x) for x in bp.inputs],
            "outputs": [io(x) for x in bp.outputs],
        }
    return out


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Unified cross-platform EVE Frontier FSD extractor"
    )
    parser.add_argument(
        "-e", "--eve", required=True,
        help=(
            "Game root path. On Windows: the directory that contains 'stillness'. "
            "On macOS: the SharedCache directory that contains 'stillness' and 'ResFiles'."
        ),
    )
    parser.add_argument(
        "-i", "--index", required=True,
        help="Path to resfileindex.txt"
    )
    parser.add_argument(
        "-o", "--out", required=True,
        help="Output directory for JSON files"
    )
    parser.add_argument(
        "-c", "--containers", required=True,
        help="Comma-separated list of containers (e.g. 'systems,solarsystemcontent,industry_blueprints')"
    )
    args = parser.parse_args()

    game_path = Path(args.eve)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    mapping = load_resfileindex(Path(args.index))
    containers = [c.strip().lower() for c in args.containers.split(",") if c.strip()]

    for container in containers:
        print(f"[INFO] Processing container: {container}")

        fsd_file, schema_file = resolve_paths(game_path, mapping, container)
        data = load_fsd_data(game_path, container, fsd_file, schema_file)

        # deterministic dispatch
        if container == "industry_blueprints":
            clean = extract_blueprints(data)
        elif container == "systems":
            clean = extract_systems(data)
        elif container == "solarsystemcontent":
            clean = extract_solarsystemcontent(data)
        else:
            clean = data  # raw fallback

        out_path = out_dir / f"{container}.json"
        clean = materialize(clean)

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)

        print(f"[OK] {container} → {out_path}")


if __name__ == "__main__":
    main()
