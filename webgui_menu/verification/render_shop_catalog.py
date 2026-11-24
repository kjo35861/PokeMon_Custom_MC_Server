"""Render the real registry catalog with synthetic inventory/wallet; no game connection."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parents[1]
src=(r/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=src.split('mock=r"""',1)[1].split('"""',1)[0]
catalog=json.loads((r/'verification/shop-registry-catalog-report.json').read_text(encoding='utf-8'))['items']
mock+='\nwindow.previewCatalog='+json.dumps(catalog,ensure_ascii=False)+';\n'+r'''
webgui.postToGame=function(p){if(p.channel!=='pocketmate:shop')return;setTimeout(()=>{
const all=previewCatalog.filter(i=>(p.mode==='buy'?i.buy:i.sell)&&(p.mode==='buy'?i.category:i.category==='minerals'?'minerals':'crops')===p.category&&(!p.query||i.name.includes(p.query)||i.id.includes(p.query)));
const items=all.slice(p.page*24,(p.page+1)*24).map(i=>({id:i.id,name:i.name,buy:i.buyPrice,sell:i.sellPrice,owned:p.mode==='sell'?12:0}));
dispatchEvent(new CustomEvent('webgui:pocketmate:shop',{detail:{type:'snapshot',requestId:p.requestId,mode:p.mode,category:p.category,page:p.page,total:all.length,pages:Math.max(1,Math.ceil(all.length/24)),balance:10000,priceVersion:'preview',nextPriceAt:0,randomPrices:false,items}}));},30);};
'''
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True);page=browser.new_page(viewport={'width':1440,'height':900});page.add_init_script(mock);page.goto((r/'index.html').as_uri());page.wait_for_timeout(350);page.locator('[data-page=shop]').click();page.locator('.shop-product').first.wait_for();assert page.locator('.shop-product').count()==24
 first=page.locator('[data-shop-item]').first.get_attribute('data-shop-item');page.locator('.shop-main').evaluate('(e)=>e.scrollTop=e.scrollHeight');page.wait_for_timeout(250);assert page.locator('.shop-product').count()>24;assert page.locator('[data-shop-item]').first.get_attribute('data-shop-item')==first
 page.locator('[data-shop-category=building]').click();page.wait_for_timeout(100)
 for mode in ['buy','sell']:
  page.locator('[data-shop-mode='+mode+']').click();page.wait_for_timeout(120)
  for theme in ['dark','light']:
   page.evaluate('(t)=>PocketmateTheme.set(t)',theme);page.wait_for_timeout(250);page.locator('.shop-main').evaluate('(e)=>e.scrollTop=0');page.screenshot(path=str(r/f'verification/shop-continuous-catalog-{mode}-{theme}-mock.png'))
 browser.close()
(r/'verification/shop-continuous-catalog-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'actual_registry_catalog_rows':len(catalog),'page_size':24,'scroll_appends_items':True,'themes':2,'modes':2,'sample_inventory_and_balance':True,'game_texture_preview':False},indent=2),encoding='utf-8')
print('Full catalog continuous mock passed')
