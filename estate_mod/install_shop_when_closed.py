"""Install the queued shop build only after Java exits. Never starts/stops Minecraft or Prism."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,time
root=Path(__file__).resolve().parent.parent
queue=root/'webgui_menu/verification/backups/pending-shop-v0.20.0'
game=Path(os.environ['APPDATA'])/'PrismLauncher/instances/포켓메이트 메뉴 테스트/minecraft'
report=root/'webgui_menu/verification/shop-install-report.json'
parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
def install():
 check=subprocess.run(['powershell','-NoProfile','-Command','@(Get-Process java,javaw -ErrorAction SilentlyContinue).Count'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if check.returncode or check.stdout.strip()!='0':return False
 manifest=json.loads((queue/'manifest.json').read_text(encoding='utf-8'))
 for name,digest in manifest.items():
  if hashlib.sha256((queue/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Queued build changed; refusing to install')
 backup=root/'webgui_menu/verification/backups/before-shop-v0.20.0';backup.mkdir(parents=True,exist_ok=True)
 mods=(game/'mods').resolve();assert mods.is_relative_to(game.resolve())
 for old in mods.glob('pocketmate-estates-*.jar'):
  assert old.resolve().parent==mods
  if not (backup/old.name).exists():shutil.copy2(old,backup/old.name)
 for name in manifest:
  target=(game/name).resolve();assert target.is_relative_to(game.resolve())
  target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():
   saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True)
   if not saved.exists():shutil.copy2(target,saved)
  temp=target.with_suffix(target.suffix+'.pending');shutil.copy2(queue/name,temp);os.replace(temp,target)
 for old in mods.glob('pocketmate-estates-*.jar'):
  if old.name!='pocketmate-estates-0.12.0.jar':
   assert old.resolve().parent==mods;old.unlink()
 assert all(hashlib.sha256((game/name).read_bytes()).hexdigest()==digest for name,digest in manifest.items())
 report.write_text(json.dumps({'status':'installed','game_tested':False,'installed_hashes_match':True,'mod':'0.12.0','menu':'0.20.0'},indent=2)+'\n',encoding='utf-8')
 subprocess.run(['python',str(root/'webgui_menu/package_estates.py')],cwd=root,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 return True
deadline=time.monotonic()+86400
while True:
 try:
  if install():break
 except (OSError,ValueError,RuntimeError) as error:
  report.write_text(json.dumps({'status':'pending','game_tested':False,'installed_hashes_match':False,'reason':type(error).__name__},indent=2)+'\n',encoding='utf-8')
 if args.once or time.monotonic()>=deadline:break
 time.sleep(5)
