"""Static format/asset checks only; does not run Minecraft or install the draft."""
from pathlib import Path
from PIL import Image
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/design/legendary-titles/line-png-v3'
PACK=OUT/'resource-pack'
mapping=json.loads((OUT/'glyph-map.json').read_text(encoding='utf-8'))
provider=json.loads((PACK/'assets/pocketmate/font/legendary_titles.json').read_text(encoding='utf-8'))['providers'][0]
assert json.loads((PACK/'pack.mcmeta').read_text())['pack']['pack_format']==34
assert len(mapping)==94 and len({r['character'] for r in mapping})==94
assert provider['type']=='bitmap' and provider['height']==9 and provider['ascent']==8
assert len(provider['chars'])==6 and all(len(row)==16 for row in provider['chars'])
atlas=Image.open(PACK/'assets/pocketmate/textures/font/legendary_titles.png').convert('RGBA')
assert atlas.size==(768,288)
for index,entry in enumerate(mapping):
    row,column=divmod(index,16)
    assert provider['chars'][row][column]==entry['character']
    icon=Image.open(OUT/'icons'/f"{entry['dex']}.png").convert('RGBA')
    assert icon.size==(48,48) and icon.getbbox() is not None
    alpha=set(icon.getchannel('A').tobytes())
    assert 0 in alpha and 255 in alpha and len(alpha)>2,entry['dex']
    assert atlas.crop((column*48,row*48,(column+1)*48,(row+1)*48)).tobytes()==icon.tobytes()
for index in (94,95):
    row,column=divmod(index,16)
    assert provider['chars'][row][column]=='\0'
    assert atlas.crop((column*48,row*48,(column+1)*48,(row+1)*48)).getbbox() is None
examples=(OUT/'tellraw-examples.txt').read_text(encoding='utf-8').splitlines()
assert len(examples)==94
for example,entry in zip(examples,mapping):
    data=json.loads(example.removeprefix('/tellraw @s '));glyph,title,name=data['extra']
    assert glyph['text']==entry['character'] and glyph['font']==entry['font']
    assert glyph['color']=='white' and glyph['bold'] is False
    assert title['font']=='minecraft:default' and title['color']==entry['color']
print('94 smooth PNGs: transparency/antialiasing, atlas cells, font chars, 1.21.1 pack metadata and tellraw examples passed. Game untested.')
