"""Build a Xaero resource pack from the installed Pixelmon JAR."""
import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def build(pixelmon, output):
    prefix = "assets/pixelmon/"
    textures = "textures/pokemon/"
    radar = "assets/xaerominimap/entity/icon/"
    with ZipFile(pixelmon) as source:
        paths = {
            name.removeprefix(prefix) for name in source.namelist()
            if name.startswith(prefix + textures) and name.endswith(".png")
        }
        fallback = "textures/item/pokeballs/poke_ball.png"
        source.getinfo(prefix + fallback)
        variants = {"default": "outlined_sprite:pocketmate/pokeball.png"}
        sprites = {}
        for sprite in sorted(paths):
            if sprite.endswith("/sprite.png"):
                destination = "pocketmate/" + sprite.removeprefix(textures)
                sprites[destination] = sprite
                variants["pixelmon:" + sprite] = "normal_sprite:" + destination
        for texture in sorted(paths):
            if not texture.endswith("/texture.png"):
                continue
            folder = texture.rsplit("/", 1)[0]
            species = folder.split("/")[2]
            candidates = (
                f"{folder}/sprite.png",
                f"{folder.rsplit('/', 1)[0]}/none/sprite.png",
                f"{textures}{species}/all/base/none/sprite.png",
            )
            sprite = next((candidate for candidate in candidates if candidate in paths), None)
            if sprite:
                destination = "pocketmate/" + sprite.removeprefix(textures)
                sprites[destination] = sprite
                variants["pixelmon:" + texture] = "normal_sprite:" + destination
        if len(variants) < 2:
            raise ValueError("Pixelmon sprites could not be matched")
        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, "w", ZIP_DEFLATED) as pack:
            pack.writestr("pack.mcmeta", json.dumps({
                "pack": {"pack_format": 34, "description": "Pocketmate Pixelmon radar icons"}
            }))
            definition = {
                "variants": variants,
                "variantMethod": "space.pocketmate.estates.client.PixelmonRadarVariant.getVariant",
            }
            pack.writestr(radar + "definition/pixelmon/pixelmon.json", json.dumps(definition))
            pack.writestr(radar + "sprite/pocketmate/pokeball.png", source.read(prefix + fallback))
            for destination, sprite in sprites.items():
                pack.writestr(radar + "sprite/" + destination, source.read(prefix + sprite))
    return len(variants) - 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pixelmon", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(f"{build(args.pixelmon, args.output)} mapped sprite and texture IDs")
