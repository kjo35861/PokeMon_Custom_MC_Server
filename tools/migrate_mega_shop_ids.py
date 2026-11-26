"""Migrate saved shop IDs after the Pocketmate Mega registry update."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil


LEGACY = re.compile(r"^eeveemega:(mega_stone_\d+)$")


def migrate(value):
    if isinstance(value, str):
        return LEGACY.sub(r"pocketmate_mega:\1", value)
    if isinstance(value, list):
        converted = [migrate(entry) for entry in value]
        if all(isinstance(entry, str) for entry in converted):
            return list(dict.fromkeys(converted))
        return converted
    if isinstance(value, dict):
        converted = {}
        for key, entry in value.items():
            target = migrate(key)
            if target == key or target not in value:
                converted[target] = migrate(entry)
        return converted
    return value


def apply(path, backup):
    if not path.is_file():
        return
    original = json.loads(path.read_text(encoding="utf-8-sig"))
    updated = migrate(original)
    if updated == original:
        return
    if "revision" in updated:
        updated["revision"] += 1
    backup.mkdir(parents=True, exist_ok=True)
    saved = backup / path.name
    if not saved.exists():
        shutil.copy2(path, saved)
    pending = path.with_suffix(".json.namespace.pending")
    pending.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(pending, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("files", type=Path, nargs="+")
    args = parser.parse_args()
    for file in args.files:
        apply(file, args.backup)
