(() => {
  'use strict';
  const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let snapshot=null,draft=null,client=null,host=null,tab='icon',pending=null,feedback='',error=false,skin=null,identity='';
  const actionSlot=$('profile-actions-slot');
  const actionControl=selector=>actionSlot?.querySelector(selector)||host?.querySelector(selector);
  let actionsVisible=false,actionsAnimation=null;
  function showActions(visible){
    if(!actionSlot)return;
    const changed=visible!==actionsVisible;
    actionsVisible=visible;
    actionSlot.hidden=false;
    actionSlot.inert=!visible;
    actionSlot.setAttribute('aria-hidden',String(!visible));
    actionSlot.parentElement?.style.setProperty('--profile-actions-clearance',visible?'84px':'12px');
    if(!changed)return;
    actionsAnimation?.cancel();actionsAnimation=null;
    const shell=actionSlot.querySelector('.profile-actions-shell');
    const reduced=document.body.classList.contains('reduce-motion')||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if(visible){
      actionSlot.classList.add('is-open');
      if(shell?.animate&&!reduced)actionsAnimation=shell.animate([{opacity:0,transform:'translateY(22px)'},{opacity:1,transform:'translateY(0)'}],{duration:300,easing:'cubic-bezier(.22,1,.36,1)',fill:'both'});
    }else if(shell?.animate&&!reduced){
      const animation=shell.animate([{opacity:1,transform:'translateY(0)'},{opacity:0,transform:'translateY(14px)'}],{duration:160,easing:'ease-in',fill:'both'});
      actionsAnimation=animation;
      animation.onfinish=()=>{if(!actionsVisible)actionSlot.classList.remove('is-open');};
    }else actionSlot.classList.remove('is-open');
  }
  function clearActions(){
    actionsAnimation?.cancel();actionsAnimation=null;actionsVisible=false;
    if(actionSlot){actionSlot.replaceChildren();actionSlot.classList.remove('is-open');actionSlot.hidden=true;actionSlot.inert=true;actionSlot.setAttribute('aria-hidden','true');actionSlot.parentElement?.style.removeProperty('--profile-actions-clearance');}
  }
  const labels={icon:'프로필아이콘',title:'칭호',banner:'플레이어 배너'};
  const descriptions={icon:'포켓몬 이미지 또는 내 플레이어 스킨 얼굴을 골라보세요.',title:'CONNECTED PLAYER 옆에 표시할 칭호를 선택하세요.',banner:'프로필카드의 배경에 착용할 보유 배너를 선택하세요.'};
  const imagePath=value=>typeof value==='string'&&/^\.\/profile-assets\/[a-z0-9-]+\.(png|svg)$/.test(value)?value:'';
  const item=(kind,id)=>snapshot?.catalog.find(c=>c.kind===kind&&c.id===id);
  const equipped=()=>snapshot?.profile;
  const dirty=()=>draft&&equipped()&&['icon','title','banner'].some(k=>draft[k]!==equipped()[k]);
  function banner(element,id){const path=imagePath(item('banner',id)?.image);element.style.setProperty('--profile-banner',path?`url("${path}")`:'none');}
  function avatar(element,id){
    if(!element)return;element.replaceChildren();
    const path=id==='skin'?(window.PocketmatePeople?.skin(snapshot?.playerId)||(skin?.playerId===snapshot?.playerId?skin.image:'')):imagePath(item('icon',id)?.image);
    if(path){const img=new Image();img.src=path;img.alt=id==='skin'?'내 플레이어 스킨 얼굴':item('icon',id)?.name||'포켓몬';if(id==='skin')img.className='skin-face';img.onerror=()=>{img.remove();initial(element);};element.append(img);}
    else initial(element);
  }
  function initial(element){const span=document.createElement('span');span.className='avatar-initial';span.textContent=(snapshot?.playerName||client?.username||'P').slice(0,1);element.replaceChildren(span);}
  function titleMarkup(c){
    const path=imagePath(c.image),color=/^#[0-9a-f]{6}$/i.test(c.color||'')?c.color:'',light=/^#[0-9a-f]{6}$/i.test(c.lightColor||'')?c.lightColor:color;
    const icon=c.id==='none'||c.glyph===''?'':path?'<img class="title-reward-icon title-reward-dark" src="'+esc(path)+'" alt=""><img class="title-reward-icon title-reward-light" src="'+esc(path.replace('.png','-light.png'))+'" alt="">':window.PocketmateIcons(c.prefixIcon||'spark');
    return '<span class="title-reward" style="--reward-color:'+color+';--reward-light:'+light+'">'+icon+'<span>'+esc(c.name)+'</span></span>';
  }
  function acquisition(c){
    return c.acquisitionCondition||(c.id==='none'?'칭호를 표시하지 않는 기본 설정입니다.':c.starter?'서버 첫 접속 시 기본 지급됩니다.':'관리자가 지급하는 칭호입니다.');
  }
  function title(element,id){const cosmetic=item('title',id);const visible=Boolean(cosmetic&&id!=='none');element.innerHTML=visible?titleMarkup(cosmetic):'';element.hidden=!visible;}
  function updateCard(){
    if(snapshot?.playerName){$('player-name').textContent=snapshot.playerName;$('player-greeting').textContent=snapshot.playerName;}
    const value=equipped();if(!value)return;
    banner($('profile-card'),value.banner);avatar($('profile-avatar'),value.icon);title($('profile-title'),value.title);
    window.PocketmatePeople?.remember({id:snapshot.playerId,name:snapshot.playerName,appearance:{icon:value.icon,iconImage:item('icon',value.icon)?.image,bannerImage:item('banner',value.banner)?.image}});
  }
  function request(action,extra={}){
    if(pending)return;
    const requestId='profile_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,8);
    const timeout=setTimeout(()=>fail('프로필 정보를 확인하지 못했습니다. 다시 불러와주세요.'),7000);
    pending={requestId,action,timeout};feedback='';error=false;
    const payload={channel:'pocketmate:profile',action,requestId,...extra};
    try{
      if(typeof window.webgui?.postToGame==='function')window.webgui.postToGame(payload);
      else if(typeof window.cefQuery==='function')window.cefQuery({request:JSON.stringify(payload),onSuccess:()=>{},onFailure:()=>fail('프로필 서버에 연결하지 못했습니다.')});
      else fail('게임에 접속하면 보유한 꾸미기 항목을 확인할 수 있습니다.');
    }catch(_){fail('프로필 서버에 연결하지 못했습니다.');}
    render();
  }
  function fail(message){if(pending)clearTimeout(pending.timeout);pending=null;feedback=message;error=true;render();}
  function receive(event){
    const response=event.detail;if(!pending||response?.requestId!==pending.requestId)return;
    const action=pending.action;clearTimeout(pending.timeout);pending=null;
    if(response.type==='error'){feedback=response.message||'프로필 요청이 거절되었습니다.';error=true;render();if(action==='equip')setTimeout(()=>{if(!pending)request('view');},400);return;}
    if(response.type!=='snapshot'||!response.profile||!Array.isArray(response.profile.owned)||!Array.isArray(response.catalog)||typeof response.playerId!=='string'){fail('프로필 응답을 확인하지 못했습니다.');return;}
    snapshot=response;draft={icon:response.profile.icon,title:response.profile.title,banner:response.profile.banner};feedback=response.message||'';error=false;updateCard();render();
  }
  window.addEventListener('webgui:pocketmate:profile',receive);
  window.addEventListener('webgui:pocketmate:profile-skin',event=>{
    const value=event.detail;if(typeof value?.playerId!=='string'||typeof value.png!=='string'||value.png.length>100000||!/^iVBOR[A-Za-z0-9+/=]+$/.test(value.png))return;
    if(value.playerId!==snapshot?.playerId)return;
    skin={playerId:value.playerId,image:'data:image/png;base64,'+value.png};updateCard();updatePreview();
    if(host)host.querySelectorAll('[data-profile-skin]').forEach(el=>avatar(el,'skin'));
  });
  function updatePreview(){
    if(!host||!draft)return;const preview=host.querySelector('.profile-preview');if(!preview)return;
    banner(preview,draft.banner);avatar(preview.querySelector('.profile-preview-avatar'),draft.icon);title(preview.querySelector('.profile-title'),draft.title);
    preview.querySelector('.profile-preview-name').textContent=snapshot.playerName;
    host.querySelectorAll('[data-profile-item]').forEach(button=>button.setAttribute('aria-pressed',String(draft[tab]===button.dataset.profileItem)));
    showActions(Boolean(dirty()));
    const save=actionControl('[data-profile-save]');if(save)save.disabled=Boolean(pending)||!dirty();
    const cancel=actionControl('[data-profile-reset]');if(cancel)cancel.disabled=Boolean(pending)||!dirty();
  }
  function render(){
    if(!host||!host.isConnected)return;
    if(!snapshot){if(actionSlot){showActions(false);actionSlot.replaceChildren();}host.innerHTML=`<div class="profile-wait"><h2>프로필 꾸미기</h2><p role="status">${esc(pending?'보유한 항목을 불러오고 있습니다.':feedback||'프로필 정보를 확인해 주세요.')}</p><button class="primary-button" data-profile-retry ${pending?'disabled':''}>다시 불러오기</button></div>`;host.querySelector('button').onclick=()=>request('view');return;}
    const owned=snapshot.catalog.filter(c=>c.kind===tab&&snapshot.profile.owned.includes(c.kind+':'+c.id));
    host.innerHTML=`<section class="profile-studio" aria-label="프로필 꾸미기"><div class="profile-editor-scroll" aria-label="프로필 편집 항목"><div class="profile-preview" aria-label="착용 미리보기"><span class="profile-preview-tag">PREVIEW</span><span class="profile-avatar profile-preview-avatar"></span><div><div class="profile-heading"><span class="micro-label">CONNECTED PLAYER</span><span class="profile-title"></span></div><strong class="profile-preview-name"></strong></div></div><div class="profile-workspace"><div class="profile-tabs" role="tablist" aria-label="꾸미기 종류">${Object.entries(labels).map(([kind,label])=>`<button role="tab" id="profile-tab-${kind}" aria-controls="profile-options" data-profile-tab="${kind}" aria-selected="${tab===kind}">${label}<small>${snapshot.catalog.filter(c=>c.kind===kind&&snapshot.profile.owned.includes(c.kind+':'+c.id)).length}</small></button>`).join('')}</div><section class="profile-collection" id="profile-options" role="tabpanel" aria-labelledby="profile-tab-${tab}"><h2>보유한 ${labels[tab]}</h2><p class="profile-collection-desc">${descriptions[tab]}</p>${tab==='title'?'<p class="profile-acquisition-note">포획 칭호의 자동 지급은 준비 중이며, 현재는 관리자가 지급합니다.</p>':''}<div class="profile-choice-grid ${tab==='banner'?'profile-banner-options':''}">${owned.map(c=>`<button class="profile-choice ${tab==='title'?'profile-choice-title':''}" data-profile-item="${esc(c.id)}" aria-pressed="${draft[tab]===c.id}" ${pending?'disabled':''}>${tab==='icon'?`<span class="profile-option-icon profile-avatar" ${c.id==='skin'?'data-profile-skin':''}></span>`:tab==='banner'?'<span class="profile-banner-thumb"></span>':''}<span class="profile-choice-name ${tab==='title'?'profile-title-choice':''}">${tab==='title'?titleMarkup(c):esc(c.name)}</span>${tab==='title'?`<span class="profile-acquisition"><span class="profile-acquisition-label">획득 조건</span>${esc(acquisition(c))}</span>`:''}<small>${equipped()[tab]===c.id?'착용 중':c.starter?'기본 지급':'보유 중'}</small></button>`).join('')}</div></section></div><span class="profile-feedback" role="status" data-error="${error}">${esc(feedback||(dirty()?'미리보기 중 · 저장하면 카드에 적용됩니다.':'보유한 항목을 선택해 나만의 카드를 꾸며보세요.'))}</span></div><footer class="profile-actions"><button class="back-button" data-profile-reset>선택 되돌리기</button><button class="primary-button" data-profile-save>프로필 저장</button></footer></section>`;
    if(actionSlot){
      let shell=actionSlot.querySelector('.profile-actions-shell');
      if(!shell){shell=document.createElement('div');shell.className='profile-actions-shell';actionSlot.replaceChildren(shell);}
      shell.replaceChildren(host.querySelector('.profile-actions'));
    }
    host.querySelectorAll('[data-profile-tab]').forEach(button=>button.onclick=()=>{tab=button.dataset.profileTab;render();host.querySelector(`[data-profile-tab="${tab}"]`).focus({preventScroll:true});});
    const tabs=[...host.querySelectorAll('[role=tab]')];tabs.forEach((button,index)=>{button.tabIndex=button.getAttribute('aria-selected')==='true'?0:-1;button.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(e.key))return;e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(index+(['ArrowRight','ArrowDown'].includes(e.key)?1:tabs.length-1))%tabs.length;tabs[next].click();};});
    host.querySelectorAll('[data-profile-item]').forEach(button=>{
      if(tab==='icon')avatar(button.querySelector('.profile-option-icon'),button.dataset.profileItem);
      if(tab==='banner')banner(button.querySelector('.profile-banner-thumb'),button.dataset.profileItem);
      button.onclick=()=>{draft[tab]=button.dataset.profileItem;feedback='';error=false;updatePreview();host.querySelector('.profile-feedback').textContent=dirty()?'미리보기 중 · 저장하면 카드에 적용됩니다.':'현재 착용 중인 항목입니다.';};
    });
    actionControl('[data-profile-reset]').onclick=()=>{draft={icon:equipped().icon,title:equipped().title,banner:equipped().banner};feedback='선택을 되돌렸습니다.';render();};
    actionControl('[data-profile-save]').onclick=()=>request('equip',draft);updatePreview();
  }
  window.PocketmateProfile={displayName:()=>snapshot?.playerName||client?.username||'',mount(element){host=element;tab='icon';if(snapshot)draft={icon:equipped().icon,title:equipped().title,banner:equipped().banner};render();request('view');},unmount(){host=null;clearActions();},client(value){client=value;if(value?.username&&identity!==value.username){identity=value.username;snapshot=null;skin=null;request('view');}},diagnostics:()=>({connected:Boolean(snapshot),profile:equipped(),draft,dirty:Boolean(dirty())})};
  window.addEventListener('webgui:client',event=>window.PocketmateProfile.client(event.detail));
  if(window.webgui?.client)window.PocketmateProfile.client(window.webgui.client);
})();
