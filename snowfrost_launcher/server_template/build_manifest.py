"""Build a hashed Pocketmate content manifest; optionally serve it on loopback."""
import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import quote, urlsplit
import os

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--version', required=True, help='Published pack version, e.g. 2026.11.23.1')
parser.add_argument('--base-url', help='Public HTTPS base URL ending in /, or loopback for tests')
loaders = parser.add_mutually_exclusive_group()
loaders.add_argument('--fabric', help='Fabric loader version, e.g. 0.16.14')
loaders.add_argument('--neoforge', help='NeoForge version, e.g. 21.1.123')
loaders.add_argument('--vanilla', action='store_true', help='Explicitly publish a vanilla pack; default is Fabric 0.20.1')
parser.add_argument('--serve', action='store_true', help='Serve this folder locally for testing')
parser.add_argument('--port', type=int, default=18765)
args = parser.parse_args()
base = args.base_url or (f'http://127.0.0.1:{args.port}/' if args.serve else '')
address = urlsplit(base)
if address.scheme != 'https' and not (address.scheme == 'http' and address.hostname in ('127.0.0.1', 'localhost', '::1')):
    parser.error('Use --base-url https://your-host/ or --serve for loopback testing.')
base = base.rstrip('/')+'/'
files = []
loader = {'type':'vanilla'} if args.vanilla else {'type':'neoforge','version':args.neoforge} if args.neoforge else {'type':'fabric','version':args.fabric or '0.20.1'}
for folder in ('mods', 'resourcepacks', 'config', 'shaderpacks'):
    source = root/'files'/folder
    source.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob('*')):
        if path.is_symlink():
            parser.error('Links are not supported in published content.')
        if not path.is_file():
            continue
        relative = path.relative_to(root/'files').as_posix()
        if folder == 'mods' and args.vanilla:
            parser.error('Mod files require --fabric LOADER_VERSION or --neoforge LOADER_VERSION.')
        files.append({'path':relative, 'url':base+'files/'+quote(relative, safe='/'),
                      'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'size':path.stat().st_size})
manifest = {'formatVersion':1,'serverId':'pocketmate','minecraftVersion':'1.21.1',
            'packVersion':args.version,'loader':loader,'files':files}
(root/'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False),encoding='utf-8')
print(f'Manifest ready: {len(files)} files; set launcher update URL to {base}manifest.json', flush=True)
if args.serve:
    os.chdir(root)
    print('Local test server only. Stop with Ctrl+C.', flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),SimpleHTTPRequestHandler).serve_forever()
