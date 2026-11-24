"""Install the queued shop favorites build only after Java exits. Never starts/stops Minecraft or Prism."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,time
root=Path(__file__).resolve().parent.parent
queue=root/'webgui_menu/verification/backups/pending-shop-v0.23.0'
game=Path(os.environ['APPDATA'])/'PrismLauncher/instances/포켓메이트 메뉴 테스트/minecraft'
report=root/'webgui_menu/verification/shop-favorites-install-report.json'
parser=argparse.ArgumentParser();parser.add_argument('--font-baseline',action='store_true');parser.add_argument('--pixel-font',action='store_true');parser.add_argument('--sharp-font',action='store_true');parser.add_argument('--font-fix',action='store_true');parser.add_argument('--once',action='store_true');args=parser.parse_args()
mod_version='0.15.4' if args.font_baseline else '0.15.3' if args.pixel_font else '0.15.2' if args.sharp_font else '0.15.1' if args.font_fix else '0.15.0'
menu_version='0.23.4' if args.font_baseline else '0.23.3' if args.pixel_font else '0.23.2' if args.sharp_font else '0.23.1' if args.font_fix else '0.23.0'
queue=root/f'webgui_menu/verification/backups/pending-shop-v{menu_version}'
if args.font_baseline:report=root/'webgui_menu/verification/shop-font-baseline-install-report.json'
elif args.pixel_font:report=root/'webgui_menu/verification/shop-pixel-font-install-report.json'
elif args.sharp_font:report=root/'webgui_menu/verification/shop-sharp-font-install-report.json'
elif args.font_fix:report=root/'webgui_menu/verification/shop-font-fix-install-report.json'
def install():
 check=subprocess.run(['powershell','-NoProfile','-Command','@(Get-Process java,javaw -ErrorAction SilentlyContinue).Count'],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if check.returncode or check.stdout.strip()!='0':return False
 manifest=json.loads((queue/'manifest.json').read_text(encoding='utf-8'))
 for name,digest in manifest.items():
  if hashlib.sha256((queue/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Queued build changed; refusing to install')
 backup=root/f'webgui_menu/verification/backups/before-shop-v{menu_version}';backup.mkdir(parents=True,exist_ok=True)
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
  if old.name!=f'pocketmate-estates-{mod_version}.jar':
   assert old.resolve().parent==mods;old.unlink()
 assert all(hashlib.sha256((game/name).read_bytes()).hexdigest()==digest for name,digest in manifest.items())
 report.write_text(json.dumps({'status':'installed','game_tested':False,'installed_hashes_match':True,'mod':mod_version,'menu':menu_version},indent=2)+'\n',encoding='utf-8')
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
