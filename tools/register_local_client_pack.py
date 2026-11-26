"""Take an explicit snapshot of a local test instance's installed content.

Run only when updating the curated local pack. The launcher never invokes this
tool automatically: later unregistered additions remain blocked at launch.
Existing registered entries and all instance files are preserved.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def register(instance, launcher, backup):
    instance, launcher, backup = (p.resolve() for p in (instance, launcher, backup))
    manifest_path = launcher / 'client-pack.json'
    manifest = json.loads(manifest_path.read_text('utf-8-sig'))
    config = json.loads((launcher / 'launcher-config.json').read_text('utf-8-sig'))
    assert config['localTestInstanceId'] == instance.parent.name
    assert manifest['serverId'] == 'pocketmate' and manifest['formatVersion'] == 1
    assert manifest['loader'] == {'type': 'neoforge', 'version': '21.1.248'}
    assert not backup.exists()
    existing = {x['path'].casefold(): x for x in manifest['files']}
    assert len(existing) == len(manifest['files'])
    additions = []
    for folder, suffix in [('mods', '.jar'), ('resourcepacks', '.zip')]:
        for source in sorted((instance / folder).iterdir()):
            if folder == 'resourcepacks' and source.is_dir():
                raise ValueError('Unpacked resource packs require a separate curated manifest')
            if not source.is_file() or source.suffix.lower() != suffix:
                continue
            relative = source.relative_to(instance).as_posix()
            assert source.resolve().is_relative_to(instance)
            digest, size = sha(source), source.stat().st_size
            if relative.casefold() in existing:
                approved = existing[relative.casefold()]
                assert approved['sha256'] == digest and approved['size'] == size, relative
                continue
            additions.append((source, {'path': relative, 'url': 'local:' + relative,
                                       'sha256': digest, 'size': size}))
    if not additions:
        return {'added': 0, 'existing_entries_preserved': True}
    backup.mkdir(parents=True)
    shutil.copy2(manifest_path, backup / 'client-pack.json')
    # Stage verified sources first; publish the manifest only when all are ready.
    for source, entry in additions:
        destination = (launcher / 'client-files' / entry['path']).resolve()
        assert destination.is_relative_to((launcher / 'client-files').resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            saved = backup / 'client-files' / entry['path']
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, saved)
        temporary = destination.with_name(destination.name + '.register.pending')
        shutil.copy2(source, temporary)
        assert sha(temporary) == entry['sha256']
        os.replace(temporary, destination)
    manifest['files'].extend(entry for _, entry in additions)
    manifest['packVersion'] = 'local-neoforge-client-' + datetime.now().strftime('%Y%m%d-%H%M%S')
    temporary = manifest_path.with_suffix('.json.register.pending')
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    os.replace(temporary, manifest_path)
    report = {'added': len(additions), 'registered_files': len(manifest['files']),
              'registered_mods': sum(x['path'].startswith('mods/') for x in manifest['files']),
              'registered_resourcepacks': sum(x['path'].startswith('resourcepacks/') for x in manifest['files']),
              'existing_entries_preserved': True, 'launcher_verification_unchanged': True,
              'instance_files_modified': False, 'game_started': False,
              'in_game_verified': False, 'pack_version': manifest['packVersion']}
    (backup / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['instance', 'launcher', 'backup']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(register(args.instance, args.launcher, args.backup), indent=2))
