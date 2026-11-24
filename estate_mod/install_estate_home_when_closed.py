"""Install the staged mod once its old JAR is released, without controlling Minecraft."""
from pathlib import Path
import argparse,hashlib,json,os,time

parser=argparse.ArgumentParser()
parser.add_argument('--once',action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
game=Path(os.environ['APPDATA'])/'PrismLauncher/instances/포켓메이트 메뉴 테스트/minecraft'
old=game/'mods/pocketmate-estates-0.7.0.jar'
target=game/'mods/pocketmate-estates-0.8.0.jar'
pending=target.with_suffix('.jar.pending')
backup=root/'webgui_menu/verification/backups/before-v0.13.0/pocketmate-estates-0.7.0.jar'
report=root/'webgui_menu/verification/estate-home-install.json'
expected=hashlib.sha256((root/'estate_mod/dist'/target.name).read_bytes()).hexdigest()

def status(value):
    report.write_text(json.dumps({'status':value,'version':'0.8.0','restart_required':True},indent=2),encoding='utf-8')

def install():
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==expected and not old.exists():
        status('installed');return True
    if not pending.exists() or hashlib.sha256(pending.read_bytes()).hexdigest()!=expected:
        status('staged_file_missing_or_changed');return True
    moved=False
    try:
        if old.exists():os.replace(old,backup);moved=True
        os.replace(pending,target)
        status('installed');return True
    except PermissionError:
        if moved and not old.exists():os.replace(backup,old)
        status('waiting_for_game_to_release_old_jar');return False
    except OSError:
        if moved and not old.exists():os.replace(backup,old)
        status('file_update_failed');return True

deadline=time.monotonic()+3600
while True:
    if install() or args.once:break
    if time.monotonic()>=deadline:
        status('waiting_timed_out_run_installer_again_after_closing_game');break
    time.sleep(.25)
