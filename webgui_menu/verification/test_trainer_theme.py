"""Mock-only visual and layout checks for the shared trainer theme."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parents[1]
a=(r/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=a.split('mock=r"""',1)[1].split('"""',1)[0]
b=(r/'verification/test_daily_missions_ui.py').read_text(encoding='utf-8');mock+=b.split("mock+=r'''",1)[1].split("'''",1)[0]
e=(r/'verification/test_estate_community.py').read_text(encoding='utf-8');estate=e.split('mock=r"""',1)[1].split('"""',1)[0]
estate=estate.replace('freeTestMode:true,','freeTestMode:true,estateLevel:0,chunkLimit:1,memberLimit:5,purchasedChunks:1,treasury:0,lordBalance:0,levels:[{level:0,cost:0,limit:1,members:5},{level:1,cost:0,limit:4,members:5}],')
errors=[];cases=0
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1440,'height':900});page.add_init_script(mock);page.on('pageerror',lambda e:errors.append(str(e)))
 for theme in ['dark','light']:
  page.goto((r/'index.html').as_uri());page.wait_for_timeout(400);page.evaluate('(t)=>PocketmateTheme.set(t)',theme);page.wait_for_timeout(300)
  expected=page.locator('.shell').evaluate('(e)=>getComputedStyle(e).backgroundColor')
  for route in ['home','shop','quests','profile','settings','warehouse','warp']:
   if route in ['profile','warehouse','warp']:page.evaluate('(route)=>document.querySelector(`[data-go="${route}"]`).click()',route)
   else:page.locator('[data-page="'+route+'"]').click()
   page.wait_for_timeout(400)
   assert page.locator('#profile-card').is_visible()
   if route=='shop':assert page.locator('#shop-page').evaluate('(e)=>getComputedStyle(e).backgroundColor')==expected
   if route in ['home','shop','quests','profile']:page.screenshot(path=str(r/f'verification/trainer-theme-{route}-{theme}.png'))
   if route=='quests':assert page.locator('.mission-card').count()==5 and page.locator('[data-mission-claim-all]').is_visible()
   # Return to home so home-only routes are interactable for the next iteration.
   page.evaluate('document.querySelector("[data-page=home]").click()');page.wait_for_timeout(60)
   cases+=1
  for w,h,scale in [(1920,1080,1.6),(1280,720,1),(1280,720,1.6),(854,480,1)]:
   page.set_viewport_size({'width':w,'height':h});page.evaluate('(s)=>document.documentElement.style.setProperty("--text-scale",s)',str(scale));page.wait_for_timeout(60)
   assert page.locator('#page-scroll').evaluate('(e)=>e.scrollHeight-e.clientHeight')<=1
   page.locator('[data-page=quests]').click();page.wait_for_timeout(80)
   assert page.locator('#page-scroll').evaluate('(e)=>e.scrollHeight-e.clientHeight')<=1
   page.locator('[data-page=home]').click();cases+=1
  page.set_viewport_size({'width':1440,'height':900});page.evaluate('document.documentElement.style.setProperty("--text-scale","1")')
 ep=browser.new_page(viewport={'width':1440,'height':900});ep.add_init_script(estate);ep.on('pageerror',lambda e:errors.append(str(e)))
 for theme in ['dark','light']:
  ep.goto((r/'index.html').as_uri());ep.evaluate('(t)=>PocketmateTheme.set(t)',theme);ep.locator('[data-page=estate]').click();ep.locator('.estate-plaza').wait_for();ep.wait_for_timeout(300)
  assert ep.locator('.estate-window').evaluate('(e)=>getComputedStyle(e).backgroundColor')==ep.locator('.shell').evaluate('(e)=>getComputedStyle(e).backgroundColor')
  ep.screenshot(path=str(r/f'verification/trainer-theme-estate-{theme}.png'))
  ep.locator('.estate-nav [data-estate-tab=members]').click();assert ep.locator('[data-estate-invite]').is_visible();ep.locator('[data-estate-invite]').click();ep.locator('#estate-player-search').wait_for();ep.locator('[data-cancel]').click();cases+=1
  for tab in ['vault','settings','manage','options']:
   ep.locator(f'.estate-nav [data-estate-tab={tab}]').click();ep.wait_for_timeout(120);assert ep.locator('#estate-content').is_visible();cases+=1
   if tab=='vault':ep.screenshot(path=str(r/f'verification/trainer-theme-vault-{theme}.png'))
 assert not errors,errors
 browser.close()
(r/'verification/trainer-theme-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'themes':2,'route_and_viewport_cases':cases,'shared_surface':True,'profile_dock_preserved':True,'mission_cards_and_claim_all':True,'estate_members_and_dialog':True,'errors':errors},indent=2),encoding='utf-8')
print('Trainer theme checks passed:',cases,'cases')
