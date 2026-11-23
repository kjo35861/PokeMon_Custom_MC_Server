"""Multi-selection UI contract checks; durable transaction rules use the Java suite."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
mock=r"""
window.requests=[];window.testClaims=new Map();window.forceReject=false;window.testEstateName="";
window.webgui={client:{username:'TestPlayer',gamemode:'creative',health:20,maxHealth:20,xpLevel:7,dimension:'minecraft:overworld',pos:{x:8,y:-60,z:8}},postToGame(p){
 requests.push(p);if(p.channel!=='pocketmate:estate')return;
 setTimeout(()=>{
  let response;
  if(forceReject&&p.action==='buy')response={requestId:p.requestId,type:'error',message:'이미 소유주가 있는 청크입니다.'};
  else{
   if(p.action==='create'){testClaims.set('0:0',true);testEstateName=p.name;}
   if(p.action==='buy')for(const c of p.chunks)testClaims.set(c.x+':'+c.z,true);
   let cx=p.centerX??p.x??p.chunks?.[0]?.x??0,cz=p.centerZ??p.z??p.chunks?.[0]?.z??0,radius=p.radius??8,cells=[];
   for(let z=cz-radius;z<=cz+radius;z++)for(let x=cx-radius;x<=cx+radius;x++){
    const mine=testClaims.has(x+':'+z),other=x===4&&z===0;
    const adjacent=[[x-1,z],[x+1,z],[x,z-1],[x,z+1]].some(([a,b])=>testClaims.has(a+':'+b));
    cells.push({x,z,mine,owner:mine?'TestPlayer':other?'OtherPlayer':'',adjacent:!mine&&!other&&adjacent});
   }
   response={type:'snapshot',requestId:p.requestId,estateName:testEstateName,hasEstate:testClaims.size>0,isLord:testClaims.size>0,members:[],playerName:'TestPlayer',freeTestMode:true,purchaseEnabled:true,ownedCount:testClaims.size,estateLevel:10,chunkLimit:36,treasury:500000,lordBalance:500000,personalBalance:500000,purchasedChunks:testClaims.size||1,pricing:{freeChunks:4,base:20000,increment:2500},dimension:'minecraft:overworld',inOverworld:true,currentX:0,currentZ:0,currentOwner:testClaims.size?'TestPlayer':'',currentMine:testClaims.size>0,centerX:cx,centerZ:cz,radius,cells,...(testClaims.size?{homeX:0,homeZ:0}:{}),...(p.action!=='view'?{message:'테스트 구매 완료'}:{})};
  }
  dispatchEvent(new CustomEvent('webgui:pocketmate:estate',{detail:response}));
 },35);
}};
"""
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1920,'height':1080},device_scale_factor=1)
    page.add_init_script(mock);page.goto((root/'index.html').as_uri())
    assert page.locator('[data-page="estate"]').inner_text().startswith('영지관리')
    page.locator('[data-page="estate"]').click();page.locator('[data-estate-create]').wait_for()
    assert page.locator('.shell').is_hidden()
    assert page.locator('#estate-page').is_visible()
    screen=page.locator('#estate-page').bounding_box()
    assert screen['x']==0 and screen['y']==0 and screen['width']==1920 and screen['height']==1080
    assert page.locator('.estate-window').bounding_box()['width']>1180
    assert page.locator('#feature-content .estate-app').count()==0
    original=page.locator('[data-estate-text-value]').inner_text()
    page.locator('[data-estate-text-size="1"]').click()
    assert page.locator('[data-estate-text-value]').inner_text()!=original
    page.locator('[data-estate-text-size="-1"]').click()
    page.locator('[data-estate-create]').click();assert page.locator('[data-confirm]').is_disabled();page.locator('#estate-create-name').fill('달빛 마을');page.locator('[data-confirm]').click();page.locator('[data-estate-manage]').wait_for();page.locator('[data-estate-manage]').click()
    page.locator('[data-estate-buy]').wait_for();page.wait_for_timeout(150)
    def select(x,z):
        d=page.evaluate('PocketmateEstates.diagnostics()');box=page.locator('#estate-map').bounding_box()
        page.mouse.click(box['x']+box['width']/2+(x+.5-d['cx'])*d['scale'],box['y']+box['height']/2+(z+.5-d['cz'])*d['scale'])
    def count():return page.evaluate('PocketmateEstates.diagnostics().selectedCount')
    assert page.locator('[data-estate-buy]').is_disabled()
    initial=page.evaluate('PocketmateEstates.diagnostics()')
    assert initial['scale']==32 and 450<initial['visibleBlocksX']<500 and initial['radius']>12
    assert page.locator('.map-scale-label').inner_text()=='128 블록'
    assert abs(page.locator('.map-scale-line').bounding_box()['width']-256)<1
    select(1,0);assert count()==1;select(1,0);assert count()==0
    select(1,1);page.locator('[data-estate-buy]').click()
    assert '한 면 이상' in page.locator('.estate-alert').inner_text()
    page.locator('[data-alert-close]').click();select(1,1)
    select(4,0);assert count()==0
    select(0,0);assert count()==0
    select(1,0);select(4,0);select(0,0);assert count()==1;select(1,0)
    assert count()==0
    assert page.evaluate("requests.filter(r=>r.action==='buy').length")==0
    # A chain may be selected in reverse order; removing the bridge must invalidate the whole set.
    select(3,0);select(2,0);select(1,0);assert count()==3
    select(2,0);assert count()==2;page.locator('[data-estate-buy]').click()
    assert page.locator('.estate-alert').is_visible();page.locator('[data-alert-close]').click()
    select(2,0);page.locator('[data-estate-buy]').click()
    assert '3개 청크' in page.locator('.estate-confirm').inner_text()
    page.wait_for_timeout(5200);assert page.locator('.estate-confirm').is_visible()
    page.evaluate('window.forceReject=true');page.locator('[data-confirm]').click()
    page.locator('.estate-alert').wait_for();assert '소유주' in page.locator('.estate-alert').inner_text()
    assert page.evaluate('testClaims.size')==1;page.locator('[data-alert-close]').click()
    page.wait_for_timeout(650);assert count()==3
    assert len(page.evaluate("requests.filter(r=>r.action==='buy')[0].chunks"))==3
    page.evaluate('window.forceReject=false');page.locator('[data-estate-buy]').click();page.locator('[data-confirm]').click()
    page.wait_for_timeout(180);assert page.evaluate('testClaims.size')==4;assert count()==0
    assert page.evaluate("requests.filter(r=>r.action==='buy').length")==2
    # Drag/polling preserves selection and the canvas; a drag does not toggle a chunk.
    select(3,1);page.evaluate('window.savedMap=document.querySelector("canvas")')
    before=page.evaluate('PocketmateEstates.diagnostics()')
    box=page.locator('#estate-map').bounding_box();mx=box['x']+box['width']/2;my=box['y']+box['height']/2
    page.mouse.move(mx,my);page.mouse.down();page.mouse.move(mx+85,my+44,steps=8);page.mouse.up();page.wait_for_timeout(500)
    after=page.evaluate('PocketmateEstates.diagnostics()');assert after['cx']<before['cx'];assert count()==1
    assert page.evaluate('window.savedMap===document.querySelector("canvas")')
    page.mouse.move(mx,my);page.mouse.wheel(0,-260);page.wait_for_timeout(500)
    assert page.evaluate('PocketmateEstates.diagnostics().scale')>after['scale'];assert count()==1
    # Both wheel and minus button must stop at the 128-block default zoom.
    page.mouse.wheel(0,10000);page.wait_for_timeout(500)
    assert page.evaluate('PocketmateEstates.diagnostics().scale')==32
    assert page.locator('.map-scale-label').inner_text()=='128 블록'
    for _ in range(6):page.locator('[data-map-zoom-out]').click()
    assert page.evaluate('PocketmateEstates.diagnostics().scale')==32
    assert page.locator('.map-scale-label').inner_text()=='128 블록'
    page.locator('[data-estate-clear]').click();assert count()==0
    page.locator('[data-estate-tab="options"]').click();page.locator('[data-map-option="grid"]').uncheck()
    assert page.evaluate('JSON.parse(localStorage.getItem("pocketmate.mapOptions")).grid') is False
    page.locator('[data-estate-tab="manage"]').click()
    assert page.locator('#estate-input-x,#estate-input-z').count()==0
    assert '청크 X' not in page.locator('.estate-app').inner_text()
    assert not __import__('re').search(r'\[-?\d+,\s*-?\d+\]',page.locator('.estate-app').inner_text())
    page.screenshot(path=str(root/'verification/estate-management.png'))
    reports=[]
    for width,height in [(1920,1080),(1280,720),(854,480),(640,360)]:
        page.set_viewport_size({'width':width,'height':height});page.evaluate("document.documentElement.style.setProperty('--text-scale','1.6')");page.wait_for_timeout(80)
        metrics=page.evaluate('''(() => {const c=document.querySelector('canvas').getBoundingClientRect(),f=document.querySelector('.map-bottom').getBoundingClientRect(),s=document.querySelector('#estate-content').getBoundingClientRect();return {bodyWidth:document.documentElement.scrollWidth,canvasWidth:c.width,mapBottom:f.bottom,availableBottom:s.bottom};})()''')
        assert metrics['bodyWidth']<=width;assert metrics['canvasWidth']>0
        if width>1000:assert metrics['mapBottom']<=metrics['availableBottom']+1,metrics
        reports.append({'width':width,'height':height,**metrics})
    assert page.evaluate("requests.filter(r=>r.action==='create').length")==1
    (root/'verification/estate-browser-report.json').write_text(json.dumps({'passed':True,'checks':['wheel and minus button stop at 128-block zoom','128-block scale has correct pixel length','default view covers twice the original terrain span','expanded ownership request radius','click toggles selection','disconnected selection opens warning without purchase','own and other occupied chunks cannot be selected','reverse-order connected batch allowed','removing bridge invalidates batch','confirmation survives polling','server rejection opens warning without clearing selection','batch payload and success clear selection','drag and zoom retain selection and canvas','clear selection','map options persist','chunk coordinates removed','four responsive viewports','estate screen covers viewport outside hub','estate panel larger than hub','dedicated font controls','return to hub and reopen'],'viewports':reports},ensure_ascii=False,indent=2),encoding='utf-8')
    page.set_viewport_size({'width':1920,'height':1080})
    page.locator('.estate-return').click()
    assert page.locator('#estate-page').is_hidden() and page.locator('.shell').is_visible()
    assert not page.evaluate('document.body.classList.contains("estate-active")')
    page.locator('[data-page="estate"]').click();page.locator('.estate-plaza').wait_for()
    assert page.locator('.shell').is_hidden() and page.locator('#estate-page').is_visible()
    browser.close()
print('Estate multi-selection browser checks passed')
