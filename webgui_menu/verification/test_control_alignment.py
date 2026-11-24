"""Mock-only audit of shared button icon placement and header insets."""
from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parents[1]
a=(r/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=a.split('mock=r"""',1)[1].split('"""',1)[0]
b=(r/'verification/test_daily_missions_ui.py').read_text(encoding='utf-8');mock+=b.split("mock+=r'''",1)[1].split("'''",1)[0]
e=(r/'verification/test_estate_community.py').read_text(encoding='utf-8');estate=e.split('mock=r"""',1)[1].split('"""',1)[0]
audit=r'''()=>[...document.querySelectorAll('button>svg')].flatMap(svg=>{const b=svg.parentElement,r=svg.getBoundingClientRect(),p=b.getBoundingClientRect(),s=getComputedStyle(b);if(r.width===0||r.height===0||p.bottom<0||p.top>innerHeight||s.flexDirection==='column'||!['flex','inline-flex','grid'].includes(s.display))return [];return [{label:b.getAttribute('aria-label')||b.textContent.trim(),centerError:Math.abs((r.y+r.height/2)-(p.y+p.height/2)),inside:r.x>=p.x&&r.right<=p.right&&r.y>=p.y&&r.bottom<=p.bottom}];})'''
cases=0;buttons=0;errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page();page.add_init_script(mock);page.on('pageerror',lambda e:errors.append(str(e)))
 for theme in ['dark','light']:
  for w,h in [(1440,900),(1280,720),(854,480)]:
   for scale in [1,1.4,1.6]:
    if w==854 and scale>1:continue
    page.set_viewport_size({'width':w,'height':h});page.goto((r/'index.html').as_uri());page.wait_for_timeout(350);page.evaluate('([t,s])=>{PocketmateTheme.set(t);document.documentElement.style.setProperty("--text-scale",s)}',[theme,str(scale)])
    for route in ['home','quests','settings','shop','profile']:
     page.evaluate('(v)=>document.querySelector(`[data-page="${v}"]`)?.click()',route) if route!='profile' else page.get_by_role('button',name='프로필카드 편집').click()
     page.wait_for_timeout(80)
     result=page.evaluate(audit);buttons+=len(result);assert all(x['inside'] and x['centerError']<=1.1 for x in result),(w,h,scale,route,result)
     if route=='home':
      pad=page.locator('#close-menu').evaluate('e=>{const s=getComputedStyle(e);return [s.paddingLeft,s.paddingRight]}');assert pad[0]==pad[1]
      if w==1440 and scale==1.4:
       page.screenshot(path=str(r/f'verification/control-alignment-home-{theme}.png'))
       page.locator('#close-menu').screenshot(path=str(r/f'verification/control-alignment-close-{theme}.png'))
     cases+=1
 ep=browser.new_page(viewport={'width':1440,'height':900});ep.add_init_script(estate);ep.on('pageerror',lambda e:errors.append(str(e)))
 for theme in ['dark','light']:
  ep.goto((r/'index.html').as_uri());ep.evaluate('(t)=>PocketmateTheme.set(t)',theme);ep.locator('[data-page=estate]').click();ep.locator('.estate-plaza').wait_for()
  result=ep.evaluate(audit);buttons+=len(result);assert all(x['inside'] and x['centerError']<=1.1 for x in result),result
  ep.locator('.estate-nav [data-estate-tab=members]').click();ep.locator('[data-estate-invite]').click();ep.locator('#estate-player-search').wait_for();ep.screenshot(path=str(r/f'verification/control-alignment-estate-dialog-{theme}.png'));ep.locator('[data-cancel]').click();cases+=1
 assert not errors,errors
 browser.close()
(r/'verification/control-alignment-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'page_viewport_scale_cases':cases,'icon_buttons_checked':buttons,'icon_inside_and_centered':True,'symmetric_close_padding':True,'themes':2,'scales':[1,1.4,1.6],'errors':errors},indent=2),encoding='utf-8')
print('Control alignment audit passed:',cases,'cases,',buttons,'icon buttons')
