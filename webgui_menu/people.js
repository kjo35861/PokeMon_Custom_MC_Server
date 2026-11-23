/* One public identity component for member lists, invitations and user confirmations. */
(() => {
  'use strict';
  const people=new Map(),skins=new Map();
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const asset=value=>typeof value==='string'&&/^\.\/profile-assets\/[a-z0-9-]+\.(png|svg)$/.test(value)?value:'';
  function remember(person){
    if(!person||typeof person.id!=='string'||person.id.length>64)return null;
    const old=people.get(person.id),raw=person.appearance;
    const appearance=raw&&typeof raw.icon==='string'?{icon:raw.icon,iconImage:asset(raw.iconImage),bannerImage:asset(raw.bannerImage)}:old?.appearance||{icon:'skin',iconImage:'',bannerImage:''};
    const value={id:person.id,name:String(person.name||old?.name||'플레이어'),appearance};
    people.set(value.id,value);
    if(people.size>256)people.delete(people.keys().next().value);
    return value;
  }
  function avatarUrl(person){
    const value=typeof person==='string'?people.get(person):person;
    return value?.appearance?.icon==='skin'?skins.get(value.id)||'':asset(value?.appearance?.iconImage);
  }
  function markup(person){
    const value=remember(person);if(!value)return '';
    const style=value.appearance.bannerImage?` style="--profile-banner:url('${value.appearance.bannerImage}')"`:'';
    return `<span class="people-card"${style}><span class="people-avatar" data-person-avatar="${esc(value.id)}">${esc(value.name.slice(0,1))}</span><strong class="people-name">${esc(value.name)}</strong></span>`;
  }
  function hydrate(root=document){
    root.querySelectorAll('[data-person-avatar]').forEach(element=>{
      const value=people.get(element.dataset.personAvatar);if(!value)return;
      const url=avatarUrl(value);
      if(!url){element.textContent=value.name.slice(0,1);return;}
      if(element.firstElementChild?.getAttribute('src')===url)return;
      const img=new Image();img.alt=value.appearance.icon==='skin'?value.name+'의 스킨 얼굴':value.name+'의 프로필아이콘';
      img.className=value.appearance.icon==='skin'?'skin-face':'pokemon-face';
      img.onerror=()=>{if(element.firstElementChild===img)element.textContent=value.name.slice(0,1);};
      img.src=url;element.replaceChildren(img);
    });
  }
  window.addEventListener('webgui:pocketmate:profile-skin',event=>{
    const value=event.detail;
    if(typeof value?.playerId!=='string'||typeof value.png!=='string'||value.png.length>100000||!/^iVBOR[A-Za-z0-9+/=]+$/.test(value.png))return;
    skins.set(value.playerId,'data:image/png;base64,'+value.png);
    if(skins.size>256)skins.delete(skins.keys().next().value);
    hydrate();window.dispatchEvent(new CustomEvent('pocketmate:peoplechange'));
  });
  window.PocketmatePeople={remember,markup,hydrate,avatarUrl,skin:id=>skins.get(id)||'',get:id=>people.get(id)};
})();
