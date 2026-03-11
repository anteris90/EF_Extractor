#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EVE Frontier Staticdata Extractor – V4 (stable)
Windows + macOS compatible
"""

import argparse
import json
import sys
import importlib.util
import pickle
from pathlib import Path

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

def build_root(game_path: Path):

    if IS_MAC:
        return (
            game_path
            / "stillness"
            / "EVE.app"
            / "Contents"
            / "Resources"
            / "build"
        )

    return game_path / "stillness"


def bin64_root(game_path: Path):
    return build_root(game_path) / "bin64"


def codeccp_root(game_path: Path):

    if IS_MAC:
        return build_root(game_path) / "code.ccp"

    return game_path / "stillness" / "code.ccp"


def resfiles_root(game_path: Path):
    return game_path / "ResFiles"


# ------------------------------------------------------------
# MATERIALIZE
# ------------------------------------------------------------

def materialize(obj):

    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    if hasattr(obj, "items"):
        return {str(k): materialize(v) for k, v in obj.items()}

    try:
        name = type(obj).__name__
    except Exception:
        name = None

    if name and name not in ("list", "tuple"):

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

    if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
        try:
            return [materialize(x) for x in obj]
        except Exception:
            pass

    return str(obj)


# ------------------------------------------------------------
# LOADERS
# ------------------------------------------------------------

def load_built_fsd(game_path: Path, container: str, fsd_file: Path):

    ext = ".pyd" if IS_WIN else ".so"
    wanted = f"{container}loader{ext}".lower()

    root = bin64_root(game_path)

    for p in root.rglob(f"*{ext}"):

        if p.name.lower() == wanted:

            sys.path.insert(0, str(root))

            try:
                spec = importlib.util.spec_from_file_location(p.stem, p)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                return module.load(str(fsd_file))

            finally:
                sys.path.remove(str(root))

    return None


def load_schema_fsd(game_path: Path, fsd_file: Path, schema_file: Path | None):

    sys.path.insert(0, str(codeccp_root(game_path)))

    try:
        from fsd.schemas.binaryLoader import LoadFSDDataInPython

        # fsdbinary → optimized
        optimized = fsd_file.name.endswith(".fsdbinary")

        return LoadFSDDataInPython(
            str(fsd_file),
            str(schema_file) if schema_file else None,
            optimized,
            None,
        )

    finally:
        sys.path.remove(str(codeccp_root(game_path)))


def load_fsd(game_path, container, fsd_file, schema_file):

    data = load_built_fsd(game_path, container, fsd_file)

    if data is not None:
        return data

    return load_schema_fsd(game_path, fsd_file, schema_file)


def load_fsd_data(game_path, container, fsd_file, schema_file):

    data = load_fsd(game_path, container, fsd_file, schema_file)

    if hasattr(data, "items"):
        return {k: v for k, v in data.items()}

    return data


# ------------------------------------------------------------
# RESFILEINDEX
# ------------------------------------------------------------

def load_resfileindex(index_path: Path):

    mapping = {}

    with index_path.open("r", encoding="utf-8") as f:

        for line in f:

            if not (
                line.startswith("res:/staticdata/")
                or line.startswith("res:/localizationfsd/")
            ):
                continue

            respath, folder, *_ = line.strip().split(",")

            name = respath.split("/")[-1]

            if name.endswith(".static"):
                key = name[:-7]

            elif name.endswith(".fsdbinary"):
                key = name[:-10]

            elif name.endswith(".schema"):
                key = name[:-7] + ".schema"

            else:
                key = name

            mapping[key] = folder

    return mapping


def resolve_paths(game_path, mapping, container):

    if container not in mapping:
        raise RuntimeError(f"No FSD file for container: {container}")

    fsd_file = resfiles_root(game_path) / mapping[container]

    schema = None
    schema_key = f"{container}.schema"

    if schema_key in mapping:
        schema = resfiles_root(game_path) / mapping[schema_key]

    print("   FSD:", fsd_file)
    print("   SCHEMA:", schema)

    return fsd_file, schema


# ------------------------------------------------------------
# LOCALIZATION
# ------------------------------------------------------------

def normalize_localization(data):

    if isinstance(data, dict):
        return data

    if isinstance(data, tuple):
        for item in data:
            if isinstance(item, dict):
                return item
            if isinstance(item, list):
                try:
                    return dict(item)
                except Exception:
                    pass

    if isinstance(data, list):
        try:
            return dict(data)
        except Exception:
            pass

    raise RuntimeError(
        f"Unsupported localization pickle format: {type(data)}"
    )

def extract_localization(game_path: Path, mapping: dict, out_dir: Path):

    loc_key = None

    for k in mapping:
        if "localization_fsd_en-us" in k:
            loc_key = k
            break

    if not loc_key:
        print("[WARN] localization not found")
        return

    path = game_path / "ResFiles" / mapping[loc_key]

    print("[INFO] Loading localization:", path)

    try:
        with open(path, "rb") as f:
            raw = pickle.load(f)

        data = normalize_localization(raw)
    except Exception as exc:
        print("[WARN] localization pickle format unexpected:", exc)
        return

    clean = {str(k): v for k, v in data.items()}

    out = out_dir / "localization.json"

    with out.open("w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)

    print("[OK] localization →", out)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

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

    containers = [c.strip() for c in args.containers.split(",")]

    for container in containers:

        print("[INFO] Processing:", container)

        fsd_file, schema = resolve_paths(game_path, mapping, container)

        data = load_fsd_data(game_path, container, fsd_file, schema)

        clean = materialize(data)

        out = out_dir / f"{container}.json"

        with out.open("w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, indent=2)

        print("[OK]", container, "→", out)

    extract_localization(game_path, mapping, out_dir)


if __name__ == "__main__":
    main()