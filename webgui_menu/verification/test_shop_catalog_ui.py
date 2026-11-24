"""Mock shop protocol checks; never connects to the running game or wallet."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parents[1]
s=(r/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=s.split('mock=r"""',1)[1].split('"""',1)[0]
mock+=r'''
window.shopCalls=[];window.shopBalance=50000;window.shopVersion='fixed_test';window.shopOwned=10;window.shopReject=false;
const postOriginal=webgui.postToGame;
webgui.postToGame=function(p){if(p.channel!=='pocketmate:shop')return postOriginal.call(this,p);shopCalls.push(p);setTimeout(()=>{
 let error='',message='';
 if(p.action==='trade'){
  if(p.priceVersion!==shopVersion)error='가격이 갱신되었습니다.';
  else if(shopReject)error='저장하지 못했습니다.';
  else if(p.mode==='buy'&&shopBalance<p.quantity*100)error='개인 재화가 부족합니다.';
  else if(p.mode==='sell'&&shopOwned<p.quantity)error='수량이 부족합니다.';
  else{shopBalance+=(p.mode==='buy'?-100:50)*p.quantity;shopOwned+=(p.mode==='buy'?1:-1)*p.quantity;message='거래를 완료했습니다.';}
 }
 if(p.action==='quote'){dispatchEvent(new CustomEvent('webgui:pocketmate:shop',{detail:{type:'quote',requestId:p.requestId,item:p.item,mode:p.mode,unitPrice:p.mode==='buy'?100:50,owned:shopOwned,capacity:2304,maxQuantity:p.mode==='buy'?Math.min(2304,Math.floor(shopBalance/100)):shopOwned,balance:shopBalance,priceVersion:shopVersion}}));return;}
 if(p.action==='status'){dispatchEvent(new CustomEvent('webgui:pocketmate:shop',{detail:{type:'status',requestId:p.requestId,balance:shopBalance,priceVersion:shopVersion,buyPaused:false,sellPaused:false}}));return;}
 let names={building:['돌','참나무 판자'],colored:['하얀색 양털'],decoration:['횃불'],minerals:['철 원석'],crops:p.mode==='buy'?['밀 씨앗']:['밀']}[p.category]||[];
 let items=names.map((name,i)=>({id:'minecraft:'+({building:['stone','oak_planks'],colored:['white_wool'],decoration:['torch'],minerals:['raw_iron'],crops:p.mode==='buy'?['wheat_seeds']:['wheat']}[p.category][i]),name,buy:100,sell:['minerals','crops'].includes(p.category)?50:0,owned:shopOwned}));if(p.query)items=items.filter(i=>i.name.includes(p.query)||i.id.includes(p.query));
 dispatchEvent(new CustomEvent('webgui:pocketmate:shop',{detail:error?{type:'error',requestId:p.requestId,message:error}:{type:'snapshot',requestId:p.requestId,mode:p.mode,category:p.category,page:0,total:items.length,pages:1,balance:shopBalance,priceVersion:shopVersion,nextPriceAt:0,randomPrices:false,message,items}}));
 },70);};
'''
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':900});page.add_init_script(mock);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto((r/'index.html').as_uri());page.wait_for_timeout(400);page.locator('[data-page=shop]').click();page.locator('.shop-product').first.wait_for()
 assert page.locator('[data-shop-category]').count()==10
 assert page.locator('.shop-product').count()==2
 page.evaluate("dispatchEvent(new CustomEvent('webgui:pocketmate:shop-assets',{detail:{requestId:shopCalls.at(-1).requestId,icons:{}}}))")
 page.locator('[data-shop-item="minecraft:stone"]').click();page.locator('[data-shop-qty="16"]').click();assert '1,600원' in page.locator('.shop-trade-total').inner_text();page.locator('[data-shop-confirm]').click();page.wait_for_timeout(150);assert page.evaluate('shopBalance')==48400
 page.locator('[data-shop-mode=sell]').click();page.wait_for_timeout(150);assert page.locator('[data-shop-category=building]').is_disabled();assert page.locator('#shop-category-title').inner_text()=='광물'
 page.locator('[data-shop-item="minecraft:raw_iron"]').click();page.locator('[data-shop-confirm]').click();page.wait_for_timeout(150);assert page.evaluate('shopBalance')==48450
 for theme in ['dark','light']:
  page.evaluate('(t)=>PocketmateTheme.set(t)',theme);page.wait_for_timeout(250);page.screenshot(path=str(r/f'verification/shop-catalog-sell-{theme}-mock.png'))
 page.locator('[data-shop-mode=buy]').click();page.wait_for_timeout(150)
 for category in ['balls','held','zcrystals','megastones']:
  page.locator('[data-shop-category='+category+']').click();page.wait_for_timeout(120);assert page.locator('.shop-product').count()==0 and '추후' in page.locator('.shop-empty').inner_text()
 page.locator('[data-shop-category=building]').click();page.wait_for_timeout(120);page.locator('.shop-search input').fill('돌');page.wait_for_timeout(450);assert page.locator('.shop-product').count()==1 and page.locator('.shop-search input').evaluate('(e)=>e===document.activeElement')
 page.locator('.shop-search input').fill('');page.wait_for_timeout(450)
 page.locator('[data-shop-item="minecraft:stone"]').click();page.wait_for_function("!document.querySelector('[data-shop-max]').disabled");page.locator('.shop-trade-dialog input').fill('1.5');assert page.locator('[data-shop-confirm]').is_disabled();page.locator('.shop-trade-dialog input').fill('1');page.evaluate('shopVersion="new_version"');page.locator('[data-shop-confirm]').click();page.wait_for_timeout(150);assert '갱신' in page.locator('.shop-feedback').inner_text() and page.evaluate('shopBalance')==48450
 page.locator('[data-shop-refresh]').click();page.wait_for_timeout(120);page.locator('[data-shop-item="minecraft:stone"]').click();page.wait_for_function("!document.querySelector('[data-shop-max]').disabled");page.evaluate('shopBalance=0');page.locator('[data-shop-confirm]').click();page.wait_for_timeout(150);assert '부족' in page.locator('.shop-feedback').inner_text()
 page.evaluate('shopBalance=50000');page.locator('[data-shop-refresh]').click();page.wait_for_timeout(120)
 for w,h in [(1440,900),(1280,720),(854,480),(640,360)]:
  page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(100);assert page.locator('#shop-page').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
  for b in page.locator('.shop-product').all():assert b.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
 page.set_viewport_size({'width':1440,'height':900});page.evaluate('PocketmateTheme.set("dark")');page.wait_for_timeout(250);page.screenshot(path=str(r/'verification/shop-catalog-buy-dark-mock.png'))
 assert all('price' not in c and 'total' not in c and 'balance' not in c for c in page.evaluate('shopCalls'))
 page.locator('#shop-page [data-go=home]').click();count=page.evaluate('shopCalls.length');page.clock.install();page.clock.fast_forward(20000);assert page.evaluate('shopCalls.length')==count
 assert not errors,errors
 browser.close()
(r/'verification/shop-catalog-ui-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'nine_product_categories_and_favorites':True,'pokemon_categories_empty':True,'buy_and_sell':True,'separate_prices':True,'quantity_validation':True,'korean_search_focus':True,'stale_price_rejected':True,'insufficient_balance_rejected':True,'no_client_prices':True,'viewport_sizes':4,'unmount_cancels_poll':True,'errors':errors},indent=2),encoding='utf-8')
print('Shop catalog UI checks passed')
