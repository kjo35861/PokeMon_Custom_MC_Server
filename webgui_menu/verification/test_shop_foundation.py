from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
s=(root/'verification/test_estate_community.py').read_text(encoding='utf-8');mock=s.split('mock=r"""',1)[1].split('"""',1)[0]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':900});page.add_init_script(mock);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto((root/'index.html').as_uri());page.locator('.shop-entry-tile').click()
 assert page.locator('#shop-page').is_visible()
 assert page.locator('#shop-page').evaluate('(e)=>getComputedStyle(e).position')=='fixed'
 page.locator('[data-shop-category="pokemon"]').click();assert page.locator('#shop-category-title').inner_text()=='포켓몬 용품'
 page.locator('.shop-search input').fill('<script>');assert page.locator('.shop-empty h3').inner_text()=='검색된 상품이 없습니다'
 page.locator('.shop-search input').fill('')
 page.locator('[data-shop-category="all"]').click()
 for theme in ['dark','light']:
  page.evaluate('(t)=>document.documentElement.dataset.theme=t',theme)
  page.screenshot(path=str(root/f'verification/shop-foundation-{theme}.png'))
 for width,height in [(1920,1080),(1280,720),(854,480),(640,360)]:
  page.set_viewport_size({'width':width,'height':height});assert page.locator('#shop-page').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
 page.set_viewport_size({'width':1440,'height':900});page.locator('#shop-page [data-go="home"]').click();page.locator('[data-go="warehouse"]').click();assert page.locator('#feature-title').inner_text()=='창고'
 page.locator('[data-page="estate"]').click();page.locator('.estate-plaza').wait_for();assert page.locator('[data-estate-image-delete]').count()==0
 page.evaluate("imageValue='data:image/jpeg;base64,/9j/';")
 page.locator('[data-estate-refresh]').click();page.locator('[data-estate-image-delete]').wait_for();page.locator('[data-estate-image-delete]').click();page.locator('[data-cancel]').click();assert page.evaluate("requests.filter(r=>r.action==='image').length")==0
 page.locator('[data-estate-image-delete]').click();page.locator('[data-confirm]').click();page.wait_for_timeout(150)
 assert page.evaluate("requests.filter(r=>r.action==='image').length")==1
 assert page.evaluate('imageValue')=='' and page.locator('.estate-cover').count()==0
 page.evaluate("viewerLord=false;imageValue='data:image/jpeg;base64,/9j/';")
 page.locator('[data-estate-refresh]').click();page.wait_for_timeout(150);assert page.locator('[data-estate-image-delete]').count()==0
 assert not errors,errors
 browser.close()
(root/'verification/shop-foundation-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'shop_fullscreen':True,'categories_and_search':True,'themes':2,'viewport_sizes':4,'warehouse_route':True,'image_delete_cancel_and_confirm':True,'non_lord_hidden':True,'errors':errors},indent=2),encoding='utf-8')
print('Shop foundation and image removal mock checks passed')
