"""Keep only Mega Pokemon and Mega Stone assets from the recovered Eevee pack.

The original archive is backed up outside resourcepacks. No game is started and
the selected pack filename is preserved, so options.txt is not modified.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

ORIGINAL_SHA256 = 'd4146d3a1eeebfc6f9064ee26948d7073621494255c6b0826fbbf3e73d2e3e8b'
FORMS = {'mega', 'megax', 'megay', 'megaz'}
STONE = re.compile(r'assets/eeveemega/(models|textures)/item/mega_stone_\d+\.(json|png)')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def mega_pokemon(name):
    parts = name.split('/')
    return (name.startswith('assets/pixelmon/textures/pokemon/') and len(parts) >= 9
            and parts[6] in FORMS and not name.endswith('/'))


def language(name, data):
    if name == 'assets/eeveemega/lang/ko_kr.json':
        return {k: v for k, v in data.items() if re.fullmatch(r'item\.eeveemega\.mega_stone_\d+', k)}
    if name == 'assets/pixelmon/lang/ko_kr.json':
        return {k: v for k, v in data.items() if re.search(r'\.form\.mega[xyz]?$', k)}
    return {}


def filter_pack(source, output, launcher, backup):
    source, output, launcher, backup = (p.resolve() for p in (source, output, launcher, backup))
    assert source.parent.name == 'resourcepacks' and source.suffix == '.zip'
    assert not output.exists() and not backup.exists()
    assert not backup.is_relative_to(source.parent)
    assert sha(source) == ORIGINAL_SHA256
    manifest_path = launcher / 'client-pack.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8-sig'))
    relative = 'resourcepacks/' + source.name
    entries = [entry for entry in manifest['files'] if entry['path'] == relative]
    assert len(entries) == 1
    entry = entries[0]
    assert entry['sha256'] == ORIGINAL_SHA256 and entry['url'].startswith('local:')
    local_root = (launcher / 'client-files').resolve()
    local = (local_root / entry['url'][6:]).resolve()
    assert local.is_relative_to(local_root) and sha(local) == ORIGINAL_SHA256
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as old:
        names = old.namelist()
        assert len(names) == len(set(names))
        retained = sorted(n for n in names if mega_pokemon(n) or STONE.fullmatch(n))
        translations = {n: language(n, json.loads(old.read(n))) for n in
                        ['assets/eeveemega/lang/ko_kr.json', 'assets/pixelmon/lang/ko_kr.json']}
        with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as new:
            new.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 34,
                'description': 'PocketMate - Mega Evolution resources only'}}, ensure_ascii=False))
            for name in retained:
                new.writestr(name, old.read(name))
            for name, data in translations.items():
                if data:
                    new.writestr(name, json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        with zipfile.ZipFile(output) as new:
            assert new.testzip() is None
            expected = set(retained) | {'pack.mcmeta'} | {n for n, d in translations.items() if d}
            assert set(new.namelist()) == expected
            assert all(old.read(n) == new.read(n) for n in retained)
            assert not any(n.startswith('assets/minecraft/') for n in new.namelist())
            assert not any('/' + folder + '/' in n for n in new.namelist()
                           for folder in ['gui', 'font', 'shaders', 'sounds'])
            for name in retained:
                if not name.endswith('.json'):
                    continue
                model = json.loads(new.read(name))
                assert model['parent'] in {'item/generated', 'minecraft:item/generated'}
                for texture in model.get('textures', {}).values():
                    namespace, texture_path = texture.split(':', 1)
                    assert f'assets/{namespace}/textures/{texture_path}.png' in expected
            stats = {'source_entries': len(names), 'output_entries': len(expected),
                     'mega_pokemon_files': sum(mega_pokemon(n) for n in retained),
                     'mega_stone_files': sum(bool(STONE.fullmatch(n)) for n in retained),
                     'language_keys': {n: len(d) for n, d in translations.items()},
                     'removed_files': len(set(names) - expected),
                     'retained_namespaces': sorted({n.split('/')[1] for n in expected if n.startswith('assets/')}),
                     'source_namespace_counts': dict(Counter(n.split('/')[1] for n in names if n.startswith('assets/')))}
    digest = sha(output)
    backup.mkdir(parents=True)
    shutil.copy2(source, backup / source.name)
    (backup / 'client-pack.json').write_bytes(manifest_bytes)
    originals = backup / source.name
    assert sha(originals) == ORIGINAL_SHA256
    entry.update({'sha256': digest, 'size': output.stat().st_size})
    manifest['packVersion'] += '-mega-only'
    assert manifest_path.read_bytes() == manifest_bytes, 'Manifest changed during filtering'
    applied = []
    try:
        for target in [source, local]:
            temporary = target.with_name(target.name + '.mega-only.pending')
            shutil.copy2(output, temporary)
            assert sha(temporary) == digest
            os.replace(temporary, target)
            applied.append(target)
        temporary = manifest_path.with_suffix('.json.mega-only.pending')
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf-8')
        os.replace(temporary, manifest_path)
    except OSError:
        for target in reversed(applied):
            shutil.copy2(originals, target)
        manifest_path.write_bytes(manifest_bytes)
        raise
    assert sha(source) == sha(local) == digest
    report = dict(stats, original_sha256=ORIGINAL_SHA256, filtered_sha256=digest,
                  filtered_bytes=output.stat().st_size, all_mega_assets_byte_identical=True,
                  item_texture_references_resolved=True, crc_passed=True,
                  vanilla_namespace_files=0, gui_font_shader_sound_files=0,
                  overlays_removed=True, launcher_manifest_updated=True,
                  selected_pack_filename_preserved=True, options_modified=False,
                  game_started=False, in_game_verified=False)
    (backup / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['source', 'output', 'launcher', 'backup']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(filter_pack(args.source, args.output, args.launcher, args.backup), ensure_ascii=False, indent=2))
