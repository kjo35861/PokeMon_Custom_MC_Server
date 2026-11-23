from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
mock=r"""
window.calls=[];window.level=1;window.wallet=100000;window.treasury=0;window.claims=4;window.isLord=true;
window.limits=[1,4,6,9,12,16,20,24,28,32,36];window.costs=[0,0,50000,100000,200000,350000,550000,800000,1100000,1500000,2000000];
window.webgui={client:{username:'Lord'},postToGame(p){
 if(p.channel!=='pocketmate:estate')return;calls.push(p);
 setTimeout(()=>{
 if(p.action==='deposit'){treasury+=p.amount;wallet-=p.amount;}
 if(p.action==='upgrade'){treasury-=costs[level+1];level++;}
 if(p.action==='buy'){let remaining=Math.max(0,p.expectedTotal-treasury);wallet-=remaining;treasury=Math.max(0,treasury-p.expectedTotal);claims+=p.chunks.length;}
 const cells=[],radius=p.radius||8;for(let z=-radius;z<=radius;z++)for(let x=-radius;x<=radius;x++){const mine=z===0&&x>=0&&x<claims;cells.push({x,z,mine,owner:mine?'Lord':'',adjacent:!mine&&((z===0&&(x===claims||x===-1))||(Math.abs(z)===1&&x>=0&&x<claims))});}
 dispatchEvent(new CustomEvent('webgui:pocketmate:estate',{detail:{type:'snapshot',requestId:p.requestId,playerName:'Lord',estateName:'달빛 마을',hasEstate:true,isLord,freeTestMode:false,testEconomy:true,purchaseEnabled:isLord,ownedCount:claims,dimension:'minecraft:overworld',inOverworld:true,currentX:0,currentZ:0,currentOwner:'Lord',centerX:p.centerX||0,centerZ:p.centerZ||0,radius,cells,members:[],homeX:0,homeZ:0,estateLevel:level,chunkLimit:limits[level],treasury,personalBalance:wallet,lordBalance:isLord?wallet:0,purchasedChunks:claims,levels:limits.map((limit,level)=>({level,limit,cost:costs[level]})),pricing:{freeChunks:4,base:20000,increment:2500},vaultHistory:[],...(p.action!=='view'?{message:'변경 완료'}:{})}}));
 },50);
}};
"""
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1920,'height':1080});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script(mock);page.goto((root/'index.html').as_uri());page.locator('[data-page="estate"]').click();page.locator('.estate-plaza').wait_for()
    page.locator('[data-estate-tab="vault"]').click();assert page.locator('.estate-level-schedule tbody tr').count()==11
    assert page.locator('[data-estate-upgrade]').is_disabled()
    def deposit(amount):
        page.locator('[data-vault-deposit]').click();assert page.locator('[data-deposit-confirm]').is_disabled();page.locator('#vault-deposit-amount').fill(str(amount));page.locator('[data-deposit-confirm]').click();page.wait_for_timeout(100)
    deposit(30000);assert page.locator('[data-estate-upgrade]').is_disabled();deposit(20000);assert page.locator('[data-estate-upgrade]').is_enabled()
    page.locator('[data-estate-upgrade]').click();assert '50,000원' in page.locator('.estate-confirm').inner_text();page.wait_for_timeout(5200);assert page.locator('.estate-confirm').is_visible();page.locator('[data-confirm]').click();page.wait_for_timeout(120)
    assert page.evaluate('level')==2 and page.evaluate('treasury')==0 and page.evaluate('wallet')==50000
    page.locator('[data-estate-tab="manage"]').click();page.wait_for_timeout(200)
    def select(x,z=0):
        d=page.evaluate('PocketmateEstates.diagnostics()');box=page.locator('canvas').bounding_box();page.mouse.click(box['x']+box['width']/2+(x+.5-d['cx'])*d['scale'],box['y']+box['height']/2+(z+.5-d['cz'])*d['scale'])
    select(4);select(5);assert '42,500원' in page.locator('.estate-sidebar').inner_text()
    page.locator('[data-estate-buy]').click();assert '42,500원' in page.locator('.estate-confirm').inner_text();assert '영주 개인 재화' in page.locator('.estate-confirm').inner_text();page.locator('[data-confirm]').click();page.wait_for_timeout(140)
    assert page.evaluate('claims')==6 and page.evaluate('wallet')==7500
    request=page.evaluate("calls.find(p=>p.action==='buy')");assert request['expectedTotal']==42500 and request['expectedPurchasedChunks']==4
    select(6);page.locator('[data-estate-buy]').click();assert '최대 6청크' in page.locator('.estate-alert').inner_text();page.locator('[data-alert-close]').click();page.locator('[data-estate-clear]').click()
    page.evaluate('level=3;treasury=20000;wallet=10000');page.locator('[data-estate-refresh]').click();page.wait_for_timeout(140)
    select(6);select(7);page.locator('[data-estate-buy]').click();assert '22,500원' in page.locator('.estate-alert').inner_text();assert page.evaluate("calls.filter(p=>p.action==='buy').length")==1;page.locator('[data-alert-close]').click();page.locator('[data-estate-clear]').click()
    page.locator('[data-estate-tab="vault"]').click();page.screenshot(path=str(root/'verification/estate-vault.png'))
    page.evaluate('isLord=false;wallet=0');page.locator('[data-estate-refresh]').click();page.wait_for_timeout(140);assert page.locator('[data-estate-upgrade]').is_disabled();assert page.locator('[data-vault-deposit]').is_disabled()
    reports=[]
    for width,height in [(1920,1080),(1280,720),(854,480),(640,360)]:
        page.set_viewport_size({'width':width,'height':height});page.evaluate("document.documentElement.style.setProperty('--text-scale','1.6')");page.wait_for_timeout(100)
        metrics=page.evaluate('({body:document.documentElement.scrollWidth,width:innerWidth})');assert metrics['body']<=width;reports.append(metrics)
        page.locator('.estate-level-schedule tbody tr').last.scroll_into_view_if_needed();assert page.locator('.estate-level-schedule tbody tr').last.is_visible()
    assert not errors,errors
    (root/'verification/estate-economy-browser-report.json').write_text(json.dumps({'passed':True,'checks':['11 level steps','deposit validates and debits personal balance','insufficient vault blocks upgrade','confirmation survives polling','upgrade uses vault','multi-chunk sequential price quote','personal top-up shown and sent','chunk limit warning before request','combined insufficiency warning before request','non-lord cannot upgrade','4 responsive viewports at 160%'],'viewports':reports},ensure_ascii=False,indent=2),encoding='utf-8')
    browser.close()
print('Estate economy browser checks passed')
