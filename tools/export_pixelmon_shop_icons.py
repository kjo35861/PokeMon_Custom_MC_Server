"""Extract native ball and Mega Stone item textures from an installed Pixelmon JAR."""
import argparse
import json
from pathlib import Path
import re
from zipfile import ZipFile


def export(pixelmon, output, pocketmate_mega=None, minecraft=None):
    icons = {}
    index = {}

    def add(jar, item_namespace, item, sprite):
        namespace, texture = sprite.split(":", 1)
        resource = f"assets/{namespace}/textures/{texture}.png"
        try:
            data = jar.read(resource)
        except KeyError:
            if namespace != "minecraft" or minecraft is None:
                return False
            with ZipFile(minecraft) as vanilla:
                data = vanilla.read(resource)
        filename = f"{item_namespace}_{item}.png"
        icons[filename] = data
        index[f"{item_namespace}:{item}"] = filename
        return True

    with ZipFile(pixelmon) as jar:
        names = set(jar.namelist())
        for item in ("tera_orb", "dynamax_band"):
            if not add(jar, "pocketmate", item, f"pixelmon:gui/inventory/{item}"):
                raise ValueError(f"Missing Pixelmon equipment icon for {item}")
        for path in sorted(names):
            if not path.startswith("data/pixelmon/pokeballs/") or not path.endswith(".json"):
                continue
            ball = json.loads(jar.read(path))
            name, sprite = ball["name"], ball["ballSprite"]
            if not re.fullmatch(r"[a-z0-9_]+", name):
                continue
            if sprite.startswith("pixelmon:item/") and not add(jar, "pixelmon", name, sprite):
                raise ValueError(f"Missing inventory texture for {name}")
        for path in sorted(names):
            if not path.startswith("assets/pixelmon/models/item/") or not path.endswith(".json"):
                continue
            model = json.loads(jar.read(path))
            sprite = model.get("textures", {}).get("layer0", "")
            if sprite.startswith("pixelmon:item/helditems/mega/"):
                item = Path(path).stem
                if not add(jar, "pixelmon", item, sprite):
                    raise ValueError(f"Missing Mega Stone texture for {item}")
    if pocketmate_mega is not None:
        with ZipFile(pocketmate_mega) as jar:
            catalog = json.loads(jar.read("pocketmate_mega_catalog.json"))
            for identifier in catalog["stones"]:
                if not re.fullmatch(r"pocketmate_mega:mega_stone_\d+", identifier):
                    continue
                namespace, item = identifier.split(":", 1)
                model = json.loads(jar.read(f"assets/{namespace}/models/item/{item}.json"))
                if not add(jar, namespace, item, model["textures"]["layer0"]):
                    raise ValueError(f"Missing Pocketmate Mega Stone texture for {item}")
    if not icons:
        raise ValueError("No Pixelmon ball icons found")
    output.mkdir(parents=True, exist_ok=True)
    for name, data in icons.items():
        (output / name).write_bytes(data)
    (output / "index.json").write_text(json.dumps(index, sort_keys=True) + "\n", encoding="utf-8")
    return len(icons)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pixelmon", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pocketmate-mega", type=Path)
    parser.add_argument("--minecraft", type=Path)
    args = parser.parse_args()
    print(f"Exported {export(args.pixelmon, args.output, args.pocketmate_mega, args.minecraft)} inventory icons")
