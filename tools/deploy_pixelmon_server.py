"""Deploy the pinned server mods and Pocketmate pages without running Minecraft.

Backups and the detailed report stay outside the repository. Existing unrelated
mods, worlds, WebGUI secrets and extra web files are preserved.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import os
import shutil
import tomllib
import zipfile
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
PINNED = {
    'sophisticatedbackpacks-1.21.1-3.26.23.2263.jar': '8df6a8ebad2aebc71bc54e51eddd47fe931ed8bc338f7d1924e272ac72e38092',
    'sophisticatedcore-1.21.1-1.5.43.2504.jar': '6273cfa446b338f165a9c799ddd78fcb320fad0b519a70d969165b7518d3bac8',
    'accessories-neoforge-1.1.0-beta.54+1.21.1.jar': 'cbecac21acbaf323349afa263b22cda67c3e836f928f6cf3f951ba460c196d15',
    'owo-lib-neoforge-0.12.15.6-beta.1+1.21.jar': '5fc306ad3d42e1dc26812f2df856e7c232376405caab6af4f5aaffe89cd2b256',
    'Clumps-neoforge-1.21.1-19.0.0.1.jar': 'b524ccdace2ef8fd19f5b2074f7de1103ac5065c52553f064c00e098346c293e',
    'Jade-1.21.1-NeoForge-15.10.6.jar': '276f1f65a20d04f536989c4f311949d770b52c440c23c2b904a08860f3c93810',
    'appleskin-neoforge-mc1.21-3.0.9.jar': '38b48dd6231341c9f964ce6e42c57ec866c6cc8f72bec938390a59bafb3922df',
    'Pixelmon-1.21.1-9.4.3-universal.jar': '3700dd10bef8a16a6a740819d1e3b29df17067471ca01288cb6bb37d38470bfe',
    'PocketMate_Mega.jar': 'c132251daa6d90bc993440a228c92525bfb8ae8be965b7058e505e2f5e72f838',
    'pocketmate-mega-evolution-0.1.3.jar': '4bcde6ca102f61bcc5faa39194d54bff20109d6eb55f1fdb60dfba9abb7dcbb2',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pages():
    # Read the packaging allowlist as syntax; do not execute the packaging job.
    tree = ast.parse((ROOT / 'webgui_menu/package_estates.py').read_text('utf-8'))
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'files' for t in n.targets))
    names = ast.literal_eval(assignment.value.generators[0].iter)
    base = ROOT / 'webgui_menu'
    result = {Path(name): base / name for name in names}
    for directory, suffixes in [('profile-assets', {'.png', '.svg', '.txt'}),
                                ('icons', {'.svg'}), ('home-assets', {'.webp'})]:
        result.update({Path(directory) / p.name: p for p in (base / directory).iterdir()
                       if p.is_file() and p.suffix in suffixes})
    assert all(p.is_file() for p in result.values())
    return result


def metadata(path):
    with zipfile.ZipFile(path) as jar:
        return tomllib.loads(jar.read('META-INF/neoforge.mods.toml').decode('utf-8'))


def deploy(server, client, backup):
    server, client, backup = [p.resolve() for p in (server, client, backup)]
    assert (server / 'run.bat').is_file() and (server / 'mods').is_dir()
    assert not backup.is_relative_to(ROOT) and not backup.exists()
    assets = pages()
    sources = {name: client / 'mods' / name for name in PINNED}
    for name, source in sources.items():
        assert source.is_file() and sha(source) == PINNED[name], name
    # Fail on malformed runtime files before writing any deployment files.
    for base in (server, client):
        assert isinstance(json.loads((base / 'config/webgui/server.json').read_text('utf-8')), dict)
    assert (server / 'run.bat').read_bytes().splitlines()[0].strip().lower() == b'@echo off'
    wanted = {m['modId'] for p in sources.values() for m in metadata(p)['mods']}
    for existing in (server / 'mods').glob('*.jar'):
        ids = {m['modId'] for m in metadata(existing)['mods']}
        if ids & wanted and existing.name not in sources:
            raise RuntimeError(f'Conflicting mod requires review: {existing.name}')
    backup.mkdir(parents=True)
    changed = []

    def write(base, relative, data, label):
        target = (base / relative).resolve()
        assert target.is_relative_to(base)
        if target.exists() and target.read_bytes() == data:
            return
        previous = backup / label / relative
        if target.exists():
            previous.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, previous)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.pocketmate-deploy.tmp')
        temporary.write_bytes(data)
        os.replace(temporary, target)
        changed.append(f'{label}/{relative.as_posix()}')

    for name, source in sources.items():
        write(server, Path('mods') / name, source.read_bytes(), 'server')
    for base, label in [(server, 'server'), (client, 'client')]:
        for relative, source in assets.items():
            write(base, Path('config/webgui/web') / relative, source.read_bytes(), label)
        config_path = Path('config/webgui/server.json')
        config = json.loads((base / config_path).read_text('utf-8'))
        expected = {'mainMenuUrl': 'webgui://index.html', 'serveBundledPages': True,
                    'bundledPagesDir': 'web', 'autoHudOnJoin': False}
        if any(config.get(k) != v for k, v in expected.items()):
            config.update(expected)
            write(base, config_path, (json.dumps(config, ensure_ascii=False, indent=2) + '\n').encode(), label)
        assert all((base / 'config/webgui/web' / name).read_bytes() == p.read_bytes()
                   for name, p in assets.items())
    run = (server / 'run.bat').read_bytes()
    if b'cd /d "%~dp0"' not in run.lower():
        lines = run.splitlines(keepends=True)
        assert lines[0].strip().lower() == b'@echo off'
        lines.insert(1, b'cd /d "%~dp0" || exit /b 1\r\n')
        write(server, Path('run.bat'), b''.join(lines), 'server')
    installed = {name: sha(server / 'mods' / name) for name in sources}
    assert installed == PINNED
    ids = [m['modId'] for p in (server / 'mods').glob('*.jar') for m in metadata(p)['mods']]
    assert len(ids) == len(set(ids)), 'Duplicate mod IDs'
    assert {'pixelmon', 'tcg', 'eeveemega', 'pocketmate_mega_bridge', 'webgui', 'pocketmate_estates'} <= set(ids)
    report = {'checked_at': datetime.now().astimezone().isoformat(),
              'installed_mods': installed, 'web_file_count': len(assets),
              'server_and_client_pages_match_source': True,
              'unique_mod_ids': sorted(ids), 'working_directory_pinned': True,
              'game_or_server_started': False, 'in_game_verified': False,
              'server_restart_required': True, 'changed_files': changed}
    (backup / 'deployment-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    result = deploy(args.server, args.client, args.backup)
    print(json.dumps({k: v for k, v in result.items() if k != 'changed_files'}, ensure_ascii=False, indent=2))
    print(f"Changed {len(result['changed_files'])} files; backup: {args.backup}")
