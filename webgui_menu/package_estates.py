"""Package an explicit allowlist, excluding WebGUI secrets and saved-world data."""
from pathlib import Path
import zipfile,hashlib,json,os,argparse
parser=argparse.ArgumentParser();parser.add_argument('--allow-pending-deployment',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent
estate=root.parent/'estate_mod'
files={f'config/webgui/web/{name}':root/name for name in ['index.html','menu.css','menu.js','estate.css','estate-map.js','estate-app.js','estate-background.svg','theme.css','appearance.css','appearance.js','people.css','people.js','help.css','help.js','fonts.css','NanumSquareRound-LICENSE.txt','profile.js','profile.css','icons.css','icons.js','pocketmate-mark.png']}
files.update({
    'mods/pocketmate-estates-0.7.0.jar':estate/'dist/pocketmate-estates-0.7.0.jar',
    'client-only/pocketmate-webgui-alpha-0.1.0.jar':root/'transparency_fix/dist/pocketmate-webgui-alpha-0.1.0.jar',
    '메뉴 사용 안내.txt':root/'사용 안내.txt',
    '영지 설치와 운영.txt':estate/'설치와 운영.txt',
})
files.update({f'config/webgui/web/profile-assets/{p.name}':p for p in (root/'profile-assets').iterdir() if p.suffix in {'.png','.svg','.txt'}})
files.update({f'config/webgui/web/icons/{p.name}':p for p in (root/'icons').glob('*.svg')})
out=root/'PocketmateMenu-v0.12.5.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
    for target,source in files.items():archive.write(source,target)
    archive.writestr('client-only/설치 위치.txt','반투명 보완 JAR는 플레이어 PC의 minecraft/mods에 넣으세요. 전용 서버에는 필요하지 않습니다.\n'.encode('utf-8'))
report={'bundle':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}}
game=Path(os.environ['APPDATA'])/'PrismLauncher/instances/포켓메이트 메뉴 테스트/minecraft'
report['deployed_assets_match']=all((game/name).exists() and (game/name).read_bytes()==path.read_bytes() for name,path in files.items() if name.startswith(('config/','mods/')))
assert report['deployed_assets_match'] or args.allow_pending_deployment
(root/'verification/estate-package-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(out.name)
