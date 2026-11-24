from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parents[1]
a=(r/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=a.split('mock=r"""',1)[1].split('"""',1)[0]
b=(r/'verification/test_daily_missions_ui.py').read_text(encoding='utf-8');mock+=b.split("mock+=r'''",1)[1].split("'''",1)[0]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1920,'height':1080});page.add_init_script(mock);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def reopen():
  page.locator('[data-page="home"]').click();page.locator('[data-page="quests"]').click();page.wait_for_timeout(100)
 def reset():
  page.goto((r/'index.html').as_uri());page.wait_for_timeout(350);reopen()
 reset();button=page.locator('[data-mission-claim-all]');assert button.is_disabled()
 page.evaluate('missionState.tasks[0].progress=32;missionState.tasks[3].progress=32');reopen()
 page.evaluate("document.querySelector('[data-mission-claim-all]').click();document.querySelector('[data-mission-claim-all]').click()")
 page.wait_for_timeout(850)
 assert page.evaluate('missionState.tasks.filter(t=>t.claimed).length')==2
 assert page.evaluate("missionCalls.filter(c=>c.action==='claim').length")==2
 assert not page.evaluate('missionState.finalClaimed') and button.is_disabled()
 page.evaluate('missionState.tasks.forEach(t=>t.progress=t.target)');reopen();button.click();page.wait_for_timeout(1400)
 assert page.evaluate('missionState.tasks.every(t=>t.claimed)&&missionState.finalClaimed')
 assert page.evaluate("missionCalls.filter(c=>c.action==='claim').length")==6 and button.is_disabled()
 # A rejected save must stop the chain without marking a task claimed.
 reset();page.evaluate('missionState.tasks.forEach(t=>t.progress=t.target);rejectMission=true');reopen();button.click();page.wait_for_timeout(800)
 assert page.evaluate("missionCalls.filter(c=>c.action==='claim').length")==1
 assert page.evaluate('missionState.tasks.every(t=>!t.claimed)&&!missionState.finalClaimed')
 # Unmount cancels the delayed next request after the first authoritative acknowledgement.
 reset();page.evaluate('missionState.tasks.forEach(t=>t.progress=t.target)');reopen();button.click();page.wait_for_timeout(70);page.locator('[data-page="home"]').click();page.wait_for_timeout(600)
 assert page.evaluate("missionCalls.filter(c=>c.action==='claim').length")==1
 # Day rollover between queue items must never claim rewards for the new day.
 reset();page.evaluate('missionState.tasks.forEach(t=>t.progress=t.target)');reopen();button.click();page.wait_for_timeout(70);page.evaluate('missionState.date="2026-11-26";missionState.tasks.forEach(t=>{t.progress=0;t.claimed=false})');page.wait_for_timeout(800)
 assert page.evaluate("missionCalls.filter(c=>c.action==='claim').length")==2
 assert page.evaluate('missionState.tasks.every(t=>!t.claimed)')
 # Header addition must keep all five cards and final reward visible.
 reset()
 for w,h,scale in [(1920,1080,1),(1920,1080,1.6),(1440,900,1),(1440,900,1.6),(1366,768,1),(1366,768,1.6),(1280,720,1),(1280,720,1.6),(854,480,1)]:
  page.set_viewport_size({'width':w,'height':h});page.evaluate('(s)=>document.documentElement.style.setProperty("--text-scale",s)',str(scale));page.wait_for_timeout(80)
  assert page.locator('#page-scroll').evaluate('(e)=>e.scrollHeight-e.clientHeight')<=1,(w,h,scale)
  assert page.locator('[data-mission-claim-all]').is_visible()
  assert page.locator('.mission-card').evaluate_all('(es)=>es.every(e=>e.scrollHeight<=e.clientHeight+1)'),(w,h,scale)
 page.set_viewport_size({'width':1440,'height':900});page.evaluate('document.documentElement.style.setProperty("--text-scale","1")');page.screenshot(path=str(r/'verification/mission-claim-all-mock.png'))
 assert not errors,errors
 browser.close()
(r/'verification/mission-claim-all-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'partial_claims_only':True,'final_reward_included':True,'double_click_guard':True,'save_failure_stops':True,'unmount_stops':True,'rollover_rejected':True,'viewport_scale_cases':9,'errors':errors},indent=2),encoding='utf-8')
print('Bulk reward checks passed')
