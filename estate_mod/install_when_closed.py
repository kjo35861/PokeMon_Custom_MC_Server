"""One-shot local file update; does not control or launch Minecraft."""
from pathlib import Path
import os,time,json,hashlib

root=Path(__file__).resolve().parent.parent
game=Path(os.environ['APPDATA'])/'PrismLauncher/instances/포켓메이트 메뉴 테스트/minecraft'
old=game/'mods/pocketmate-estates-0.6.0.jar'
target=game/'mods/pocketmate-estates-0.6.1.jar'
pending=game/'mods/pocketmate-estates-0.6.1.jar.pending'
backup=root/'webgui_menu/verification/backups/before-v0.10.1/pocketmate-estates-0.6.0.jar'
report=root/'webgui_menu/verification/member-limit-install.json'
expected=hashlib.sha256((root/'estate_mod/dist'/target.name).read_bytes()).hexdigest()
def status(value):report.write_text(json.dumps({'status':value,'version':'0.6.1'},indent=2),encoding='utf-8')
status('waiting_for_game_to_release_old_jar')
deadline=time.monotonic()+3600
while time.monotonic()<deadline:
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==expected:
        status('installed');break
    moved=False
    try:
        if not pending.exists() or hashlib.sha256(pending.read_bytes()).hexdigest()!=expected:
            status('staged_file_missing_or_changed');break
        if old.exists():os.replace(old,backup);moved=True
        os.replace(pending,target)
        status('installed');break
    except PermissionError:
        if moved and not old.exists():os.replace(backup,old)
        time.sleep(.25)
    except OSError:
        if moved and not old.exists():os.replace(backup,old)
        status('file_update_failed');break
else:status('waiting_timed_out_run_installer_again_after_closing_game')
