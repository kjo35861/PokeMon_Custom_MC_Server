"""Replace the launcher after its executable is unlocked; never stop an app."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import time


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def apply(manifest):
    source, target, backup = (Path(manifest[k]).resolve() for k in ['source', 'target', 'backup'])
    assert source != target and target.suffix.lower() == '.exe'
    assert not backup.is_relative_to(target.parent)
    assert sha(source) == manifest['new_sha256']
    current = sha(target)
    if current == manifest['new_sha256']:
        return True
    if current != manifest['old_sha256']:
        raise ValueError('Launcher changed since staging; refusing to overwrite it')
    backup.mkdir(parents=True, exist_ok=True)
    saved = backup / (target.name + '.bak')
    if not saved.exists():
        shutil.copy2(target, saved)
    assert sha(saved) == manifest['old_sha256']
    temporary = target.with_name(target.name + '.foreground-update.pending')
    try:
        shutil.copy2(source, temporary)
        assert sha(temporary) == manifest['new_sha256']
        os.replace(temporary, target)
    except PermissionError:
        temporary.unlink(missing_ok=True)
        return False
    assert sha(target) == manifest['new_sha256']
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text('utf-8'))
    deadline = time.monotonic() + 86400
    while True:
        try:
            installed = apply(data)
            result = {'status': 'installed' if installed else 'pending_executable_lock',
                      'sha256': data['new_sha256'], 'processes_stopped': False}
        except (OSError, ValueError, AssertionError) as error:
            result = {'status': 'blocked', 'reason': type(error).__name__, 'processes_stopped': False}
            installed = False
        args.manifest.with_name('status.json').write_text(json.dumps(result, indent=2)+'\n', 'utf-8')
        if installed or result['status'] == 'blocked' or args.once or time.monotonic() >= deadline:
            print(json.dumps(result))
            break
        time.sleep(1)
