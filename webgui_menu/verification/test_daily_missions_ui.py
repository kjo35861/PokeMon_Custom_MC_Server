"""Isolated daily mission browser checks; no live progress or rewards are changed."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
source=(root/'verification/test_profile_ui.py').read_text(encoding='utf-8')
mock=source.split('mock=r"""',1)[1].split('"""',1)[0]
mock+=r'''
window.missionCalls=[];window.missionReady=false;window.rejectMission=false;
window.missionState={date:'2026-11-25',resetAt:Date.now()+3600000,finalClaimed:false,rewardsConfigured:false,tasks:[
{id:'lumber',slot:0,name:'숲속의 나무꾼',description:'원목 32개 채집하기',target:32,progress:0,claimed:false},
{id:'wild',slot:1,name:'야생의 도전자',description:'야생 포켓몬 5마리 처치하기',target:5,progress:0,claimed:false},
{id:'capture',slot:2,name:'새로운 동료',description:'야생 포켓몬 2마리 포획하기',target:2,progress:0,claimed:false},
{id:'planks',slot:3,name:'목재 가공 전문가',description:'나무판자 32개 제작하기',target:32,progress:0,claimed:false},
{id:'walk',slot:4,name:'모험의 시작',description:'도보로 500블록 이동하기',target:500,progress:0,claimed:false}]};
const originalPost=webgui.postToGame;
webgui.postToGame=function(p){
 if(p.channel!=='pocketmate:missions')return originalPost.call(this,p);
 missionCalls.push(p);
 setTimeout(()=>{
  let error='';
  if(p.action==='claim'){
   const t=missionState.tasks.find(t=>t.id===p.taskId);
   if(p.date!==missionState.date)error='새로운 하루의 임무가 시작되었습니다.';
   else if(rejectMission)error='저장하지 못했습니다.';
   else if(p.taskId==='final'){
    if(missionState.finalClaimed||missionState.tasks.some(t=>t.progress<t.target))error='수령 불가';else missionState.finalClaimed=true;
   }else if(!t||t.claimed||t.progress<t.target)error='수령 불가';else t.claimed=true;
  }
  const response=error?{type:'error',requestId:p.requestId,message:error}:{type:'snapshot',requestId:p.requestId,pokemonReady:missionReady,missions:structuredClone(missionState)};
  dispatchEvent(new CustomEvent('webgui:pocketmate:missions',{detail:response}));
 },30);
};
'''
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1920,'height':1080});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script(mock);page.goto((root/'index.html').as_uri());page.wait_for_timeout(500)
 assert page.locator('[data-page="quests"]').inner_text().startswith('임무')
 assert '퀘스트' not in page.locator('body').inner_text()
 def reopen():
  page.locator('[data-page="home"]').click();page.locator('[data-page="quests"]').click();page.wait_for_timeout(150)
 reopen();assert page.locator('.mission-card').count()==5
 assert page.locator('.mission-connection').is_visible()
 assert page.locator('[data-mission-claim]:enabled').count()==0
 for theme in ['dark','light']:
  page.evaluate('(v)=>document.documentElement.dataset.theme=v',theme)
  for scale in ['1','1.6']:
   page.evaluate('(v)=>document.documentElement.style.setProperty("--text-scale",v)',scale)
   for card in page.locator('.mission-card').all():
    copy=card.locator('.mission-copy').bounding_box();button=card.locator('button').bounding_box()
    assert copy['x']+copy['width']<=button['x']+1
  page.evaluate('document.documentElement.style.setProperty("--text-scale","1")')
  page.screenshot(path=str(root/'verification'/('daily-missions-'+theme+'.png')))
 page.evaluate('missionState.tasks[0].progress=32');reopen()
 page.locator('[data-mission-claim="lumber"]').click();page.wait_for_timeout(100)
 assert page.locator('[data-mission-claim="lumber"]').is_disabled()
 assert page.locator('[data-mission-claim="lumber"]').inner_text()=='수령 완료'
 assert page.locator('[data-mission-claim="final"]').is_disabled()
 page.evaluate('missionReady=true;missionState.tasks.forEach(t=>t.progress=t.target)');reopen()
 assert page.locator('[data-mission-claim="final"]').is_enabled()
 page.locator('[data-mission-claim="final"]').click();page.wait_for_timeout(100)
 assert page.locator('[data-mission-claim="final"]').is_disabled()
 # Persistence is authoritative: mount again from a fresh server snapshot.
 reopen();assert '최종 보상 수령 완료' in page.locator('.mission-final').inner_text()
 # Reject a stale-day claim, then refresh to the reset day without retaining the old completion.
 page.evaluate('missionState.date="2026-11-26";missionState.finalClaimed=false;missionState.tasks.forEach(t=>{t.progress=0;t.claimed=false})')
 page.locator('[data-mission-claim="wild"]').click();page.wait_for_timeout(550)
 assert '2026-11-26' in page.locator('.mission-day').inner_text()
 assert page.locator('[data-mission-claim]:enabled').count()==0
 calls=page.evaluate('missionCalls.filter(p=>p.action==="claim")')
 assert all(set(c)=={'channel','action','requestId','date','taskId'} for c in calls)
 page.locator('[data-page="home"]').click();before=page.evaluate('missionCalls.length')
 page.clock.install();page.clock.fast_forward(6000)
 assert page.evaluate('missionCalls.length')==before
 assert not errors,errors
 browser.close()
(root/'verification/daily-missions-ui-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'five_categories':True,'renamed_mission_tab':True,'dark_light_and_text_scale':True,'no_overlapping_claim_buttons':True,'claim_and_final_gating':True,'stale_day_rejected_and_refreshed':True,'no_client_progress_payload':True,'polling_stops_on_unmount':True,'errors':errors},indent=2)+'\n',encoding='utf-8')
print('Mission UI: 5 slots, both themes, text size, claims, stale-day refresh, server-only progress and cleanup passed.')
