"""Add first-run Minecraft and Xaero defaults to a Pocketmate player payload."""
import argparse
import json
from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile


XAERO_CONFIGS = (
    "minimap/client.cfg",
    "minimap/profiles/default.cfg",
    "minimap/profiles/entity_radar_categories/default.cfg.json",
    "minimap/profiles/info_display_config/default.cfg.txt",
    "world-map/client.cfg",
    "world-map/profiles/default.cfg",
    "lib/client.cfg",
    "lib/profiles/default.cfg",
)


def package(game, previous, launcher, output):
    if previous.resolve() == output.resolve():
        raise ValueError("Use a separate output archive")
    with ZipFile(previous) as source:
        manifest = json.loads(source.read("client-pack.json"))
        bundled = {"file/" + entry["path"].split("/", 1)[1] for entry in manifest["files"]
                   if entry["path"].startswith("resourcepacks/")}
        options = {}
        for line in (game / "options.txt").read_text("utf-8-sig").splitlines():
            key, separator, value = line.partition(":")
            if separator and key not in {"lastServer", "soundDevice", "overrideWidth", "overrideHeight"}:
                options[key] = value
        packs = json.loads(options.get("resourcePacks", '["vanilla","mod_resources"]'))
        packs = [name for name in packs if name in bundled or not name.startswith("file/")]
        radar = "file/pocketmate-pixelmon-radar.zip"
        if radar in bundled and radar not in packs:
            packs.append(radar)
        options["resourcePacks"] = json.dumps(packs, ensure_ascii=False)
        options["incompatibleResourcePacks"] = "[]"
        # Pixelmon already uses H for multiple actions.
        options["key_accessories.key.open_accessories_screen"] = "key.keyboard.j"
        defaults = {"options.txt": "".join(f"{key}:{value}\n" for key, value in options.items()).encode()}
        defaults["config/xaerohud.txt"] = (
            b"module;id=xaerominimap:minimap;x=0;y=0;centered=false;"
            b"fromRight=true;fromBottom=true;flippedVer=false;flippedHor=false;\n"
        )
        for name in XAERO_CONFIGS:
            relative = "config/xaero/" + name
            defaults[relative] = (game / relative).read_bytes()
        migrated = "config/xaero/minimap/profiles/entity_radar_categories/default.cfg.json"
        manifest["files"] = [entry for entry in manifest["files"] if entry["path"] != migrated]
        with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=1) as target:
            for entry in source.infolist():
                name = entry.filename
                if (entry.is_dir() or name.startswith("client-defaults/")
                        or name in {"client-pack.json", "PocketmateLauncher.exe", "client-files/" + migrated}):
                    continue
                with source.open(entry) as content, target.open(name, "w", force_zip64=True) as destination:
                    shutil.copyfileobj(content, destination)
            target.writestr("client-pack.json", json.dumps(manifest, ensure_ascii=False).encode())
            target.write(launcher, "PocketmateLauncher.exe")
            for name, content in defaults.items():
                target.writestr("client-defaults/" + name, content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("game", "previous", "launcher", "output"):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    package(args.game, args.previous, args.launcher, args.output)
