"""Headless mock: durable-order protocol, page boundaries and zero layout shift."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
base=(root/'verification/test_profile_ui.py').read_text('utf-8').split('mock=r"""',1)[1].split('"""',1)[0]
mock=base+r'''
window.adminCalls=[];window.rejectMove=false;window.adminRevision=0;
window.adminItems=Array.from({length:27},(_,i)=>({id:'minecraft:fixture_'+i,name:'검증 상품 '+String(i).padStart(2,'0'),category:'building',buy:true,sell:false,buyPrice:100,sellPrice:50,buyAllowed:true,sellAllowed:false}));
const previousPost=webgui.postToGame;
webgui.postToGame=p=>{if(p.channel!=='pocketmate:admin')return previousPost(p);adminCalls.push(p);setTimeout(()=>{
 const emit=detail=>dispatchEvent(new CustomEvent('webgui:pocketmate:admin',{detail:{...detail,requestId:p.requestId}}));
 if(p.action==='capabilities'){emit({type:'capabilities',canAdmin:true});return;}
 if(p.action==='move'&&(rejectMove||p.revision!==adminRevision)){emit({type:'error',message:'다른 관리자가 설정을 변경했습니다. 새로고침 후 다시 수정해주세요.'});return;}
 let message='';
 if(p.action==='move'){const i=adminItems.findIndex(x=>x.id===p.item),item=adminItems.splice(i,1)[0],a=adminItems.findIndex(x=>x.id===p.anchor);adminItems.splice(a+(p.position==='after'?1:0),0,item);adminRevision++;message='상점 품목 순서를 변경했습니다.';}
 if(p.action==='delete'){adminItems=adminItems.filter(x=>x.id!==p.item);adminRevision++;message='상점 목록에서 품목을 삭제했습니다.';}
 const list=adminItems.filter(x=>!p.query||x.name.includes(p.query)),page=Math.min(p.page||0,Math.floor((list.length-1)/24)),items=list.slice(page*24,page*24+24).map((x,i)=>({...x,previousItem:list[page*24+i-1]?.id||'',nextItem:list[page*24+i+1]?.id||''}));
 emit({type:'snapshot',canAdmin:true,revision:adminRevision,page,pages:Math.ceil(list.length/24),total:list.length,items,message,settings:{buyBase:100,sellBase:50,randomEnabled:false,intervalSeconds:3600,deviationPercent:15},audit:[],titles:[],status:{}});
 },35);};
'''

with sync_playwright() as playwright:
 browser=playwright.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':900});errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script(mock);page.goto((root/'index.html').as_uri())
 page.locator('#admin-open').wait_for(state='visible');page.locator('#admin-open').click()
 page.locator('[data-admin-move]').first.wait_for()
 before=page.locator('.admin-filters').bounding_box()
 assert page.locator('[data-admin-move]').first.is_disabled()
 page.locator('[data-admin-move="minecraft:fixture_0"][data-position=after]').click()
 page.wait_for_function('adminItems[1].id==="minecraft:fixture_0"')
 page.locator('.pm-notification').wait_for(state='visible')
 after=page.locator('.admin-filters').bounding_box();assert abs(before['y']-after['y'])<.5
 assert page.locator('.admin-feedback').count()==0
 assert page.locator('.admin-table tbody tr').first.inner_text().startswith('검증 상품 01')
 page.locator('[data-admin-page="1"]').click();page.wait_for_function('document.querySelector(".admin-pagination span").textContent.trim()==="2 / 2"')
 page.locator('[data-admin-move="minecraft:fixture_24"][data-position=before]').click()
 page.wait_for_function('document.querySelector(".admin-pagination span").textContent.trim()==="1 / 2"')
 assert page.evaluate('adminItems[23].id')=='minecraft:fixture_24'
 page.locator('[data-admin-search]').fill('검증 상품 02');page.wait_for_timeout(450)
 assert page.locator('.admin-table tbody tr').count()==1
 assert page.locator('[data-admin-move]').first.is_disabled() and page.locator('[data-admin-move]').last.is_disabled()
 page.locator('[data-admin-search]').fill('');page.wait_for_timeout(450)
 page.evaluate('rejectMove=true');revision=page.evaluate('adminRevision')
 page.locator('[data-admin-move][data-position=after]').first.click();page.locator('.pm-notification[data-error=true]').wait_for(state='visible')
 assert page.evaluate('adminRevision')==revision
 assert abs(page.locator('.admin-filters').bounding_box()['y']-before['y'])<.5
 page.locator('.pm-notification button').click();assert page.locator('.pm-notification').is_hidden()
 page.evaluate('rejectMove=false')
 page.locator('[data-admin-delete]').first.click();page.locator('[data-admin-delete-confirm]').click()
 page.get_by_text('상점 목록에서 품목을 삭제했습니다.',exact=True).wait_for(state='visible')
 assert abs(page.locator('.admin-filters').bounding_box()['y']-before['y'])<.5
 for theme in ['dark','light']:
  page.evaluate('(t)=>PocketmateTheme.set(t)',theme)
  page.screenshot(path=str(root/f'verification/admin-order-notification-v0.24-{theme}-mock.png'))
 page.wait_for_timeout(4700);assert page.locator('.pm-notification').is_hidden()
 for width,height in [(1920,1080),(1280,720),(390,844)]:
  page.set_viewport_size({'width':width,'height':height})
  page.evaluate('PocketmateNotify.show("상점 품목 순서를 변경했습니다.")')
  popup=page.locator('.pm-notification').bounding_box()
  assert popup['x']>=0 and popup['x']+popup['width']<=width+1
  assert popup['y']>=0 and popup['y']+popup['height']<=height+1
 assert not errors,errors
 browser.close()

report={'permission_checked_by_backend_tests':True,'move_request_and_updated_order':True,'cross_page_move':True,'filtered_boundaries':True,'stale_error_keeps_order':True,'success_and_error_popup_zero_layout_shift':True,'popup_manual_close_and_auto_dismiss':True,'themes':2,'viewport_sizes':4,'game_tested':False,'errors':errors}
(root/'verification/admin-order-notifications-report.json').write_text(json.dumps(report,indent=2)+'\n','utf-8')
print('Admin ordering and popup mock checks passed')
