#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
from pathlib import Path

# Path to the convert directory where converters are located
CONVERT_DIR = Path(__file__).resolve().parent

# List of converters to run, corresponding to JSON files in output/
converters = [
    'types_json_to_db.py',
    'systems_json_to_db.py',
    'regions_json_to_db.py',
    'locationcache_json_to_db.py',
    'solarsystemcontent_json_to_db.py',
]

def main():
    for converter in converters:
        converter_path = CONVERT_DIR / converter
        if converter_path.exists():
            print(f"Running {converter}...")
            try:
                result = subprocess.run([sys.executable, str(converter_path)], cwd=CONVERT_DIR, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"[OK] {converter} completed successfully.")
                    print(result.stdout)
                else:
                    print(f"[ERROR] {converter} failed with return code {result.returncode}.")
                    print(result.stderr)
            except Exception as e:
                print(f"[ERROR] Failed to run {converter}: {e}")
        else:
            print(f"[WARNING] {converter} not found.")

    # Delete temporary databases as they are integrated into eve_universe.db and no longer needed
    regions_db = CONVERT_DIR.parent / 'db' / 'regions.db'
    if regions_db.exists():
        regions_db.unlink()
        print("Deleted regions.db as it's no longer needed.")

    locationcache_db = CONVERT_DIR.parent / 'db' / 'locationcache.db'
    if locationcache_db.exists():
        try:
            locationcache_db.unlink()
            print("Deleted locationcache.db as it's no longer needed.")
        except PermissionError:
            print("Could not delete locationcache.db (file in use), but it's no longer needed.")

    types_db = CONVERT_DIR.parent / 'db' / 'types.db'
    if types_db.exists():
        try:
            types_db.unlink()
            print("Deleted types.db as it's no longer needed.")
        except PermissionError:
            print("Could not delete types.db (file in use), but it's no longer needed.")

if __name__ == "__main__":
    main()