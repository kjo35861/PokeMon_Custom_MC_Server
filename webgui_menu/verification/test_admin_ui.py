"""Admin mock permission + editing flow checks; no live player/config mutations."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parents[1]
s=(r/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=s.split('mock=r"""',1)[1].split('"""',1)[0]
mock+=r'''
window.op=false;window.adminCalls=[];window.adminState={revision:0,page:0,pages:1,total:1,items:[{id:'minecraft:raw_iron',name:'철 원석',category:'minerals',buy:true,sell:true,buyPrice:100,sellPrice:50,buyAllowed:true,sellAllowed:true}],settings:{buyBase:100,sellBase:50,randomEnabled:false,intervalSeconds:3600,deviationPercent:15},buyPaused:false,sellPaused:false,estatePurchasesPaused:false,missionRewardsPaused:false,maintenanceReason:'',audit:[],status:{modVersion:'0.13.0',estateReady:true,estates:1,chunks:1,memberLimit:5,maxEstateLevel:10,maxChunks:36,missionResetAt:Date.now()+3600000,pokemonReady:false}};
const originalAdminPost=webgui.postToGame;
webgui.postToGame=function(p){if(p.channel!=='pocketmate:admin')return originalAdminPost.call(this,p);adminCalls.push(p);setTimeout(()=>{
 if(p.action==='capabilities'){dispatchEvent(new CustomEvent('webgui:pocketmate:admin',{detail:{type:'capabilities',requestId:p.requestId,canAdmin:op}}));return;}
 let error='',forbidden=false;
 if(!op){error='OP 권한이 필요합니다.';forbidden=true;}
 else if(p.action==='lookup'){const items=p.query==='몬스터볼'?[{id:'pixelmon:poke_ball',name:'몬스터볼',registrationAllowed:false,registrationEditable:true}]:[{id:'minecraft:stone',name:'돌',category:'building',buyAllowed:true,sellAllowed:false}];dispatchEvent(new CustomEvent('webgui:pocketmate:admin',{detail:{type:'lookup',requestId:p.requestId,items}}));return;}
 else if(p.action!=='view'&&p.revision!==adminState.revision)error='다른 관리자가 설정을 변경했습니다.';
 else if(p.action==='upsert'){const row={id:p.item,name:p.item==='minecraft:stone'?'돌':'철 원석',category:p.itemCategory,buy:p.buy,sell:p.sell,buyPrice:p.buyPrice,sellPrice:p.sellPrice,buyAllowed:true,sellAllowed:p.item!=='minecraft:stone'};adminState.items=adminState.items.filter(i=>i.id!==p.item).concat([row]);adminState.revision++;}
 else if(p.action==='disable'){const row=adminState.items.find(i=>i.id===p.item);if(p.side!=='sell')row.buy=false;if(p.side!=='buy')row.sell=false;adminState.revision++;}
 else if(p.action==='configure'){for(const key of ['buyBase','sellBase','randomEnabled','intervalSeconds','deviationPercent'])adminState.settings[key]=p[key];for(const key of ['buyPaused','sellPaused','estatePurchasesPaused','missionRewardsPaused','maintenanceReason'])adminState[key]=p[key];adminState.revision++;}
 if(error)dispatchEvent(new CustomEvent('webgui:pocketmate:admin',{detail:{type:'error',requestId:p.requestId,message:error,forbidden}}));else{adminState.total=adminState.items.length;dispatchEvent(new CustomEvent('webgui:pocketmate:admin',{detail:{...structuredClone(adminState),type:'snapshot',requestId:p.requestId,canAdmin:true}}));}
 },35);};
'''
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':900});page.add_init_script(mock);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto((r/'index.html').as_uri());page.wait_for_timeout(400)
 assert page.locator('#admin-open').is_hidden()
 page.evaluate('document.querySelector("#admin-open").click()');assert page.locator('#admin-page').is_hidden();page.locator('#dialog-ok').click()
 page.wait_for_timeout(2100)
 page.evaluate('op=true;dispatchEvent(new CustomEvent("webgui:client",{detail:webgui.client}))');page.locator('#admin-open').wait_for(state='visible');page.locator('#admin-open').click();page.locator('[data-admin-edit]').wait_for()
 page.locator('[data-admin-edit]').click();page.locator('[name=buyPrice]').fill('200');page.locator('[name=sellPrice]').fill('75');page.locator('.admin-dialog button[type=submit]').click();page.wait_for_timeout(120);assert page.evaluate('adminState.items[0].buyPrice')==200
 page.locator('[data-admin-disable]').click();page.locator('[data-admin-cancel]').click();assert page.evaluate('adminState.revision')==1
 page.locator('[data-admin-disable]').click();page.locator('[data-remove-side]').select_option('sell');page.locator('[data-admin-remove]').click();page.wait_for_timeout(120);assert not page.evaluate('adminState.items[0].sell')
 page.locator('[data-admin-add]').click();page.locator('[data-admin-lookup]').fill('돌');page.locator('[data-pick]').wait_for();page.locator('[data-pick]').click();assert page.locator('[name=item]').input_value()=='minecraft:stone';assert page.locator('[name=sell]').is_disabled();page.locator('.admin-dialog button[type=submit]').click();page.wait_for_timeout(120);assert page.evaluate('adminState.items.length')==2
 page.locator('[data-admin-add]').click();page.locator('[data-admin-lookup]').fill('몬스터볼')
 blocked=page.locator('[data-pick]',has_text='등록 비허용')
 blocked.click()
 assert page.locator('[name=registrationQuery]').input_value()=='pixelmon:poke_ball'
 assert page.locator('[data-registration-filter]').input_value()=='blocked'
 assert page.evaluate('adminCalls.at(-1).registrationQuery')=='pixelmon:poke_ball'
 page.locator('[data-admin-tab=policy]').click();page.wait_for_timeout(120);page.locator('[name=randomEnabled]').check();page.locator('[name=buyPaused]').check();page.locator('[name=estatePurchasesPaused]').check();page.locator('[name=missionRewardsPaused]').check();page.locator('[name=maintenanceReason]').fill('운영 점검');page.locator('[data-admin-policy] button[type=submit]').click();page.wait_for_timeout(120);assert page.evaluate('adminState.buyPaused&&adminState.estatePurchasesPaused&&adminState.missionRewardsPaused')
 for tab in ['items','policy','status','audit']:
  page.locator('[data-admin-tab='+tab+']').click();page.wait_for_timeout(120)
  for theme in ['dark','light']:
   page.evaluate('(t)=>PocketmateTheme.set(t)',theme);page.wait_for_timeout(200)
   if tab in ['items','policy']:page.screenshot(path=str(r/f'verification/admin-{tab}-{theme}-mock.png'))
 page.locator('[data-admin-tab=items]').click();page.wait_for_timeout(100);page.locator('[data-admin-edit]').first.click();page.evaluate('adminState.revision++');page.locator('.admin-dialog button[type=submit]').click();page.wait_for_timeout(120);assert '다른 관리자' in page.locator('.pm-notification').inner_text()
 for w,h in [(1280,720),(854,480),(640,360)]:
  page.set_viewport_size({'width':w,'height':h});page.evaluate('document.documentElement.style.setProperty("--text-scale","1.6")');page.wait_for_timeout(60);assert page.locator('#admin-page').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
 page.evaluate('op=false');page.locator('[data-admin-refresh]').click();page.wait_for_timeout(120);assert page.locator('#admin-page').is_hidden() and page.locator('#admin-open').is_hidden()
 assert not errors,errors
 browser.close()
(r/'verification/admin-ui-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'non_op_button_hidden':True,'direct_route_denied':True,'op_entry':True,'edit_prices':True,'remove_cancel_and_confirm':True,'lookup_and_add':True,'pause_and_random_policy':True,'stale_revision_rejected':True,'revocation_closes_page':True,'themes':2,'viewport_sizes':4,'errors':errors},indent=2),encoding='utf-8')
print('Admin permission and editor UI checks passed')
