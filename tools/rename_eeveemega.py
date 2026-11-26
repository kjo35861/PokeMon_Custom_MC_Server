"""Change only EeveeMega's displayName; keep every other JAR entry intact."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tomllib
import zipfile

ORIGINAL_SHA256 = '9ed23a4b2bd8146481484b212a9b1fcf883607310d55f8378cf0847b4fc6f058'
OLD_NAME = 'eeveemega-1.21.1-1.1.0.jar'
NEW_NAME = 'PocketMate_Mega.jar'
METADATA = 'META-INF/neoforge.mods.toml'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def rename(source, output, targets, backup):
    source, output, backup = (p.resolve() for p in (source, output, backup))
    targets = [p.resolve() for p in targets]
    assert sha(source) == ORIGINAL_SHA256
    assert output.name == NEW_NAME and not output.exists() and not backup.exists()
    for target in targets:
        assert target.is_dir() and sha(target / OLD_NAME) == ORIGINAL_SHA256
        assert not (target / NEW_NAME).exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as old:
        assert not any(n.upper().endswith(('.SF', '.RSA', '.DSA', '.EC')) for n in old.namelist())
        metadata = old.read(METADATA)
        assert metadata.count(b'displayName = "EeveeMega"') == 1
        changed = metadata.replace(b'displayName = "EeveeMega"', b'displayName = "PocketMate_Mega"')
        with zipfile.ZipFile(output, 'w') as new:
            new.comment = old.comment
            for entry in old.infolist():
                new.writestr(entry, changed if entry.filename == METADATA else old.read(entry))
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(output) as new:
        assert new.testzip() is None and old.namelist() == new.namelist()
        differences = [n for n in old.namelist() if old.read(n) != new.read(n)]
        assert differences == [METADATA]
        before = tomllib.loads(old.read(METADATA).decode())
        after = tomllib.loads(new.read(METADATA).decode())
        assert after['mods'][0]['displayName'] == 'PocketMate_Mega'
        after['mods'][0]['displayName'] = before['mods'][0]['displayName']
        assert before == after
    backup.mkdir(parents=True)
    for number, target in enumerate(targets):
        original, installed = target / OLD_NAME, target / NEW_NAME
        saved = backup / str(number) / OLD_NAME
        saved.parent.mkdir()
        assert original.resolve().parent == target
        shutil.copy2(original, saved)
        temporary = installed.with_suffix('.jar.pending')
        shutil.copy2(output, temporary)
        try:
            # Move the original out of mods to avoid duplicate registration.
            original.rename(saved.with_suffix('.jar.moved'))
            os.replace(temporary, installed)
        except OSError:
            moved = saved.with_suffix('.jar.moved')
            if moved.exists() and not original.exists():
                moved.rename(original)
            temporary.unlink(missing_ok=True)
            raise
        assert sha(installed) == sha(output) and not original.exists()
    report = {'original_sha256': ORIGINAL_SHA256, 'renamed_sha256': sha(output),
              'filename': NEW_NAME, 'display_name': 'PocketMate_Mega',
              'mod_id': 'eeveemega', 'version': '1.1.0',
              'changed_jar_entries': differences, 'other_entries_byte_identical': True,
              'metadata_only_display_name_changed': True, 'crc_passed': True,
              'installed_locations': len(targets), 'restart_required': True,
              'game_started': False, 'in_game_verified': False}
    (backup / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', 'utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mods', type=Path, action='append', required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    rename(args.source, args.output, args.mods, args.backup)
