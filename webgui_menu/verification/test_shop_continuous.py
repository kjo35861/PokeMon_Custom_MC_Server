"""Headless fixtures only: continuous catalog, fresh MAX quotes and public pause notices."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parents[1]
source=(r/'verification/test_profile_ui.py').read_text(encoding='utf-8')
mock=source.split('mock=r"""',1)[1].split('"""',1)[0]
mock+=r'''
window.shopCalls=[];window.shopBalance=50000;window.shopOwned=81;window.shopCapacity=100;window.shopVersion='fixture1';window.buyPaused=false;window.sellPaused=false;window.quoteDelay=30;window.saleCategories=['minerals','crops'];
const originalShopPost=webgui.postToGame;
webgui.postToGame=function(p){if(p.channel!=='pocketmate:shop')return originalShopPost.call(this,p);shopCalls.push(p);setTimeout(()=>{
 const meta={balance:shopBalance,priceVersion:shopVersion,randomPrices:false,nextPriceAt:0,buyPaused,sellPaused,saleCategories,maintenanceReason:'상품 가격 점검 중입니다.'};
 let out={...meta,requestId:p.requestId};
 if(p.action==='status')out.type='status';
 else if(p.action==='quote')Object.assign(out,{type:'quote',item:p.item,mode:p.mode,unitPrice:p.mode==='buy'?100:50,owned:shopOwned,capacity:shopCapacity,maxQuantity:p.mode==='buy'?Math.min(shopCapacity,Math.floor(shopBalance/100)):shopOwned});
 else{
  let error='',message='';
  if(p.action==='trade'){
   if(p.priceVersion!==shopVersion)error='가격이 갱신되었습니다.';
   else if(p.mode==='buy'&&buyPaused||p.mode==='sell'&&sellPaused)error='거래가 일시정지되었습니다.';
   else if(p.mode==='buy'&&(p.quantity>shopCapacity||p.quantity*100>shopBalance))error='공간 또는 금액이 부족합니다.';
   else if(p.mode==='sell'&&p.quantity>shopOwned)error='판매 수량이 부족합니다.';
   else{shopBalance+=(p.mode==='buy'?-100:50)*p.quantity;shopOwned+=(p.mode==='buy'?1:-1)*p.quantity;message='거래를 완료했습니다.';}
  }
  let all=Array.from({length:p.category==='building'?75:['minerals','crops'].includes(p.category)?2:0},(_,i)=>({id:'minecraft:fixture_'+i,name:'테스트 상품 '+i,buy:100,sell:50,owned:shopOwned}));
  if(p.query)all=all.filter(i=>i.name.includes(p.query));const current=Math.min(p.page,Math.max(0,Math.ceil(all.length/24)-1));
  Object.assign(out,error?{type:'error',message:error}:{type:'snapshot',mode:p.mode,category:p.category,page:current,pages:Math.max(1,Math.ceil(all.length/24)),total:all.length,items:all.slice(current*24,(current+1)*24),message});
 }
 dispatchEvent(new CustomEvent('webgui:pocketmate:shop',{detail:out}));
},p.action==='quote'?quoteDelay:30);};
'''
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':900});page.add_init_script(mock);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto((r/'index.html').as_uri());page.wait_for_timeout(300);page.locator('[data-page=shop]').click();page.locator('.shop-product').first.wait_for()
 for _ in range(8):
  page.locator('.shop-main').evaluate('(e)=>e.scrollTop=e.scrollHeight');page.wait_for_timeout(160)
 assert page.locator('.shop-product').count()==75
 assert page.locator('[data-shop-page]').count()==0
 page.locator('[data-shop-refresh]').click();page.wait_for_timeout(150);assert page.locator('[data-shop-item]').first.get_attribute('data-shop-item')=='minecraft:fixture_0'
 for _ in range(8):
  page.locator('.shop-main').evaluate('(e)=>e.scrollTop=e.scrollHeight');page.wait_for_timeout(120)
 assert page.locator('.shop-product').count()==75
 assert len(set(page.locator('[data-shop-item]').evaluate_all('(es)=>es.map(e=>e.dataset.shopItem)')))==75
 # Icons arriving for older loaded batches still hydrate.
 page.evaluate("dispatchEvent(new CustomEvent('webgui:pocketmate:shop-assets',{detail:{requestId:shopCalls.findLast(c=>c.action==='view'&&c.page===0).requestId,icons:{'minecraft:fixture_0':'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='}}}))")
 assert page.locator('[data-shop-icon="minecraft:fixture_0"] img').count()==1
 page.locator('[data-shop-item="minecraft:fixture_74"]').click();page.locator('[data-shop-max]').click();assert page.locator('dialog input').input_value()=='100';assert '10,000원' in page.locator('.shop-trade-total').inner_text();assert page.evaluate("shopCalls.filter(c=>c.action==='trade').length")==0
 page.locator('[data-shop-confirm]').click();page.wait_for_timeout(150);assert page.evaluate('shopBalance')==40000;assert page.locator('.shop-product').count()==75
 assert page.locator('.shop-main').evaluate('(e)=>e.scrollTop>0')
 page.evaluate('shopBalance=250');page.locator('[data-shop-item="minecraft:fixture_74"]').click();page.locator('[data-shop-max]').click();assert page.locator('dialog input').input_value()=='2';page.locator('[data-shop-cancel]').click()
 page.locator('[data-shop-mode=sell]').click();page.wait_for_timeout(150);page.evaluate('shopOwned=81');page.locator('[data-shop-item]').first.click();page.locator('[data-shop-max]').click();assert page.locator('dialog input').input_value()=='81';page.locator('[data-shop-confirm]').click();page.wait_for_timeout(150);assert page.evaluate('shopOwned')==0
 building=page.locator('[data-shop-category=building]')
 assert building.is_disabled()
 page.evaluate("saleCategories=['minerals','crops','building']")
 page.locator('[data-shop-refresh]').click();page.wait_for_timeout(150)
 assert building.is_enabled()
 building.click();page.locator('.shop-product').first.wait_for()
 assert page.locator('#shop-category-title').inner_text()=='건축블럭'
 page.evaluate("saleCategories=['minerals','crops']")
 page.locator('[data-shop-refresh]').click();page.wait_for_timeout(200)
 assert building.is_disabled() and page.locator('#shop-category-title').inner_text()=='광물'
 # Public pause banner and label, updated by server status poll.
 page.evaluate('buyPaused=true;sellPaused=true');page.wait_for_timeout(5200);assert '구매 일시정지' in page.locator('.shop-maintenance').inner_text();assert '판매 일시정지' in page.locator('.shop-maintenance').inner_text();assert page.locator('[data-shop-item]').first.is_disabled();assert '판매 중지' in page.locator('[data-shop-item]').first.inner_text()
 for theme in ['dark','light']:
  page.evaluate('(t)=>PocketmateTheme.set(t)',theme);page.wait_for_timeout(100);page.screenshot(path=str(r/f'verification/shop-continuous-pause-{theme}-mock.png'))
 page.evaluate('buyPaused=false;sellPaused=false;shopBalance=50000;shopCapacity=0');page.locator('[data-shop-mode=buy]').click();page.wait_for_timeout(150);page.locator('[data-shop-item]').first.click();page.wait_for_timeout(120);assert page.locator('[data-shop-max]').is_disabled();assert page.locator('[data-shop-confirm]').is_disabled();page.locator('[data-shop-cancel]').click()
 page.evaluate('shopCapacity=100');page.locator('[data-shop-item]').first.click();page.locator('[data-shop-max]').click();page.evaluate('shopVersion="fixture2"');page.locator('[data-shop-confirm]').click();page.wait_for_timeout(150);assert '갱신' in page.locator('.pm-notification').inner_text();assert page.evaluate('shopBalance')==50000
 page.locator('[data-shop-category=building]').click();page.wait_for_timeout(150);page.locator('.shop-search input').fill('상품 74');page.wait_for_timeout(450);assert page.locator('.shop-product').count()==1,(page.locator('.shop-product').count(),page.evaluate('shopCalls.slice(-6)'),page.locator('.pm-notification').inner_text())
 page.locator('.shop-search input').fill('');page.wait_for_timeout(450)
 # Closing a pending quote must never resurrect a dialog.
 page.evaluate('quoteDelay=300');page.locator('[data-shop-item]').first.click();page.locator('[data-shop-cancel]').click();page.wait_for_timeout(400);assert page.locator('.shop-trade-dialog').count()==0
 for w,h in [(1440,900),(1280,720),(854,480),(640,360)]:
  page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(100);assert page.locator('#shop-page').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
 page.set_viewport_size({'width':1440,'height':900});page.locator('#shop-page [data-go=home]').click();count=page.evaluate('shopCalls.length');page.clock.install();page.clock.fast_forward(20000);assert page.evaluate('shopCalls.length')==count
 assert all('balance' not in c and 'total' not in c and 'unitPrice' not in c for c in page.evaluate('shopCalls'));assert not errors,errors
 browser.close()
(r/'verification/shop-continuous-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'gpu_icons_tested':False,'continuous_75_unique_items':True,'older_batch_icons':True,'max_capacity_and_affordability':True,'max_sell_all':True,'public_pause_notice':True,'zero_capacity_disables_trade':True,'price_change_rejected':True,'late_quote_ignored_after_close':True,'search_resets_list':True,'four_viewports':True,'unmount_stops_poll':True,'errors':errors},indent=2)+'\n',encoding='utf-8')
print('Continuous shop mock checks passed')
