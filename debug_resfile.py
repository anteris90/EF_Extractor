#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EVE Frontier – Generic Resfile Debugger

Purpose:
- Inspect ANY resfile before writing an extractor
- Detect BUILT loader / schema / raw FSD
- Safely introspect first object
- NEVER crashes on missing fields

Usage:
python debug_resfile.py \
  -e "C:\Program Files\EVE Frontier" \
  -i "C:\Program Files\EVE Frontier\stillness\resfileindex.txt" \
  -c solarsystemcontent

py -3.12 debug_resfile.py -e "C:\Program Files\EVE Frontier" -i "C:\Program Files\EVE Frontier\stillness\resfileindex.txt" -c solarsystemcontent

"""

import argparse
import sys
from pathlib import Path
import importlib.util

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


# ------------------------------------------------------------
# PATH HELPERS
# ------------------------------------------------------------

def bin64_root(game_path: Path) -> Path:
    return game_path / "stillness" / "bin64"

def codeccp_root(game_path: Path) -> Path:
    return game_path / "stillness" / "code.ccp"

def resfiles_root(game_path: Path) -> Path:
    return game_path / "ResFiles"


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

            container = (
                respath
                .replace("res:/staticdata/", "")
                .replace("res:/localizationfsd/", "")
            )

            for ext in (".static", ".fsdbinary", ".pickle"):
                if container.endswith(ext):
                    container = container[: -len(ext)]

            mapping[container.lower()] = folder

    return mapping


# ------------------------------------------------------------
# LOADER DETECTION
# ------------------------------------------------------------

def find_builtin_loader(game_path: Path, container: str):
    ext = ".pyd" if IS_WIN else ".so"
    wanted = f"{container}loader{ext}".lower()

    print("[DEBUG] Scanning bin64 for loaders...")
    for p in bin64_root(game_path).rglob(f"*{ext}"):
        if wanted == p.name.lower():
            print("[FOUND] BUILT loader:", p.name)
            return p

    print("[INFO] No BUILT loader found")
    return None


def load_with_schema(game_path: Path, fsd_file: Path):
    sys.path.insert(0, str(codeccp_root(game_path)))
    try:
        from fsd.schemas.binaryLoader import LoadFSDDataInPython
        return LoadFSDDataInPython(str(fsd_file), None, False, None)
    finally:
        sys.path.remove(str(codeccp_root(game_path)))


# ------------------------------------------------------------
# SAFE OBJECT INTROSPECTION
# ------------------------------------------------------------

def safe_fields(obj, limit=50):
    fields = []
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            _ = obj[name]
            fields.append(name)
        except Exception:
            pass
    return fields[:limit]

# ------------------------------------------------------------
# FIND SCHEMA (if needed)
# ------------------------------------------------------------

def find_schema(mapping, container):
    key = f"{container}.schema"
    return mapping.get(key)


# ------------------------------------------------------------
# MAIN DEBUG LOGIC
# ------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="EVE Frontier resfile debugger")
    ap.add_argument("-e", "--eve", required=True, help="Game root path")
    ap.add_argument("-i", "--index", required=True, help="resfileindex.txt path")
    ap.add_argument("-c", "--container", required=True, help="container name")
    args = ap.parse_args()

    game_path = Path(args.eve)
    container = args.container.lower()

    print("=" * 60)
    print("EVE FRONTIER RESFILE DEBUGGER")
    print("=" * 60)

    mapping = load_resfileindex(Path(args.index))

    if container not in mapping:
        print("[ERROR] Container not found in resfileindex")
        return

    fsd_file = resfiles_root(game_path) / mapping[container]

    print("[INFO] Container:", container)
    print("[INFO] ResFile:", fsd_file)
    print()

    # --- BUILT loader check ---
    loader = find_builtin_loader(game_path, container)

    if loader:
        print("[INFO] Loading via BUILT loader")
        sys.path.insert(0, str(loader.parent))
        try:
            spec = importlib.util.spec_from_file_location(loader.stem, loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            data = module.load(str(fsd_file))
        finally:
            sys.path.remove(str(loader.parent))
    else:
        print("[INFO] Loading via SCHEMA / RAW FSD")
        schema_rel = find_schema(mapping, container)
        schema_file = None

        if schema_rel:
            schema_file = resfiles_root(game_path) / schema_rel
            print("[INFO] Using schema:", schema_file)
        else:
            print("[WARN] No schema file found")

        # --- import loader here (scope-safe) ---
        sys.path.insert(0, str(codeccp_root(game_path)))
        try:
            from fsd.schemas.binaryLoader import LoadFSDDataInPython

            data = LoadFSDDataInPython(
                str(fsd_file),
                str(schema_file) if schema_file else None,
                False,
                None,
            )
        finally:
            sys.path.remove(str(codeccp_root(game_path)))



    print()
    print("[DEBUG] data type:", type(data))
    print("[DEBUG] has items:", hasattr(data, "items"))
    print("[DEBUG] length:", len(data) if hasattr(data, "__len__") else "N/A")

    if not hasattr(data, "items"):
        print("[WARN] Data is not dict-like")
        return

    # --- SAFE FIRST ELEMENT EXTRACTION ---
    try:
        if hasattr(data, "items"):
            first_key, first_obj = next(iter(data.items()))
        else:
            raise RuntimeError("Data is not dict-like")
    except Exception as e:
        print("[ERROR] Failed to extract first element:", e)
        return


    print()
    print("[DEBUG] First key:", first_key)
    print("[DEBUG] First object type:", type(first_obj))
    print("[DEBUG] First object repr:", repr(first_obj))

    print()
    print("[DEBUG] Accessible fields:")
    for f in safe_fields(first_obj):
        print(" ", f)

    print()
    print("✔ Debug complete.")
    print("You can now write a proper extractor for this container.")
    print("=" * 60)


if __name__ == "__main__":
    main()
