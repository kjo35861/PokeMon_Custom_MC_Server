"""Mock favorites navigation and reviewed bulk request."""
from pathlib import Path
import os, sys
sys.path.insert(0, str(Path(os.environ["LOCALAPPDATA"])/"PocketmateMenuTools"))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
mock=(root/"verification/test_profile_ui.py").read_text(encoding="utf8").split('mock=r"""',1)[1].split('"""',1)[0]
mock+=r"""
let favorites=['minecraft:stone'];
window.lastBulk=null;
const original=webgui.postToGame;
webgui.postToGame=p=>{
 if(p.channel!=='pocketmate:shop')return original.call(webgui,p);
 if(p.action==='favorite')favorites=favorites.includes(p.item)?[]:[p.item];
 if(p.action==='bulk')window.lastBulk=p;
 const items=p.category==='favorites'&&!favorites.length?[]:[{id:'minecraft:stone',name:'Stone',buy:100,sell:50,owned:8}];
 setTimeout(()=>dispatchEvent(new CustomEvent('webgui:pocketmate:shop',{detail:{type:'snapshot',requestId:p.requestId,category:p.category,mode:p.mode,page:0,pages:1,items,total:items.length,favorites,balance:1000,priceVersion:'test'}})),30);
};
"""
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",headless=True)
 page=browser.new_page(viewport={"width":1440,"height":900})
 page.add_init_script(mock)
 page.goto((root/"index.html").as_uri())
 page.locator("[data-page=shop]").click()
 page.locator('[data-shop-category=favorites][aria-pressed=true]').wait_for()
 page.locator('[data-shop-star][aria-pressed=true]').wait_for()
 page.locator('[data-shop-bulk]').click()
 assert page.evaluate('lastBulk') is None
 page.locator('.shop-trade-dialog [data-confirm]').click()
 page.wait_for_function('lastBulk !== null')
 assert page.evaluate('lastBulk.reviewed')=='minecraft:stone=1'
 page.locator('[data-shop-mode=sell]').click()
 page.locator('[data-shop-bulk]').click()
 page.locator('.shop-trade-dialog [data-confirm]').click()
 page.wait_for_function("lastBulk.mode === 'sell'")
 assert page.evaluate('lastBulk.reviewed')=='minecraft:stone=8'
 page.locator('[data-shop-star]').click()
 page.locator('.shop-empty').wait_for()
 browser.close()
print("Favorites UI checks passed")
