"""Apply a staged, hash-pinned Mega helper update before starting the server.

Does not start/stop Minecraft. A locked old JAR causes a nonzero exit so the
launch script cannot continue with a partially applied update.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tomllib
import zipfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def retire_shop_entries(server, backup, replacements):
    if not replacements:
        return
    path = server / 'config/pocketmate-shop.json'
    state = json.loads(path.read_text('utf-8-sig'))
    original = json.dumps(state, sort_keys=True)
    retired = {'pocketmate_mega:' + slot for slot in replacements}
    for item in retired:
        state['overrides'].pop(item, None)
        for key in ('buyPrices', 'sellPrices'):
            state['prices'].get(key, {}).pop(item, None)
    for field in ('deleted', 'registrationBlocked', 'order'):
        if field in state:
            state[field] = [item for item in state[field] or [] if item not in retired]
    if json.dumps(state, sort_keys=True) == original:
        return
    backup.mkdir(parents=True, exist_ok=True)
    saved = backup / path.name
    if not saved.exists():
        shutil.copy2(path, saved)
    state['revision'] += 1
    pending = path.with_suffix('.json.mega-native.pending')
    pending.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', 'utf-8')
    os.replace(pending, path)


def apply(server, queue, backup, check=False):
    server, queue, backup = (p.resolve() for p in (server, queue, backup))
    data = json.loads((queue / 'update.json').read_text('utf-8'))
    mods = (server / 'mods').resolve()
    old, new = [(mods / data[key]).resolve() for key in ['old_name', 'new_name']]
    source = (queue / data['new_name']).resolve()
    assert old.parent == new.parent == mods and source.parent == queue
    assert old != new and sha(source) == data['new_sha256']
    with zipfile.ZipFile(source) as jar:
        metadata = tomllib.loads(jar.read('META-INF/neoforge.mods.toml').decode('utf-8'))
        assert metadata['mods'][0]['modId'] == 'pocketmate_mega_bridge'
        assert metadata['mods'][0]['version'] == data['version']
        assert jar.testzip() is None
        replacements = json.loads(jar.read('pocketmate_native_stones.json')) if data.get('retire_shop_entries') else {}
    if not old.exists() and new.exists() and sha(new) == data['new_sha256']:
        if not check:
            retire_shop_entries(server, backup, replacements)
            (queue / 'ready').unlink(missing_ok=True)
        return 'already installed'
    assert old.is_file() and sha(old) == data['old_sha256'] and not new.exists()
    if check:
        return 'ready; no server file changed'
    backup.mkdir(parents=True, exist_ok=True)
    saved = backup / old.name
    assert not saved.exists()
    temporary = new.with_suffix('.jar.pending')
    assert not temporary.exists()
    # Rename first. If the running JVM locks it, this fails without adding a
    # second mod ID or changing the original installation.
    old.rename(saved)
    try:
        shutil.copy2(source, temporary)
        assert sha(temporary) == data['new_sha256']
        os.replace(temporary, new)
    except (OSError, AssertionError):
        temporary.unlink(missing_ok=True)
        saved.rename(old)
        raise
    retire_shop_entries(server, backup, replacements)
    (queue / 'applied.json').write_text(json.dumps({'version': data['version'],
        'sha256': sha(new), 'old_archived': True, 'server_started_by_tool': False}, indent=2)+'\n', 'utf-8')
    (queue / 'ready').unlink(missing_ok=True)
    return 'installed ' + data['version'] + '; old JAR archived'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['server', 'queue', 'backup']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(apply(args.server, args.queue, args.backup, args.check))
