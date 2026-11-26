"""Add configured Pocketmate Mega Stones to a stopped server's shop."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
from zipfile import ZipFile


def seed(shop, bridge, backup):
    with ZipFile(bridge) as jar:
        catalog = json.loads(jar.read("pocketmate_mega_catalog.json"))
        stones = list(dict.fromkeys(
            item for item in catalog["stones"]
            if re.fullmatch(r"pocketmate_mega:mega_stone_\d+", item)
        ))
        if not stones:
            raise ValueError("Pocketmate Mega Stone catalog is empty")
        for stone in stones:
            jar.getinfo(f"assets/pocketmate_mega/models/item/{stone.split(':')[1]}.json")

    original = json.loads(shop.read_text(encoding="utf-8-sig"))
    state = deepcopy(original)
    prices = state["prices"]
    rules = state.setdefault("overrides", {})
    new = 0
    stone_ids = set(stones)
    for field in ("deleted", "registrationBlocked"):
        state[field] = [item for item in (state.get(field) or []) if item not in stone_ids]
    for stone in stones:
        if stone in rules:
            if rules[stone]["category"] != "megastones":
                rules[stone]["category"] = "megastones"
            continue
        rules[stone] = {
            "id": stone, "category": "megastones", "buy": True, "sell": False,
            "buyPrice": prices.get("buyPrices", {}).get(stone, prices["buyBase"]),
            "sellPrice": prices.get("sellPrices", {}).get(stone, prices["sellBase"]),
        }
        new += 1
    if state == original:
        return len(stones), new
    state["revision"] += 1
    backup.mkdir(parents=True, exist_ok=True)
    saved = backup / shop.name
    if not saved.exists():
        shutil.copy2(shop, saved)
    staged = shop.with_suffix(".json.mega-seed.pending")
    staged.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(staged, shop)
    return len(stones), new


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("shop", "bridge", "backup"):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    total, new = seed(args.shop, args.bridge, args.backup)
    print(f"Pocketmate Mega Stone shop: {new} added, {total} supported")
