"""Build a copy of the client resource pack without retired Mega form assets."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile


def filter_pack(source, output, pixelmon, replacements):
    targets = set(json.loads(replacements.read_text(encoding="utf-8")).values())
    prefixes = set()
    with ZipFile(pixelmon) as native:
        for name in native.namelist():
            if not name.startswith("data/pixelmon/species/") or not name.endswith(".json"):
                continue
            base = json.loads(native.read(name))["forms"][0]
            for stone, form in zip(base.get("megaItems", []), base.get("megas", [])):
                if stone in targets:
                    targets.remove(stone)
                    prefixes.add((Path(name).stem, form))
    if targets:
        raise ValueError(f"Missing stock Mega forms: {sorted(targets)}")

    def retired(name):
        parts = name.split("/")
        return parts[:4] == ["assets", "pixelmon", "textures", "pokemon"] and len(parts) > 6 and (parts[4], parts[6]) in prefixes

    with ZipFile(source) as old:
        removed = {name for name in old.namelist() if retired(name)}
        if not removed:
            raise ValueError("No retired resources found in the input pack")
        with ZipFile(output, "x") as new:
            for entry in old.infolist():
                if entry.filename not in removed:
                    new.writestr(entry, old.read(entry))
        with ZipFile(output) as new:
            assert set(new.namelist()) == set(old.namelist()) - removed
            assert new.testzip() is None
            assert all(old.getinfo(name).CRC == new.getinfo(name).CRC for name in new.namelist())
    return len(removed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("source", "output", "pixelmon", "replacements"):
        parser.add_argument(arg, type=Path)
    print(f"Removed {filter_pack(**vars(parser.parse_args()))} retired Mega resource entries")
