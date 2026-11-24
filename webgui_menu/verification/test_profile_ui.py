"""Profile collection UI + server acknowledgement contract, with no live grants."""
from pathlib import Path
import os,sys,json,re
sys.path.insert(0,str(Path(os.environ['LOCALAPPDATA'])/'PocketmateMenuTools'))
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
mock=r"""
window.profileCalls=[];window.rejectEquip=false;window.profileSaved={icon:'skin',title:'beginner',banner:'none',owned:['icon:skin','icon:bulbasaur','icon:charmander','icon:squirtle','title:none','title:beginner','banner:none','banner:forest','banner:night']};
window.profileCatalog=[['icon','skin','내 스킨 얼굴',''],['icon','bulbasaur','이상해씨','bulbasaur.png'],['icon','charmander','파이리','charmander.png'],['icon','squirtle','꼬부기','squirtle.png'],['icon','pikachu','피카츄','pikachu.png'],['title','none','칭호 없음',''],['title','beginner','새로운 모험가',''],['banner','none','기본 카드',''],['banner','forest','초록빛 숲길','forest.svg'],['banner','night','별빛 야영','night.svg']].map(([kind,id,name,image])=>({kind,id,name,image:image?'./profile-assets/'+image:'',starter:id!=='pikachu'}));
window.webgui={client:{username:'TestPlayer',gamemode:'creative',health:20,maxHealth:20,xpLevel:7,dimension:'minecraft:overworld',pos:{x:8,y:66,z:8}},postToGame(p){
 if(p.channel!=='pocketmate:profile')return;profileCalls.push(p);
 setTimeout(()=>{let response;
 if(p.action==='equip'&&rejectEquip)response={type:'error',requestId:p.requestId,message:'보유한 항목만 착용할 수 있습니다.'};
 else{if(p.action==='equip')Object.assign(profileSaved,{icon:p.icon,title:p.title,banner:p.banner});response={type:'snapshot',requestId:p.requestId,playerId:'test-id',playerName:'TestPlayer',profile:structuredClone(profileSaved),catalog:profileCatalog,...(p.action==='equip'?{message:'프로필카드를 저장했습니다.'}:{})};}
 dispatchEvent(new CustomEvent('webgui:pocketmate:profile',{detail:response}));
 },300);
}};
"""
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1920,'height':1080})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script(mock);page.goto((root/'index.html').as_uri());page.wait_for_timeout(400)
    assert page.locator('#profile-title').inner_text()=='새로운 모험가'
    page.get_by_role('button',name='프로필카드 편집').click();page.wait_for_timeout(400)
    assert page.locator('[data-profile-item]').count()==4
    assert page.locator('[data-profile-item="pikachu"]').count()==0
    assert page.locator('[data-profile-save]').is_disabled()
    page.locator('[data-profile-item="bulbasaur"]').click()
    assert page.locator('.profile-preview-avatar img').get_attribute('src').endswith('bulbasaur.png')
    assert page.locator('#profile-avatar img').count()==0  # Preview only until server acknowledgement.
    page.locator('[data-profile-tab="banner"]').click();page.locator('[data-profile-item="forest"]').click()
    page.locator('[data-profile-tab="title"]').click();page.locator('[data-profile-item="none"]').click()
    assert page.locator('#profile-title').is_visible()
    page.locator('[data-profile-save]').click();assert page.locator('[data-profile-save]').is_disabled();page.wait_for_timeout(400)
    assert page.locator('#profile-title').is_hidden()
    assert page.locator('#profile-avatar img').get_attribute('src').endswith('bulbasaur.png')
    assert 'forest.svg' in page.locator('#profile-card').get_attribute('style')
    assert page.evaluate('profileCalls.filter(p=>p.action==="equip").length')==1
    # Reopening reads authoritative equipment instead of local browser-owned cosmetics.
    page.locator('[data-go="home"]').first.click();page.get_by_role('button',name='프로필카드 편집').click();page.wait_for_timeout(400)
    assert page.locator('[data-profile-item="bulbasaur"]').get_attribute('aria-pressed')=='true'
    page.locator('[data-profile-item="charmander"]').click();page.locator('[data-profile-reset]').click()
    assert page.locator('[data-profile-item="bulbasaur"]').get_attribute('aria-pressed')=='true'
    page.evaluate('rejectEquip=true');page.locator('[data-profile-item="squirtle"]').click();page.locator('[data-profile-save]').click();page.wait_for_timeout(350)
    assert page.locator('#profile-avatar img').get_attribute('src').endswith('bulbasaur.png')
    page.wait_for_timeout(850);assert page.locator('[data-profile-item="bulbasaur"]').get_attribute('aria-pressed')=='true'
    page.evaluate('rejectEquip=false')
    reports=[]
    for width,height in [(1920,1080),(1280,720),(854,480),(640,360)]:
        page.set_viewport_size({'width':width,'height':height});page.evaluate("document.documentElement.style.setProperty('--text-scale','1.6')");page.wait_for_timeout(100)
        assert page.evaluate('document.documentElement.scrollWidth')<=width
        page.locator('[data-profile-tab="banner"]').click()
        page.locator('[data-profile-item="night"]').click();page.wait_for_timeout(320)
        metrics=page.evaluate('''(() => {let p=document.querySelector('#page-scroll'),c=document.querySelector('.profile-studio');return {scrollWidth:p.scrollWidth,clientWidth:p.clientWidth,studioWidth:c.getBoundingClientRect().width}})()''')
        assert metrics['scrollWidth']<=metrics['clientWidth']+1,metrics
        page.locator('[data-profile-save]').scroll_into_view_if_needed();assert page.locator('[data-profile-save]').is_visible()
        reports.append({'width':width,'height':height,**metrics})
    page.set_viewport_size({'width':1920,'height':1080});page.evaluate("document.documentElement.style.setProperty('--text-scale','1.3')");page.locator('#page-scroll').evaluate('e=>e.scrollTop=0');page.screenshot(path=str(root/'verification/profile-studio-docked.png'))
    assert not errors,errors
    (root/'verification/profile-browser-layout-report.json').write_text(json.dumps({'passed':True,'checks':['title adjacent to CONNECTED PLAYER','only owned collection choices','draft preview does not alter equipped card','server acknowledgement applies icon/title/banner together','equipment retained after reopen','reset draft','rejected equipment does not change live card','4 responsive viewports at 160% text; save reachable'],'viewports':reports},ensure_ascii=False,indent=2),encoding='utf-8')
    browser.close()
print('Profile browser checks passed')
