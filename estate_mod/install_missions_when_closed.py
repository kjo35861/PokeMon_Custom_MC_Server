"""Apply the pending daily missions mod after Java exits, without controlling the game."""
from pathlib import Path
import os,subprocess,time,shutil,hashlib,json,argparse
root=Path(__file__).resolve().parent.parent
game=Path(os.environ['APPDATA'])/'PrismLauncher/instances/포켓메이트 메뉴 테스트/minecraft'
source=root/'estate_mod/dist/pocketmate-estates-0.11.2.jar'
target=game/'mods'/source.name
pending=target.with_suffix('.jar.pending')
report=root/'webgui_menu/verification/mission-stat-crash-fix-report.json'
expected=hashlib.sha256(source.read_bytes()).digest()
parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
def install():
 r=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process java,javaw -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode or r.stdout.strip()!='0':return False
 if not pending.is_file() or hashlib.sha256(pending.read_bytes()).digest()!=expected:return False
 backup=root/'webgui_menu/verification/backups/before-mission-stat-crash-fix';backup.mkdir(parents=True,exist_ok=True)
 for p in target.parent.glob('pocketmate-estates-*.jar'):
  if p!=target:shutil.copy2(p,backup/p.name)
 os.replace(pending,target)
 for p in target.parent.glob('pocketmate-estates-*.jar'):
  if p!=target:p.unlink()
 assert hashlib.sha256(target.read_bytes()).digest()==expected
 value=json.loads(report.read_text(encoding='utf-8'));value['status']='installed';value['installed_hash_matches']=True;report.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
 return True
deadline=time.monotonic()+3600
while True:
 if install() or args.once or time.monotonic()>=deadline:break
 time.sleep(5)
