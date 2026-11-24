from pathlib import Path
import os,sys,json
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
a=(root/'verification/test_profile_ui.py').read_text(encoding='utf-8');mock=a.split('mock=r"""',1)[1].split('"""',1)[0]
b=(root/'verification/test_daily_missions_ui.py').read_text(encoding='utf-8');mock+=b.split("mock+=r'''",1)[1].split("'''",1)[0]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
 page=browser.new_page();page.add_init_script(mock)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 for width,height,scale in [(1920,1080,1),(1920,1080,1.6),(1440,900,1),(1440,900,1.6),(1366,768,1),(1366,768,1.6),(1280,720,1),(1280,720,1.6),(854,480,1)]:
  page.set_viewport_size({'width':width,'height':height});page.goto((root/'index.html').as_uri());page.wait_for_timeout(450)
  page.evaluate("""missionState.tasks.forEach((t,i)=>Object.assign(t,[
   {name:'돌을 캐는 하루',description:'돌·심층암·화강암·섬록암·안산암 64개 채굴하기'},
   {name:'종족 연구',description:'서로 다른 종류의 야생 포켓몬 4종 처치하기'},
   {name:'다양한 만남',description:'서로 다른 종류의 야생 포켓몬 2종 포획하기'},
   {name:'풍요로운 수확',description:'완전히 자란 작물 24칸 수확하기'},
   {name:'세계의 방랑자',description:'도보·수영·탑승으로 총 1,200블록 이동하기'}][i]))""")
  page.locator('[data-page="quests"]').click();page.wait_for_timeout(150)
  page.evaluate('(s)=>document.documentElement.style.setProperty("--text-scale",s)',str(scale));page.wait_for_timeout(80)
  result=page.evaluate('''()=>{
   const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,bottom:r.bottom,right:r.right}};
   const area=document.querySelector('#page-scroll').getBoundingClientRect();
   return {dock:rect(document.querySelector('#profile-card')),shell:rect(document.querySelector('.shell')),area:rect(document.querySelector('#page-scroll')),cards:[...document.querySelectorAll('.mission-card')].map(e=>({box:rect(e),copy:rect(e.querySelector('.mission-copy')),buttons:rect(e.querySelector('.mission-actions')),overflow:e.scrollHeight-e.clientHeight})),final:rect(document.querySelector('.mission-final')),overflow:document.querySelector('#page-scroll').scrollHeight-document.querySelector('#page-scroll').clientHeight};
  }''')
  assert result['dock']['bottom']<result['shell']['y']
  assert abs(result['dock']['x']+result['dock']['w']/2-width/2)<1
  assert result['overflow']<=1,(width,height,scale,result)
  for card in result['cards']:
   assert card['box']['y']>=result['area']['y'] and card['box']['bottom']<=result['area']['bottom']+1
   assert card['overflow']<=1,(width,height,scale,card)
   assert card['copy']['bottom']<=card['box']['bottom']+1 and card['buttons']['bottom']<=card['box']['bottom']+1
  assert result['final']['bottom']<=result['area']['bottom']+1
  assert max(c['box']['y'] for c in result['cards'])-min(c['box']['y'] for c in result['cards'])<1
  assert result['final']['y']>=max(c['box']['bottom'] for c in result['cards'])
  print(width,height,scale,'five cards + final visible; profile outside; no overflow')
  if width==1920 and scale==1:page.screenshot(path=str(root/'verification/docked-profile-missions-dark.png'))
 # The same profile node stays visible on every destination, including the estate overlay.
 page.set_viewport_size({'width':1920,'height':1080});page.goto((root/'index.html').as_uri());page.wait_for_timeout(450)
 for route in ['home','shop','quests','settings','estate']:
  page.locator('[data-page="'+route+'"]').click();page.wait_for_timeout(100)
  assert page.locator('#profile-card').is_visible()
  assert page.locator('#profile-card').evaluate('(e)=>e.parentElement===document.body')
  if route=='estate':
   dock=page.locator('#profile-card').bounding_box();window=page.locator('.estate-window').bounding_box();assert dock['y']+dock['height']<window['y']
 page.get_by_role('button',name='프로필카드 편집').click();page.wait_for_timeout(400)
 assert page.locator('#estate-page').is_hidden() and page.locator('.profile-studio').is_visible()
 assert page.locator('#profile-card').is_visible()
 page.locator('[data-page="quests"]').click();page.wait_for_timeout(150)
 page.evaluate('document.documentElement.dataset.theme="light"');page.screenshot(path=str(root/'verification/docked-profile-missions-light.png'))
 assert not errors,errors
 browser.close()
(root/'verification/menu-layout-report.json').write_text(json.dumps({'headless_mock_only':True,'game_tested':False,'viewport_scale_cases':9,'long_mission_descriptions_checked':True,'five_missions_and_final_visible':True,'five_portrait_cards_in_one_row':True,'full_width_final_below_all_missions':True,'profile_single_body_node':True,'all_destinations_and_estate':True,'profile_edit_from_estate':True,'no_overflow':True,'errors':errors},indent=2)+'\n',encoding='utf-8')
