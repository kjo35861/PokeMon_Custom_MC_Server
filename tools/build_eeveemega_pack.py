"""Derive version-pinned Pixelmon species overrides from a local installation.

Only the authored catalogue and generator belong in Git. Stock species JSON and
the user's recovered assets are read locally and written to an external build.
This tool never launches Minecraft or edits a world.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import zipfile
from pathlib import Path
from pixelmon_bmd_bounds import model_bounds, scale_to_height

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'estate_mod/mega_compat/catalog.json'
CUSTOM = {'Mega Sol': 'MegaSol', 'Dragonize': 'Dragonize', 'Aura Guard': 'AuraGuard',
          'Piercing Drill': 'PiercingDrill', 'Eelevate': 'Eelevate',
          'Fire Mane': 'FireMane', 'Spicy Spray': 'SpicySpray'}
STAT_KEYS = ('hp', 'attack', 'defense', 'specialAttack', 'specialDefense', 'speed')

def norm(value):
    return re.sub('[^a-z0-9]', '', value.lower()).replace('armour', 'armor')

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def ability_map(core, eevee):
    result = {}
    for jar in (core, eevee):
        for name in jar.namelist():
            if '/abilities/' not in name or not name.startswith('data/') or not name.endswith('.json'):
                continue
            value = json.loads(jar.read(name))
            cls = value.get('className', '').rsplit('.', 1)[-1]
            if cls:
                result[norm(cls)] = cls
    return result

def add_mapping(form, item, target):
    items, targets = form.setdefault('megaItems', []), form.setdefault('megas', [])
    if len(items) != len(targets) or any(not x or x == 'minecraft:air' for x in items):
        raise ValueError('Unsafe source mega mapping: ' + form['name'])
    if item in items:
        if targets[items.index(item)] != target:
            raise ValueError('A stone is already assigned to another target')
    else:
        items.append(item)
        targets.append(target)

def materialize_old_mappings(doc):
    """Pixelmon StatsTypeAdapter inherits every form from the first form."""
    original = copy.deepcopy(doc['forms'][0])
    for form in doc['forms']:
        for key in ('megaItems', 'megas'):
            if key not in form:
                form[key] = copy.deepcopy(original.get(key, []))

def model_resources(pack, slug, dex, form, height, size_audit):
    prefix = f'assets/pixelmon/textures/pokemon/{dex:03}_{slug}/all/{form}/'
    names = set(pack.namelist())
    models = sorted(n for n in names if n.startswith(prefix + 'none/') and n.endswith('.bmd')
                    and n.rsplit('/', 1)[-1] not in ('idle.bmd', 'walk.bmd'))
    if not models:
        return None, []
    model = models[0]
    bounds = model_bounds(pack.read(model))
    model_scale = scale_to_height(bounds, height)
    size_audit.append({'dex': dex, 'species': slug, 'form': form, 'model': model,
                      'reference_bounds': bounds, 'target_height_metres': height,
                      'previous_model_scale': 5.0, 'model_scale': model_scale,
                      'previous_reference_height_metres': bounds['height'] * 5.0 / 16.0,
                      'new_reference_height_metres': bounds['height'] * model_scale / 16.0})
    relative = lambda p: 'pixelmon:' + p.removeprefix('assets/pixelmon/textures/')
    palettes, files = [], []
    for palette in ('none', 'shiny'):
        texture = prefix + palette + '/texture.png'
        sprite = prefix + palette + '/sprite.png'
        if texture not in names or sprite not in names:
            if palette == 'none':
                raise ValueError('Missing required texture or sprite: ' + prefix)
            continue
        animations = []
        for kind in ('idle', 'walk'):
            resource = prefix + 'none/' + kind + '.bmd'
            if resource in names:
                animations.append({'type': kind, 'animation': relative(resource)})
        value = {'name': palette, 'sprite': relative(sprite),
                 'models': [{'model_predicate': {'type': 'pixelmon:always'}, 'models': [{
                     'texture': relative(texture), 'model': relative(model),
                     'animations': animations, 'scale': model_scale}]}],
                 'tags': ['shiny'] if palette == 'shiny' else []}
        if palette == 'shiny':
            value['particle'] = {'probability': .1, 'options': {'type': 'pixelmon:shiny',
                'diameter': 2.5, 'lifetime': 30, 'tint': {'red': 255, 'green': 215, 'blue': 0, 'alpha': 255}}}
        palettes.append(value)
    files = [n for n in names if n.startswith((prefix + 'none/', prefix + 'shiny/'))]
    return [{'gender': 'ALL', 'palettes': palettes}], files

def generated_target_name(row, source):
    return row['form'] if source == row['source_forms'][0] else row['form'] + '_' + source

def generate(core_path: Path, eevee_path: Path, pack_path: Path, output: Path):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    resources = output / 'resources'
    resources.mkdir(parents=True, exist_ok=False)
    report = {'minecraft': '1.21.1', 'pixelmon': '9.4.3', 'eeveemega': '1.1.0',
              'source_hashes': {}, 'forms': [], 'asset_paths': [], 'errors': []}
    for label, p in [('pixelmon', core_path), ('eeveemega', eevee_path), ('recovered_pack', pack_path)]:
        with p.open('rb') as source:
            report['source_hashes'][label] = hashlib.file_digest(source, 'sha256').hexdigest()
        if report['source_hashes'][label] != catalog['required_source_sha256'][label]:
            raise ValueError('Unsupported source artifact hash: ' + label)
    with zipfile.ZipFile(core_path) as core, zipfile.ZipFile(eevee_path) as eevee, zipfile.ZipFile(pack_path) as pack:
        abilities = ability_map(core, eevee)
        documents, originals, asset_names = {}, {}, set()
        for row in catalog['forms']:
            path = f"data/pixelmon/species/{row['dex']:03}_{row['slug']}.json"
            if path not in documents:
                doc = json.loads(core.read(path))
                originals[path] = copy.deepcopy(doc)
                materialize_old_mappings(doc)
                documents[path] = doc
            doc = documents[path]
            by_name = {f['name']: f for f in doc['forms']}
            gender, assets = model_resources(pack, row['slug'], row['dex'], row['form'],
                                             row['height'], report.setdefault('size_audit', []))
            asset_names.update(assets)
            for source in row['source_forms']:
                if source not in by_name:
                    raise ValueError(f"Missing source {row['species']}:{source}")
                target_name = generated_target_name(row, source)
                add_mapping(by_name[source], row['stone'], target_name)
                target = by_name.get(target_name)
                if target is None:
                    target = {'name': target_name, 'megaItems': [], 'megas': []}
                    doc['forms'].append(target)
                    by_name[target_name] = target
                target.update({'tags': list(dict.fromkeys(target.get('tags', []) + ['temp', 'mega'])),
                               'defaultBaseForm': source,
                               'battleStats': copy.deepcopy(row['stats']), 'types': row['types'],
                               'weight': row['weight']})
                mapped = {}
                for slot, name in row['ability_names'].items():
                    if norm(name) not in abilities:
                        raise ValueError('Unresolved ability ' + name)
                    mapped[slot] = abilities[norm(name)]
                target['abilities'] = {'abilities': [v for k, v in mapped.items() if k != 'H'],
                                       'hiddenAbilities': [mapped['H']] if 'H' in mapped else []}
                if gender:
                    target['genderProperties'] = copy.deepcopy(gender)
                    target['growth_data'] = {'mean': row['height'] * 100, 'standard_deviation': row['height'] * 5,
                                             'min_render_scale': .1, 'max_render_scale': 4.0}
                    target['dimensions'] = {'height': row['height'], 'width': min(row['height'], 3.0),
                                            'length': min(row['height'], 3.0)}
                elif 'genderProperties' not in target:
                    raise ValueError('No model for ' + row['species'])
                elif source == row['source_forms'][0]:
                    native = target['genderProperties'][0]['palettes'][0]['models'][0]['models'][0]
                    native_path = 'assets/pixelmon/textures/' + native['model'].split(':', 1)[1]
                    bounds = model_bounds(core.read(native_path))
                    measured = bounds['height'] * native['scale'] / 16.0
                    if not 0.5 <= measured / row['height'] <= 2.0:
                        raise ValueError('Native model requires separate size review: ' + row['species'])
                    report.setdefault('native_size_audit', []).append({
                        'species': row['species'], 'form': row['form'], 'model': native_path,
                        'model_scale': native['scale'], 'reference_height_metres': measured,
                        'catalog_height_metres': row['height'], 'action': 'retained_native_model'})
                report['forms'].append({'species': row['species'], 'dex': row['dex'], 'source': source,
                    'target': target_name, 'stone': row['stone'], 'stats': row['stats'],
                    'types': row['types'], 'abilities': target['abilities'],
                    'asset_source': 'recovered_pack' if gender else 'native_pixelmon'})
        for path, doc in documents.items():
            dump(resources / path, doc)
        # Copy only relevant Pokemon assets and verified existing stone art; no HUD, titles or cosmetics.
        numbers = {int(r['stone'].rsplit('_', 1)[1]) for r in catalog['forms'] if r['stone'].startswith('eeveemega:')}
        for name in pack.namelist():
            m = re.fullmatch(r'assets/eeveemega/(?:models|textures)/item/mega_stone_(\d+)\.(?:json|png)', name)
            if m and int(m.group(1)) in numbers and int(m.group(1)) < 54:
                asset_names.add(name)
        for name in sorted(asset_names):
            destination = resources / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(pack.read(name))
        lang = {}
        for row in catalog['forms']:
            if not row['stone'].startswith('eeveemega:'):
                continue
            item = row['stone'].split(':', 1)[1]
            lang['item.eeveemega.' + item] = row['stone_name_ko']
            if row['stone_binding_basis'] == 'authored_reserved_slot_assignment':
                # Deliberately generic vanilla icon; unknown old server art is never misidentified.
                dump(resources / f'assets/eeveemega/models/item/{item}.json',
                     {'parent': 'minecraft:item/generated', 'textures': {'layer0': 'minecraft:item/amethyst_shard'}})
        lang.update({'itemGroup.pocketmate_mega_bridge': '포켓메이트 메가진화',
                     'pixelmon.generic.form.megaz': '메가Z',
                     'pixelmon.generic.form.mega_droopy': '메가',
                     'pixelmon.generic.form.mega_stretchy': '메가',
                     'pixelmon.generic.form.mega_ten_percent': '메가'})
        dump(resources / 'assets/eeveemega/lang/ko_kr.json', lang)
        dump(resources / 'assets/pocketmate_mega_bridge/lang/ko_kr.json', lang)
        dump(resources / 'pocketmate_mega_catalog.json', {'stones': [r['stone'] for r in catalog['forms']]})
        # Explicit operator-only give function, usable even before native command autocomplete refreshes.
        function = resources / 'data/pocketmate_mega/function/stones.mcfunction'
        function.parent.mkdir(parents=True, exist_ok=True)
        function.write_text('\n'.join('give @s ' + r['stone'] + ' 1' for r in catalog['forms']) + '\n', encoding='utf-8')
        report['species_overrides'] = len(documents)
        report['catalog_mega_forms'] = len(catalog['forms'])
        report['asset_paths'] = sorted(asset_names)
        report['excluded_forms'] = validate(documents, originals, catalog, resources, core, eevee)
        # Standalone packs are alternatives to the bundled mod, not additional requirements.
        for filename, prefixes, fmt in [('pocketmate-eeveemega-data.zip', ('data/',), 48),
                                        ('pocketmate-eeveemega-resources.zip', ('assets/',), 34)]:
            with zipfile.ZipFile(output / filename, 'x', zipfile.ZIP_DEFLATED) as z:
                z.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': fmt,
                    'description': 'Pocketmate EeveeMega 1.1.0 / Pixelmon 9.4.3 compatibility'}}))
                for p in sorted(resources.rglob('*')):
                    if p.is_file() and p.relative_to(resources).as_posix().startswith(prefixes):
                        z.write(p, p.relative_to(resources).as_posix())
            with zipfile.ZipFile(output / filename) as z:
                if z.testzip():
                    raise ValueError('ZIP CRC error')
    report['validation'] = 'passed_static_constraints_and_archive_crc'
    dump(output / 'validation-report.json', report)
    return report

def validate(documents, originals, catalog, resources, core, eevee):
    excluded = []
    all_items = {r['stone'] for r in catalog['forms']}
    custom_items = {item for item in all_items if item.startswith('eeveemega:')}
    source_pairs = {(r['dex'], source): r for r in catalog['forms'] for source in r['source_forms']}
    for path, doc in documents.items():
        old = originals[path]
        forms = {f['name']: f for f in doc['forms']}
        if len(forms) != len(doc['forms']):
            raise ValueError('Duplicate form names')
        for original in old['forms']:
            form = forms[original['name']]
            if (doc['dex'], form['name']) not in source_pairs:
                if not set(form.get('tags', [])) & {'mega'}:
                    if set(form.get('megaItems', [])) & custom_items:
                        raise ValueError('Unintended form inherited custom mega mapping: ' + doc['name'] + ':' + form['name'])
                    excluded.append(f"{doc['name']}:{form['name']}")
            # Preserve every stock field on non-mega forms except the intentional mega mappings.
            if 'mega' not in original.get('tags', []):
                for key, value in original.items():
                    if key not in ('megaItems', 'megas') and form.get(key) != value:
                        raise ValueError('Changed original source field ' + key)
        for source in doc['forms']:
            items, targets = source.get('megaItems', []), source.get('megas', [])
            # Stock mega forms may carry item metadata for native boss drops.
            # Preserve that metadata; only non-mega source forms are evolution inputs.
            if 'mega' in source.get('tags', []):
                continue
            if len(items) != len(targets):
                raise ValueError('Mismatched mega array lengths')
            if any(not item or item == 'minecraft:air' for item in items):
                raise ValueError('Wildcard mega stone')
            for item, target in zip(items, targets):
                if target not in forms:
                    raise ValueError('Unknown mega target ' + target)
                intended = source_pairs.get((doc['dex'], source['name']))
                if intended and item == intended['stone']:
                    t = forms[target]
                    if t.get('defaultBaseForm') != source['name']:
                        raise ValueError('Incorrect original form reversion')
                    if not {'temp', 'mega'}.issubset(t.get('tags', [])):
                        raise ValueError('Missing temporary/mega tags')
                    if set(t['battleStats']) != set(STAT_KEYS):
                        raise ValueError('Incomplete battle stats')
        # Compare every output source's custom IDs with the independently authored contract.
        for source in doc['forms']:
            expected = {r['stone'] for r in catalog['forms'] if r['dex'] == doc['dex']
                        and source['name'] in r['source_forms'] and r['stone'].startswith('eeveemega:')}
            actual = set(source.get('megaItems', [])) & custom_items
            if actual != expected:
                raise ValueError('Wrong species/form stone contract: ' + doc['name'] + ':' + source['name'])
    return excluded

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixelmon', required=True, type=Path)
    parser.add_argument('--eeveemega', required=True, type=Path)
    parser.add_argument('--resourcepack', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = generate(args.pixelmon, args.eeveemega, args.resourcepack, args.output)
    print(json.dumps({k: report[k] for k in ('species_overrides', 'catalog_mega_forms', 'validation')}, ensure_ascii=False))

if __name__ == '__main__':
    main()
