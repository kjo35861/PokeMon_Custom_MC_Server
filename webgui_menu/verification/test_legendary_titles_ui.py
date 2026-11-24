"""Headless isolated UI check; never changes game ownership."""
from pathlib import Path
import os,sys,json,base64
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
source=(root/'verification/test_profile_ui.py').read_text(encoding='utf-8')
mock=source.split('mock=r"""',1)[1].split('"""',1)[0]
rows=json.loads((root.parent/'docs/design/legendary-titles/night-sky-v10/preview-data.json').read_text(encoding='utf-8'))
items=[dict(kind='title',id='legendary_'+r['dex'],name=r['title'],image='./profile-assets/title-'+r['dex']+'.png',color='#'+r['color'],lightColor='#'+r['lightColor'],starter=False,acquisitionCondition='서버에서 '+r['name']+' 최초 포획') for r in rows]
mock+='\nprofileCatalog.push(...'+json.dumps(items,ensure_ascii=False)+');profileSaved.owned.push(...profileCatalog.filter(c=>c.id.startsWith("legendary_")).map(c=>"title:"+c.id));'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page(viewport={'width':1280,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script(mock);page.goto((root/'index.html').as_uri());page.wait_for_timeout(450)
 page.get_by_role('button',name='프로필카드 편집').click();page.wait_for_timeout(450);page.locator('[data-profile-tab="title"]').click()
 assert page.locator('[data-profile-item^="legendary_"]').count()==94
 for theme in ['dark','light']:
  page.evaluate('(t)=>document.documentElement.dataset.theme=t',theme)
  for item in items:
   tile=page.locator('[data-profile-item="'+item['id']+'"]');tile.click()
   assert page.locator('.profile-preview .profile-title').inner_text()==item['name']
   assert tile.locator('.profile-acquisition').inner_text()=='획득 조건\n'+item['acquisitionCondition']
   assert page.locator('.profile-preview .title-reward-dark').evaluate('(e)=>e.complete&&e.naturalWidth===48')
   selected=tile.locator('.title-reward-'+theme)
   assert selected.is_visible()
   assert selected.evaluate('(e)=>e.complete&&e.naturalWidth===48')
 page.locator('[data-profile-save]').click();page.wait_for_timeout(450)
 assert page.locator('#profile-title').inner_text()==items[-1]['name']
 assert not errors,errors
 browser.close()
(root/'verification/legendary-title-ui-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'species':94,'theme_selection_cases':188,'images_loaded':True,'acquisition_conditions_checked':188,'server_ack_mock_updates_card':True,'errors':errors},indent=2)+'\n',encoding='utf-8')
print('188 mock UI selections and PNG loads passed; saved card updated after mock acknowledgement. Game untested.')
