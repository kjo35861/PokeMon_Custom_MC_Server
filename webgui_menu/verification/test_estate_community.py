from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
mock=r"""
window.requests=[];window.viewerLord=true;window.estateExists=true;window.imageValue='';window.noticeValue='환영합니다!';
window.members=[{id:'lord',name:'Lord',role:'LORD',online:true,lastSeen:1700000000000},{id:'alice',name:'Alice',role:'RESIDENT',online:false,lastSeen:1700000000000}];
window.invited=false;
window.webgui={client:{username:'Lord'},postToGame(p){requests.push(p);setTimeout(()=>{
 if(p.action==='players'){
  let list=[{id:'bob',name:'Bob',online:true,available:!invited,status:invited?'초대 대기':'초대 가능'},{id:'alice',name:'Alice',online:false,available:false,status:'영지 소속'}].filter(v=>p.query?v.name.toLowerCase().includes(p.query.toLowerCase()):v.online);
  dispatchEvent(new CustomEvent('webgui:pocketmate:estate',{detail:{type:'players',requestId:p.requestId,players:list}}));return;
 }
 if(p.action==='invite')invited=true;
 if(p.action==='role')members.find(m=>m.id===p.target).role=p.role;
 if(p.action==='kick')members=members.filter(m=>m.id!==p.target);
 if(p.action==='notice')noticeValue=p.text;
 if(p.action==='image')imageValue=p.image;
 if(p.action==='deleteEstate')estateExists=false;
 const cells=[];for(let z=-8;z<=8;z++)for(let x=-8;x<=8;x++)cells.push({x,z,owner:estateExists&&x===0&&z===0?'Lord':'',mine:estateExists&&x===0&&z===0,adjacent:Math.abs(x)+Math.abs(z)===1});
 const response={type:'snapshot',requestId:p.requestId,playerName:viewerLord?'Lord':'Alice',estateName:estateExists?'달빛 마을':'',hasEstate:estateExists,isLord:estateExists&&viewerLord,freeTestMode:true,purchaseEnabled:viewerLord,ownedCount:estateExists?1:0,dimension:'minecraft:overworld',inOverworld:true,currentX:0,currentZ:0,currentOwner:estateExists?'Lord':'',centerX:0,centerZ:0,radius:8,cells,members:estateExists?members:[],announcement:noticeValue,image:imageValue,outgoingInvites:invited?[{id:'bob',name:'Bob',at:1700000000000}]:[],incomingInvites:[],...(p.action!=='view'?{message:'변경 저장 완료'}:{})};
 dispatchEvent(new CustomEvent('webgui:pocketmate:estate',{detail:response}));
 },45);}};
"""
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1920,'height':1080});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.add_init_script(mock);page.goto((root/'index.html').as_uri());page.evaluate('document.fonts.ready')
 assert page.evaluate("document.fonts.check('14px NanumSquareRound')")
 before=page.locator('.shell').evaluate('(e)=>getComputedStyle(e).backgroundColor')
 page.locator('[data-page="estate"]').click();page.locator('.estate-plaza').wait_for()
 assert page.locator('.estate-window').evaluate('(e)=>getComputedStyle(e).backgroundColor')==before
 assert page.locator('body').evaluate('(e)=>getComputedStyle(e).fontFamily').startswith('NanumSquareRound')
 assert '달빛 마을' in page.locator('.estate-header h1').inner_text()
 assert '환영합니다!' in page.locator('.estate-announcement').inner_text()
 assert 'Alice' in page.locator('.estate-plaza-roster').inner_text() and '오프라인' in page.locator('.estate-plaza-roster').inner_text()
 # Save notice through the lord-only editor.
 page.locator('[data-estate-notice]').click();page.locator('#estate-notice-text').fill('새로운 공지\n함께해요');page.locator('[data-save-notice]').click();page.wait_for_timeout(100)
 assert '새로운 공지' in page.locator('.estate-announcement').inner_text()
 # File upload uses a real PNG fixture, browser resizing/JPEG preview, and one save request.
 fixture=page.evaluate("""(()=>{const c=document.createElement('canvas');c.width=100;c.height=60;const x=c.getContext('2d');x.fillStyle='#8aa882';x.fillRect(0,0,100,60);return c.toDataURL('image/png').split(',')[1]})()""")
 import base64
 page.locator('[data-estate-image-file]').set_input_files({'name':'cover.png','mimeType':'image/png','buffer':base64.b64decode(fixture)})
 page.locator('[data-image-save]').wait_for();page.locator('[data-image-save]').click();page.wait_for_timeout(100)
 assert page.locator('.estate-cover').get_attribute('src').startswith('data:image/jpeg;base64,')
 page.screenshot(path=str(root/'verification/estate-plaza-v0.8.png'))
 page.locator('.estate-nav [data-estate-tab="members"]').click();assert page.locator('[data-estate-invite]').is_visible()
 # Invite dialog starts with current online players, then filters by typed nickname.
 page.locator('[data-estate-invite]').click();page.locator('[data-invite-user="bob"]').wait_for();assert page.locator('[data-invite-user="alice"]').count()==0
 page.locator('#estate-player-search').fill('ali');page.locator('[data-invite-user="alice"]').wait_for();assert page.locator('[data-invite-user="alice"]').is_disabled()
 page.locator('#estate-player-search').fill('Bob');page.locator('[data-invite-user="bob"]').wait_for();page.locator('[data-invite-user="bob"]').click();page.wait_for_timeout(100)
 assert 'Bob' in page.locator('.estate-outgoing').inner_text()
 page.locator('[data-role-target="alice"]').select_option('STEWARD');page.locator('[data-confirm]').click();page.wait_for_timeout(100)
 assert page.locator('[data-role-target="alice"]').input_value()=='STEWARD'
 page.locator('[data-member-kick="alice"]').click();page.locator('[data-confirm]').click();page.wait_for_timeout(100);assert page.locator('[data-role-target="alice"]').count()==0
 # Delete stays above the final settings item, and exact spelling is required.
 order=page.locator('.estate-nav button').evaluate_all('(buttons)=>buttons.map(b=>b.textContent)')
 assert '영지 삭제' in order[-2] and '지도 설정' in order[-1]
 page.locator('[data-estate-delete]').click();assert page.locator('[data-confirm-delete]').is_disabled()
 page.locator('#estate-delete-name').fill('달빛마을');assert page.locator('[data-confirm-delete]').is_disabled()
 page.locator('#estate-delete-name').fill('달빛 마을 ');assert page.locator('[data-confirm-delete]').is_disabled()
 page.locator('#estate-delete-name').fill('달빛 마을');assert page.locator('[data-confirm-delete]').is_enabled()
 page.locator('[data-cancel]').click();assert page.evaluate("requests.filter(r=>r.action==='deleteEstate').length")==0
 # Non-lord has a read-only plaza and member roster, never administrative buttons.
 page.evaluate('viewerLord=false');page.locator('[data-estate-refresh]').click();page.wait_for_timeout(100)
 assert page.locator('[data-estate-delete]').count()==0
 page.locator('[data-estate-tab="overview"]').click();assert page.locator('[data-estate-notice],[data-estate-image]').count()==0
 page.locator('.estate-nav [data-estate-tab="members"]').click();assert page.locator('[data-estate-invite],[data-role-target],[data-member-kick]').count()==0
 # Preview responsive views including a scaled font.
 page.evaluate('viewerLord=true');page.locator('[data-estate-refresh]').click();page.wait_for_timeout(100);page.locator('[data-estate-tab="overview"]').click()
 for width,height in [(1920,1080),(1280,720),(854,480),(640,360)]:
  page.set_viewport_size({'width':width,'height':height});page.evaluate("document.documentElement.style.setProperty('--text-scale','1.6')");page.wait_for_timeout(80)
  assert page.evaluate('document.documentElement.scrollWidth')<=width
  assert page.locator('.estate-window').bounding_box()['width']<=width
 assert not errors,errors
 (root/'verification/estate-community-browser-report.json').write_text(json.dumps({'passed':True,'checks':['shared colors','local rounded font','named estate plaza','lord notice editor','image upload preview and persistence payload','online players and name search','invite action','role change','kick confirmation','delete above settings','exact-name deletion gate with cancel','non-lord read-only controls','four responsive viewports'],'page_errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
 browser.close()
print('Estate community browser checks passed')
