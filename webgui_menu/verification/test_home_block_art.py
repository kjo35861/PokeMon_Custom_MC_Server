from pathlib import Path
import os,sys,json
from PIL import Image
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
alpha={}
for file in (root/'home-assets').glob('*.webp'):
 im=Image.open(file);assert im.mode=='RGBA' and im.getchannel('A').getextrema()==(0,255);alpha[file.name]=True
 assert file.stat().st_size<300_000
assert sum(p.stat().st_size for p in (root/'home-assets').glob('*.webp'))<1_000_000
s=(root/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=s.split('mock=r"""',1)[1].split('"""',1)[0]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page();page.add_init_script(mock);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 for w,h in [(1920,1080),(1440,900),(1280,720),(854,480)]:
  page.set_viewport_size({'width':w,'height':h});page.goto((root/'index.html').as_uri());page.wait_for_timeout(400)
  for theme in ['dark','light']:
   page.evaluate('(t)=>document.documentElement.dataset.theme=t',theme);page.wait_for_timeout(300)
   assert page.locator('#home-page .home-tile-image').count()==5
   assert page.locator('#home-page .home-tile-image').evaluate_all('(es)=>es.every(e=>e.complete&&e.naturalWidth>0)')
   assert page.locator('#page-scroll').evaluate('(e)=>e.scrollHeight-e.clientHeight')<=1
   checks=page.locator('#home-page .home-tile-image').evaluate_all('''es=>es.map(e=>{const a=e.getBoundingClientRect(),b=e.closest('button').getBoundingClientRect(),c=e.closest('button').querySelector('.tile-copy,.team-copy').getBoundingClientRect();return {inside:a.left>=b.left&&a.right<=b.right&&a.top>=b.top&&a.bottom<=b.bottom,copyClear:a.right<=c.left||a.left>=c.right||a.bottom<=c.top||a.top>=c.bottom}})''')
   assert all(c['inside'] and c['copyClear'] for c in checks),(w,h,theme,checks)
   if w==1440:page.screenshot(path=str(root/f'verification/home-block-art-optimized-{theme}.png'))
 assert not errors,errors
 page.locator('.shop-entry-tile').click();assert page.locator('#shop-page').is_visible()
 browser.close()
(root/'verification/home-block-art-optimized-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'transparent_assets':alpha,'export_size':512,'five_assets_total_under_1MB':True,'viewport_sizes':4,'themes':2,'image_load_and_copy_clear':True,'home_no_scroll':True,'shop_navigation':True,'errors':errors},indent=2),encoding='utf-8')
print('Home artwork checks passed')
