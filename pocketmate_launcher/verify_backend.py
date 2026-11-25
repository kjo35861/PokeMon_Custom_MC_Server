"""Exercise the compiled launcher against a loopback update server, without real login."""
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import subprocess
import threading
import zipfile
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--backend-only', action='store_true')
parser.add_argument('--output', type=Path)
args = parser.parse_args()

ROOT = Path(__file__).resolve().parent
EXE = Path(os.environ.get('POCKETMATE_TEST_EXE', str(ROOT/'dist/PocketmateLauncher.exe'))).resolve()
OUT = args.output.resolve() if args.output else ROOT/'verification'
FIXTURES = OUT/'update-fixtures'
FIXTURES.mkdir(parents=True, exist_ok=True)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def zip_pack(version):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 34, 'description': f'Pocketmate update test {version}'}}))
    return stream.getvalue()


server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(FIXTURES)))
base = f'http://127.0.0.1:{server.server_port}/'


def file(path, name, content):
    target = FIXTURES/name
    target.write_bytes(content)
    return {'path': path, 'url': base+name, 'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}


cfg1 = file('config/managed.json', 'config1.json', b'{"value":1}')
cfg2 = file('config/managed.json', 'config2.json', b'{"value":2}')
pack1 = file('resourcepacks/test.zip', 'pack1.zip', zip_pack(1))
pack2 = file('resourcepacks/test.zip', 'pack2.zip', zip_pack(2))
def manifest(name, version='1', files=None, **extra):
    value = {'formatVersion':1, 'serverId':'pocketmate', 'minecraftVersion':'1.21.1', 'packVersion':version, 'loader':{'type':'vanilla'}, 'files':files if files is not None else [cfg1,pack1]}
    value.update(extra)
    (FIXTURES/name).write_text(json.dumps(value), encoding='utf-8')
    return value


manifest('manifest-v1.json')
manifest('manifest-v2.json', '2', [pack2])
manifest('manifest-locked.json', '2', [cfg2,pack2])
manifest('manifest-bad.json', '2', [cfg2,dict(pack2,sha256='0'*64)])
manifest('manifest-version.json', minecraftVersion='1.21.4')
manifest('manifest-traversal.json',files=[dict(cfg1,path='config/../escape.json')])
manifest('manifest-missing-files.json',files=None)
bad=json.loads((FIXTURES/'manifest-missing-files.json').read_text());bad.pop('files');(FIXTURES/'manifest-missing-files.json').write_text(json.dumps(bad))
manifest('manifest-duplicates.json',files=[cfg1,dict(cfg1,path='CONFIG/managed.json')])
manifest('manifest-mods-without-loader.json',files=[dict(pack1,path='mods/example.jar')])
manifest('manifest-fabric.json',files=[],loader={'type':'fabric','version':'0.16.14'})
default_fabric=manifest('manifest-default-fabric.json',files=[])
default_fabric.pop('loader')
(FIXTURES/'manifest-default-fabric.json').write_text(json.dumps(default_fabric))
manifest('manifest-neoforge.json',files=[],loader={'type':'neoforge','version':'21.1.123'})
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
try:
    root=Path(os.environ['LOCALAPPDATA'])/'PocketmateLauncherVerification'/('backend-'+os.urandom(6).hex())
    report=OUT/'backend-report.json'
    process=subprocess.run([str(EXE),'--backend-test',str(report),'--fixture-url',base,'--data-dir',str(root)],timeout=60,capture_output=True)
    result=json.loads(report.read_text(encoding='utf-8'))
    print(json.dumps(result,indent=2,ensure_ascii=False))
    assert process.returncode==0,result
    prism=root/'test-sandbox'/'Prism data'
    for label, endpoint, expected in ([] if args.backend_only else [('update','manifest-v1.json','업데이트'),('latest','manifest-v2.json','게임 시작'),('error','manifest-version.json','다시 확인'),('vanilla','','게임 시작'),('settings','','게임 시작')]):
        data=(root/'test-sandbox'/'updates-test') if label=='latest' else root/('ui-'+label)
        data.mkdir(parents=True,exist_ok=True)
        settings={'DisplayName':'포켓메이트','UpdateManifestUrl':base+endpoint if endpoint else '', 'PrismPath':str(prism/'prismlauncher.exe'),'PrismDataPath':str(prism),'PrismInstanceId':'1.21.1 test'}
        (data/'settings.json').write_text(json.dumps(settings),encoding='utf-8')
        # Seed only this fixture instance's update state for the 'latest' UI assertion.
        if label=='latest':
            owner_key=hashlib.sha256(str(data.resolve()).lower().encode()).hexdigest()[:16]
            base_instance=root/'test-sandbox'/'Custom instances'/'1.21.1 test'
            instance_key=hashlib.sha256(str(base_instance/owner_key).lower().encode()).hexdigest()[:16]
            target=base_instance.parent/('Pocketmate-Server-'+instance_key)
            target.mkdir(parents=True,exist_ok=True)
            for name in ['instance.cfg','mmc-pack.json']:
                (target/name).write_bytes((base_instance/name).read_bytes())
            (target/'pocketmate-instance.json').write_text('{}')
            state=data/'prism'/hashlib.sha256(str(target).lower().encode()).hexdigest()[:16]
            state.mkdir(parents=True,exist_ok=True)
            for name in ['pack-state.json','loader-state.json']:
                (state/name).write_bytes((data/name).read_bytes())
            game=target/'minecraft'
            (game/'resourcepacks').mkdir(parents=True,exist_ok=True)
            (game/'resourcepacks/test.zip').write_bytes((data/'game/resourcepacks/test.zip').read_bytes())
        preview=OUT/(label+'-preview.png')
        command=[str(EXE),'--render-preview',str(preview),'--data-dir',str(data)]
        if label=='settings':
            command.append('--preview-settings')
        p=subprocess.run(command,timeout=25)
        state=json.loads(Path(str(preview)+'.state.json').read_text(encoding='utf-8'))
        assert p.returncode==0 and state['button']==expected,state
        if not endpoint:
            assert not state['updateRequired'] and state['status']=='서버 업데이트 미연결',state
        print(json.dumps({'ui':label,'button':state['button'],'status':state['status']},ensure_ascii=False),flush=True)
finally:
    server.shutdown()
    server.server_close()
