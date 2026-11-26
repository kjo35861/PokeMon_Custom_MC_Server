(() => {
  'use strict';
  const CHANNEL='pocketmate:estate',pending=new Map();
  let host=null,data=null,tab='overview',selected=new Map(),view=null,map=null,poll=null,retainedPane=null;
  let shownNotice='';
  let busy=false,loading=false,notice='',latestView='',accepted='',mapSession='',renderFrame=0;
  let options={grid:true,claims:true};
  let clientDimension=typeof window.webgui?.client?.dimension==='string'?window.webgui.client.dimension:null;
  const OVERWORLD='minecraft:overworld';
  const OVERWORLD_ONLY='영지 생성과 영토 구매는 오버월드에서만 가능합니다. 네더와 엔드에는 영지가 적용되지 않습니다.';
  function inOverworld(){return data?.dimension===OVERWORLD&&data.inOverworld===true&&(clientDimension===null||clientDimension===OVERWORLD);}
  try{options={...options,...JSON.parse(localStorage.getItem('pocketmate.mapOptions')||'{}')};}catch(_){}
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const glyph=window.PocketmateIcons;
  const key=(x,z)=>x+':'+z;
  const money=value=>Number(value||0).toLocaleString('ko-KR')+'원';
  function quote(count=selected.size){const rules=data?.pricing||{freeChunks:4,base:20000,increment:2500};const bought=data?.purchasedChunks??data?.ownedCount??1;let total=0,first=0,last=0;for(let i=0;i<count;i++){const price=bought+i<rules.freeChunks?0:rules.base+rules.increment*(bought+i-rules.freeChunks);if(!i)first=price;last=price;total+=price;}const treasury=Math.min(total,data?.treasury||0),personal=total-treasury;return {total,treasury,personal,first,last,shortfall:Math.max(0,personal-(data?.lordBalance||0))};}

  const cellAt=(x,z)=>data?.cells.find(c=>c.x===x&&c.z===z);
  function send(action,extra={}){
    if(!host||action!=='view'&&(busy||!data))return;
    if(['create','buy'].includes(action)&&!inOverworld()){notice=OVERWORLD_ONLY;render();return;}
    const requestId='estate_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,9);
    if(action==='view'){latestView=requestId;loading=true;}else if(action!=='players')busy=true;
    const timer=setTimeout(()=>{
      if(!pending.delete(requestId))return;if(action==='view'&&requestId!==latestView)return;
      loading=false;busy=false;notice=action==='view'?'영지 서버에 연결하지 못했습니다. 모드 설치와 서버 상태를 확인해 주세요.':'구매 결과 확인이 지연되었습니다. 소유권을 다시 확인합니다.';render();
      if(action!=='view')setTimeout(refresh,500);
    },7000);
    pending.set(requestId,{action,timer,query:extra.query||''});
    const payload={channel:CHANNEL,action,requestId,...extra,...(action==='view'?{mapSession}:{})};
    const failure=()=>{clearTimeout(timer);pending.delete(requestId);loading=false;busy=false;notice='영지 기능은 영지 모드가 설치된 Minecraft 안에서 사용할 수 있습니다.';render();};
    try{
      if(typeof window.webgui?.postToGame==='function')window.webgui.postToGame(payload);
      else if(typeof window.cefQuery==='function')window.cefQuery({request:JSON.stringify(payload),onSuccess:()=>{},onFailure:failure});
      else failure();
    }catch(_){failure();}
    if(!data||!['view','players'].includes(action))render();
  }
  function refresh(){send('view',view||{});}
  function receive(event){
    const response=event.detail;if(!response||!host)return;
    if(['community','image'].includes(response.type)){
      if(response.requestId!==accepted||!data)return;
      if(response.type==='community')Object.assign(data,{members:response.members||[],announcement:response.announcement||'',incomingInvites:response.incomingInvites||[],outgoingInvites:response.outgoingInvites||[]});
      else data.image=typeof response.image==='string'&&response.image.startsWith('data:image/jpeg;base64,')?response.image:'';
      render();return;
    }
    if(response.type==='players'){
      const request=pending.get(response.requestId);if(!request)return;clearTimeout(request.timer);pending.delete(response.requestId);
      const dialog=host.querySelector('.estate-invite');if(dialog&&request.query===dialog.querySelector('input').value)renderPlayers(dialog,response.players||[]);return;
    }
    if(response.type==='cells'){
      if(response.requestId!==accepted||!data||!Array.isArray(response.cells))return;
      const merged=new Map(data.cells.map(c=>[key(c.x,c.z),c]));for(const c of response.cells)merged.set(key(c.x,c.z),c);data.cells=[...merged.values()];updateSelection();scheduleRender();return;
    }
    const request=pending.get(response.requestId);if(!request)return;
    clearTimeout(request.timer);pending.delete(response.requestId);
    if(request.action==='view'&&response.requestId!==latestView)return;
    loading=false;if(request.action!=='view')busy=false;
    if(response.type==='error'){notice=response.message||'영지 요청이 거절되었습니다.';render();if(request.action!=='view'){alertDialog(notice);setTimeout(refresh,500);}return;}
    if(response.type!=='snapshot'||!Array.isArray(response.cells))return;
    data={...(data?.estateName===response.estateName?data:{}),...response};accepted=response.requestId;view={centerX:response.centerX,centerZ:response.centerZ,radius:response.radius};
    updateSelection();
    if(response.message){notice=response.message;if(['create','buy','deleteEstate','acceptInvite'].includes(request.action)){tab=request.action==='buy'?'manage':'overview';selected.clear();map?.setView(response.centerX,response.centerZ);}}
    render();
  }
  window.addEventListener('webgui:'+CHANNEL,receive);
  window.addEventListener('webgui:client',event=>{
    const dimension=event.detail?.dimension;
    if(typeof dimension!=='string'||dimension===clientDimension)return;
    clientDimension=dimension;
    if(!host)return;
    selected.clear();
    if(dimension!==OVERWORLD){notice=OVERWORLD_ONLY;host.querySelector('dialog[data-estate-purchase]')?.close();}
    else if(notice===OVERWORLD_ONLY)notice='';
    scheduleRender();
    if(!loading&&!busy)refresh();
  });
  window.addEventListener('webgui:pocketmate:terrain',event=>{if(host&&event.detail?.requestId===accepted)map?.receive(event.detail);});
  function updateSelection(){for(const cell of data.cells){const id=key(cell.x,cell.z);if(selected.has(id)){if(cell.owner)selected.delete(id);else selected.set(id,cell);}}}
  function toggle(position){
    if(busy)return;const id=key(position.x,position.z),cell=cellAt(position.x,position.z);
    if(selected.has(id))selected.delete(id);
    else if(!cell||cell.owner)return;
    else if(selected.size>=128){alertDialog('한 번에 최대 128개 청크를 선택할 수 있습니다.');return;}
    else selected.set(id,cell);
    tab='manage';render();
  }
  function selectionError(){
    if(!inOverworld())return OVERWORLD_ONLY;
    if(!selected.size)return '지도에서 구매할 청크를 선택해 주세요.';
    if(!data.ownedCount)return '먼저 광장에서 첫 영지를 생성해 주세요.';
    if(Number.isFinite(data.chunkLimit)&&data.ownedCount+selected.size>data.chunkLimit)return `레벨 ${data.estateLevel} 영지는 최대 ${data.chunkLimit}청크까지 소유할 수 있습니다. 금고·성장에서 승급한 뒤 구매해 주세요.`;
    const cells=[...selected.values()];
    if(cells.some(c=>c.owner))return '이미 소유주가 있는 청크가 포함되어 있습니다. 해당 청크를 선택 해제해 주세요.';
    if(cells.some(c=>c.owner===undefined))return ''; // The server checks off-screen or not-yet-loaded ownership.
    const remaining=new Map(selected),queue=cells.filter(c=>c.adjacent);
    for(const c of queue)remaining.delete(key(c.x,c.z));
    for(let i=0;i<queue.length;i++){const c=queue[i];for(const [x,z] of [[c.x-1,c.z],[c.x+1,c.z],[c.x,c.z-1],[c.x,c.z+1]]){const id=key(x,z);if(remaining.has(id)){queue.push(remaining.get(id));remaining.delete(id);}}}
    return remaining.size?'내 영지와 한 면 이상 이어지지 않은 청크가 있습니다. 선택한 청크들이 서로 연결되어 기존 영지에 닿아야 구매할 수 있습니다. 대각선은 연결로 인정되지 않습니다.':'';
  }
  function alertDialog(message){
    if(!host||host.querySelector('dialog[open]'))return;
    const dialog=document.createElement('dialog');dialog.className='estate-confirm estate-alert';
    dialog.innerHTML=`<h2>요청을 처리할 수 없습니다</h2><p>${esc(message)}</p><div class="estate-confirm-actions"><button class="primary-button" data-alert-close>확인</button></div>`;
    host.append(dialog);dialog.querySelector('button').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{dialog.remove();render();});dialog.showModal();
  }
  function nav(){
    const button=(id,icon,name)=>`<button data-estate-tab="${id}" class="${tab===id?'active':''}">${glyph(icon)}<span>${name}</span></button>`;
    return `<nav class="estate-nav" aria-label="영지 메뉴"><span class="estate-nav-label">ESTATE</span>${button('overview','home','광장')}${button('manage','land','영토')}${button('vault','vault','금고·성장')}${button('members','users','마을원')}${button('settings','gear','영지 설정')}<div class="estate-nav-bottom">${data?.isLord?`<button class="estate-danger-nav" data-estate-delete>${glyph('trash')}<span>영지 삭제</span></button>`:''}${button('options','gear','지도 설정')}</div></nav>`;
  }
  function mapPane(){return `<div class="estate-map-pane"><div class="estate-map-wrap"><canvas id="estate-map" aria-label="Xaero 오버월드 영토 지도. 드래그 이동, 휠 확대·축소. 청크를 클릭하면 선택하거나 취소합니다."></canvas><div class="map-legend"><span class="mine">내 영지</span><span class="other">다른 소유주</span><span class="selected">선택</span><span class="fog">미확인 지형</span></div><div class="map-tools"><button data-map-zoom-in aria-label="지도 확대">${glyph('plus')}</button><button data-map-zoom-out aria-label="지도 축소">${glyph('minus')}</button><span class="map-zoom-value">100%</span><button data-estate-location aria-label="내 위치로">${glyph('target')}</button><button data-estate-home aria-label="내 영지로">${glyph('home')}</button></div><div class="map-north">N<span>${glyph('up')}</span></div><div class="map-location"><b>오버월드</b><span class="map-position"></span></div><div class="map-scale"><span class="map-scale-line"></span><span class="map-scale-label"></span></div></div><div class="map-bottom"><span class="map-source">Xaero 지형 연결 중</span><span>드래그 이동 · 휠 확대 · 클릭 선택/취소</span></div></div>`;}
  function sidebar(){
    if(tab==='options')return `<div class="estate-side-heading"><span>MAP PREFERENCES</span><h2>지도 표시</h2><p>지형은 Xaero가 기록한 실제 월드맵입니다.</p></div><label class="estate-map-option">청크 격자<input type="checkbox" data-map-option="grid" ${options.grid?'checked':''}></label><label class="estate-map-option">소유권 표시<input type="checkbox" data-map-option="claims" ${options.claims?'checked':''}></label><p class="estate-help">어두운 사선 영역은 Xaero가 아직 불러오지 않은 지형입니다. M으로 월드맵을 한 번 열면 주변 기록을 확인할 수 있습니다.</p><p class="estate-help">설정은 이 PC에 저장됩니다. 지도 모양을 바꿔도 서버의 구매 조건과 소유권은 그대로 적용됩니다.</p>`;
    if(tab==='overview'){
      const has=data.ownedCount>0,allowed=data.purchaseEnabled&&inOverworld()&&!data.currentOwner&&!busy;
      return `<div class="estate-side-heading"><span>MY ESTATE</span><h2>${has?'나의 영지':'첫 영지를 만드세요'}</h2><p>${has?'지도에서 내 영지를 확인하고 연결된 청크로 확장하세요.':'오버월드에서 서 있는 무주 청크를 첫 영지로 등록합니다.'}</p></div><div class="estate-total">${data.ownedCount}<span>개 청크</span></div><dl><dt>면적</dt><dd>${(data.ownedCount*256).toLocaleString()} 블록²</dd><dt>현재 소유주</dt><dd>${inOverworld()?esc(data.currentOwner||'없음'):'오버월드에서 확인'}</dd></dl>${has?'<button class="primary-button" data-estate-manage>영토 관리 열기</button>':`<button class="primary-button" data-estate-create ${allowed?'':'disabled'}>영지 생성</button>`}<p class="estate-help">${!inOverworld()?OVERWORLD_ONLY:data.currentOwner&&!has?'이미 소유주가 있는 청크입니다. 다른 무주 청크로 이동해 주세요.':'추가 구매는 내 청크와 한 면 이상 맞닿아야 합니다. 대각선은 제외됩니다.'}</p><div class="estate-facts"><b>소유권은 서버가 보관합니다</b><p>동시 구매와 중복 구매를 서버에서 검사합니다. 금고를 먼저 사용하고 부족분은 영주 개인 재화에서 보충합니다.</p></div>`;
    }
    const count=selected.size,problem=count?selectionError():'';
    const canRequest=count>0&&data.ownedCount>0&&data.purchaseEnabled&&inOverworld()&&!busy;
    return `<div class="estate-side-heading"><span>SELECTED CHUNKS</span><div class="estate-heading-help"><h2>${count?count+'개 청크 선택':'영토 관리'}</h2><button type="button" class="help-button" aria-label="청크 선택 방법" data-help="청크를 클릭하면 선택하고, 다시 클릭하면 취소합니다. 선택한 청크들이 면으로 이어져 기존 영지와 연결되어야 합니다. 대각선은 연결로 인정되지 않습니다.">?</button></div></div><dl><dt>선택한 청크</dt><dd>${count}개</dd><dt>구매 면적</dt><dd>${(count*256).toLocaleString()} 블록²</dd><dt>구매 총액<button type="button" class="help-button" aria-label="영토 구매 조건과 비용 안내" data-help="구매 대상은 오버월드의 청크입니다. 떨어진 청크나 이미 소유주가 있는 청크가 포함되면 전체 구매가 취소됩니다.&#10;&#10;기본 4청크까지 무료이며, 5번째 청크부터 20,000원에서 2,500원씩 증가합니다. 금고가 부족하면 영주 개인 재화에서 부족분만 보충합니다.">?</button></dt><dd>${money(quote(count).total)}</dd><dt>금고 사용</dt><dd>${money(quote(count).treasury)}</dd><dt>영주 개인 재화 보충</dt><dd>${money(quote(count).personal)}</dd><dt>현재 한도</dt><dd>${data.ownedCount} / ${data.chunkLimit??'—'}청크</dd><dt>확장 조건</dt><dd>${!count?'선택 대기':problem?'확인 필요':'구매 시 최종 확인'}</dd></dl><button class="primary-button" data-estate-buy ${canRequest?'':'disabled'}>${busy?'처리 중…':count+'개 청크 구매'}</button><button class="back-button estate-clear-selection" data-estate-clear ${count&&!busy?'':'disabled'}>선택 모두 취소</button>${!inOverworld()?`<p class="estate-help" role="status">${OVERWORLD_ONLY}</p>`:''}`;
  }

  function scheduleRender(){if(!renderFrame)renderFrame=requestAnimationFrame(()=>{renderFrame=0;render();});}
  function render(){
    if(!host||host.querySelector('dialog[open]'))return;
    window.PocketmateHelp?.hide();
    const previous=host.querySelector('.estate-map-pane')||retainedPane,scroll=host.querySelector('.estate-sidebar')?.scrollTop||0,stageScroll=host.querySelector('.estate-vault-stage')?.scrollTop||0;
    if(notice&&notice!==shownNotice){window.PocketmateNotify.show(notice);shownNotice=notice;}else if(!notice)shownNotice='';
    host.innerHTML=`<div class="estate-app"><header class="estate-header"><div><span class="estate-eyebrow">POCKETMATE / ESTATES</span><h1>${data?esc(data.estateName||'새로운 영지'):'영지 연결 중'}</h1></div><div class="estate-header-stats">${data?.hasEstate?`<span class="estate-level-badge">Lv. ${data.estateLevel??0}</span>`:''}<span>소유 <b>${data?.ownedCount??'—'}</b> / ${data?.chunkLimit??1}청크</span><span class="estate-test-badge">${data?.testEconomy?'테스트 재화':'영지 금고'}</span><button data-estate-refresh>새로고침</button></div></header>${nav()}<section class="estate-stage${['vault','settings'].includes(tab)?' estate-vault-stage':''}">${data?stage():`<div class="estate-wait"><h2>${loading?'서버에서 영지 정보를 확인하고 있습니다':'영지 서버에 연결해 주세요'}</h2><p>접속한 서버가 실제 소유권과 구매 가능 여부를 확인합니다.</p><button data-estate-refresh>다시 확인</button></div>`}</section></div>`;
    const nextPane=host.querySelector('.estate-map-pane');
    if(nextPane){
      if(previous){nextPane.replaceWith(previous);retainedPane=previous;}
      else{retainedPane=nextPane;map=window.PocketmateMap.create(nextPane,{onSelect:toggle,onViewport(bounds){view=bounds;if(!busy)refresh();}});}
    }else retainedPane=previous;
    if(data&&map){map.update(data,[...selected.values()]);map.options(options);const side=host.querySelector('.estate-sidebar');if(side)side.scrollTop=scroll;}
    host.querySelectorAll('[data-estate-tab]').forEach(button=>button.onclick=()=>{tab=button.dataset.estateTab;render();});
    host.querySelectorAll('[data-estate-refresh]').forEach(button=>button.onclick=()=>{notice='';refresh();});
    host.querySelector('[data-estate-manage]')?.addEventListener('click',()=>{tab='manage';render();});
    host.querySelector('[data-estate-create]')?.addEventListener('click',()=>confirm('create',data.currentX,data.currentZ));
    host.querySelector('[data-estate-buy]')?.addEventListener('click',()=>{const problem=selectionError();if(problem)alertDialog(problem);else if(quote().shortfall)alertDialog('영지 금고와 영주 개인 재화를 합쳐도 '+money(quote().shortfall)+'이 부족합니다.');else confirm('buy');});
    host.querySelector('[data-estate-clear]')?.addEventListener('click',()=>{if(!busy){selected.clear();render();}});
    if(['vault','settings'].includes(tab))host.querySelector('.estate-vault-stage').scrollTop=stageScroll;
    bindCommunity();
    window.PocketmatePeople.hydrate(host);
    host.querySelectorAll('[data-map-option]').forEach(input=>input.onchange=()=>{options[input.dataset.mapOption]=input.checked;map.options(options);try{localStorage.setItem('pocketmate.mapOptions',JSON.stringify(options));}catch(_){}});
  }

  function confirm(action,x,z){
    if(busy||!host)return;
    if(!inOverworld()){alertDialog(OVERWORLD_ONLY);return;}
    const chunks=[...selected.values()].map(({x,z})=>({x,z}));const dialog=document.createElement('dialog');dialog.className='estate-confirm';dialog.dataset.estatePurchase=action;
    dialog.innerHTML=`<p class="eyebrow">${action==='create'?'CREATE ESTATE':'EXPAND ESTATE'}</p><h2>${action==='create'?'첫 영지를 생성할까요?':chunks.length+'개 청크를 구매할까요?'}</h2><p>${action==='create'?'현재 서 있는 오버월드 청크':'오버월드 '+chunks.length+'개 청크 · '+(chunks.length*256).toLocaleString()+' 블록²'}<br>${action==='create'?'레벨 0 · 기본 1청크 무료 지급':`총액 ${money(quote().total)}<br>금고 ${money(quote().treasury)} · 영주 개인 재화에서 ${money(quote().personal)} 보충`}<br>서버가 ${action==='create'?'현재 서 있는 위치와 소유권':'소유권과 내 영지에 닿는 면'}을 다시 확인합니다.</p>${action==='create'?'<label class="estate-field">영지 이름<input id="estate-create-name" maxlength="24" placeholder="우리 영지의 이름" autocomplete="off"></label>':''}<div class="estate-confirm-actions"><button class="back-button" data-cancel>취소</button><button class="primary-button" data-confirm ${action==='create'?'disabled':''}>${action==='create'?'영지 생성 요청':'구매 요청'}</button></div>`;
    host.append(dialog);dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{dialog.remove();render();});
    const nameInput=dialog.querySelector('#estate-create-name');if(nameInput)nameInput.oninput=()=>dialog.querySelector('[data-confirm]').disabled=!nameInput.value.trim();
    dialog.querySelector('[data-confirm]').onclick=()=>{const name=nameInput?.value.trim();dialog.close();dialog.remove();notice='';send(action,action==='create'?{x,z,name}:{chunks,expectedPurchasedChunks:data.purchasedChunks??data.ownedCount,expectedTotal:quote(chunks.length).total});};dialog.showModal();
  }

  const roleName=role=>({LORD:'영주',STEWARD:'부영주',RESIDENT:'영지민'})[role]||'영지민';
  const date=value=>value?new Date(value).toLocaleString('ko-KR'):'기록 없음';
  function roster(manage=false){
    const members=data.members||[];
    return `<div class="estate-roster"><table><thead><tr><th>닉네임</th><th>등급</th><th>접속</th><th>마지막 접속</th>${manage&&data.isLord?'<th>관리</th>':''}</tr></thead><tbody>${members.map(m=>`<tr><td>${window.PocketmatePeople.markup(m)}</td><td>${manage&&data.isLord&&m.role!=='LORD'?`<select aria-label="${esc(m.name)} 등급" data-role-target="${esc(m.id)}"><option value="STEWARD" ${m.role==='STEWARD'?'selected':''}>부영주</option><option value="RESIDENT" ${m.role==='RESIDENT'?'selected':''}>영지민</option></select>`:`<span class="member-rank ${m.role==='LORD'?'lord':''}">${roleName(m.role)}</span>`}</td><td><span class="member-status ${m.online?'online':''}">${m.online?'접속 중':'오프라인'}</span></td><td class="member-last-seen">${esc(date(m.lastSeen))}</td>${manage&&data.isLord?`<td>${m.role==='LORD'?'<span class="estate-muted">마을 주인</span>':`<button data-member-kick="${esc(m.id)}">추방</button>`}</td>`:''}</tr>`).join('')||'<tr><td colspan="5">마을원 정보를 확인하고 있습니다.</td></tr>'}</tbody></table></div>`;
  }
  function invitations(){return (data.incomingInvites||[]).length?`<div class="estate-incoming"><h3>도착한 영지 초대</h3>${data.incomingInvites.map(i=>`<div><strong>${esc(i.name)}</strong><button data-invite-accept="${esc(i.id)}">수락</button><button data-invite-decline="${esc(i.id)}">거절</button></div>`).join('')}<p>수락하면 해당 영지의 영지민이 됩니다.</p></div>`:'';}
  function vaultPage(){
    if(!data.hasEstate)return '<section class="estate-wait"><h2>영지를 먼저 생성해 주세요</h2><p>영지 금고와 레벨은 소속 영지가 있을 때 사용할 수 있습니다.</p></section>';
    const level=data.estateLevel??0,levels=data.levels||[],next=levels.find(row=>row.level===level+1),balance=data.treasury||0,personal=data.personalBalance||0;
    const canUpgrade=data.isLord&&next&&balance>=next.cost&&!busy;
    const names={DEPOSIT:'마을원 저축',AUTO_DEPOSIT:'영주 재화 자동 보충',TEST_CREDIT:'테스트 입금',UPGRADE:'영지 승급',PURCHASE:'청크 구매'};
    return `<section class="estate-vault"><header class="estate-vault-heading"><span>ESTATE TREASURY / GROWTH</span><h2>함께 모으고, 더 넓게 자라요</h2><p>저축한 금고 재화로 영주가 레벨을 올립니다. 승급은 청크 구매 한도를 늘리며, 청크는 영토에서 직접 구매합니다.</p><button class="estate-schedule-link" data-growth-schedule>영지 성장 단계 보기 ${glyph('down')}</button></header><div class="estate-vault-top"><section class="estate-vault-card"><span class="estate-eyebrow">OUR TREASURY</span><h3>영지 금고</h3><strong class="estate-vault-balance">${money(balance)}</strong><p>내 개인 재화 <b>${money(personal)}</b></p><button data-vault-deposit ${busy||personal<1?'disabled':''}>금고에 저축</button><p class="estate-vault-note">청크 구매는 금고를 먼저 사용하고 부족분만 영주 개인 재화에서 보충합니다. 승급은 금고 잔액만 사용합니다.</p></section><section class="estate-vault-card estate-growth-card"><div class="estate-growth-level"><span>현재 영지 레벨</span><strong>Lv. ${level}<small> / 10</small></strong></div><div class="estate-growth-limit"><span>보유 / 구매 가능 한도</span><b>${data.ownedCount} / ${data.chunkLimit}청크</b></div><div class="estate-growth-members"><span>마을원 / 최대 인원 (영주 포함)</span><b>${(data.members||[]).length} / ${data.memberLimit??5}명</b></div>${next?`<p class="estate-growth-next">Lv. ${next.level} ${glyph('arrow')} 최대 ${next.limit}청크</p><dl><dt>승급 비용</dt><dd>${money(next.cost)}</dd><dt>승급 후 금고 잔액</dt><dd>${balance>=next.cost?money(balance-next.cost):money(next.cost-balance)+' 부족'}</dd></dl><button class="primary-button" data-estate-upgrade ${canUpgrade?'':'disabled'}>${next.cost?'Lv. '+next.level+' 승급':'Lv. '+next.level+' 무료 승급'}</button><p class="estate-vault-note">${!data.isLord?'승급은 영주만 할 수 있습니다.':balance<next.cost?'금고에 필요한 금액을 먼저 저축해 주세요.':'금고에서 비용이 차감됩니다.'}</p>`:'<p class="estate-growth-next">최대 레벨에 도달했습니다.</p><p>최대 36청크까지 구매할 수 있습니다.</p>'}</section></div><section class="estate-level-schedule"><h3>영지 성장 단계</h3><p>각 비용은 해당 레벨로 한 단계 승급할 때 금고에서 차감되는 금액입니다. 최대 인원은 영주를 포함하며, 현재 모든 레벨에서 5명으로 고정됩니다.</p><div class="estate-vault-table"><table><thead><tr><th>레벨</th><th>승급 비용</th><th>최대 청크</th><th>최대 인원</th><th>상태</th></tr></thead><tbody>${levels.map(row=>`<tr class="${row.level===level?'current':''}"><td>Lv. ${row.level}</td><td>${money(row.cost)}</td><td>${row.limit}청크</td><td>${row.memberLimit??data.memberLimit??5}명</td><td>${row.level===level?'현재 레벨':row.level<level?'달성':row.level===level+1?'다음 단계':'잠김'}</td></tr>`).join('')}</tbody></table></div></section><section class="estate-vault-history"><h3>금고 사용 기록</h3>${(data.vaultHistory||[]).length?`<div class="estate-vault-table"><table><thead><tr><th>내용</th><th>금액</th><th>시간</th></tr></thead><tbody>${[...data.vaultHistory].reverse().map(row=>`<tr><td>${names[row.type]||'금고 기록'}${row.type==='UPGRADE'?' · Lv. '+row.level:''}</td><td>${['UPGRADE','PURCHASE'].includes(row.type)?'−':'+'}${money(row.amount)}</td><td>${esc(date(row.at))}</td></tr>`).join('')}</tbody></table></div>`:'<p>아직 금고 사용 기록이 없습니다.</p>'}</section></section>`;
  }
  function depositDialog(){
    const balance=data.personalBalance||0;const dialog=modal(`<h2>영지 금고에 저축</h2><p>내 개인 재화 ${money(balance)}<br>저축한 재화는 영지 승급과 청크 구매에 사용합니다. 개인 지갑으로 출금하는 기능은 제공하지 않습니다.</p><label class="estate-field">저축 금액<input type="number" id="vault-deposit-amount" min="1" max="${balance}" step="1" inputmode="numeric" placeholder="금액을 입력하세요"></label><div class="estate-confirm-actions"><button class="back-button" data-cancel>취소</button><button class="primary-button" data-deposit-confirm disabled>저축하기</button></div>`);
    if(!dialog)return;const input=dialog.querySelector('input'),button=dialog.querySelector('[data-deposit-confirm]');input.oninput=()=>button.disabled=!Number.isSafeInteger(input.valueAsNumber)||input.valueAsNumber<=0||input.valueAsNumber>balance;button.onclick=()=>{const amount=input.valueAsNumber;dialog.close();send('deposit',{amount});};
  }
  function settingsPage(){
    if(!data.hasEstate)return '<section class="estate-wait"><h2>소속 영지가 없습니다</h2><p>영지를 생성하거나 초대를 수락하면 홈 지점을 확인할 수 있습니다.</p></section>';
    const allowed=data.isLord&&inOverworld()&&data.canSetHome&&!busy;
    return `<section class="estate-settings-page"><header class="estate-members-heading"><div><span>ESTATE SETTINGS</span><h2>영지 설정</h2><p>우리 영지의 이동 지점과 운영 설정을 관리합니다.</p></div></header><section class="estate-community-card estate-home-card"><header><div><span>VILLAGE HOME</span><h2>영지 홈 지점</h2></div>${glyph('home')}</header><p class="estate-announcement">마을 이동 버튼을 누르면 이 영지의 홈으로 이동합니다. 기본 홈은 영지를 처음 만든 위치입니다.</p><div class="estate-home-status"><span>오버월드</span><strong>${data.home?.surface?'최초 영지 안의 기본 지점':'홈 지점 설정됨'}</strong></div><div class="estate-home-actions"><button class="primary-button" data-estate-travel-home ${busy?'disabled':''}>${glyph('compass')}마을 이동</button>${data.isLord?`<button class="primary-button" data-estate-set-home ${allowed?'':'disabled'}>현재 위치를 홈으로 지정</button>`:''}</div><p class="estate-search-help">${!data.isLord?'홈 지점은 영주만 변경할 수 있습니다.':!inOverworld()?'오버월드의 내 영지 안에서 홈 지점을 지정해 주세요.':!data.canSetHome?'내 영지 안으로 이동한 뒤 홈을 지정해 주세요.':'안전하고 단단한 바닥에 서서 지정해 주세요. 현재 위치와 바라보는 방향을 저장합니다.'}</p></section></section>`;
  }
  function stage(){
    if(tab==='settings')return settingsPage();
    if(tab==='vault')return vaultPage();
    if(tab==='overview'&&data.hasEstate)return `<div class="estate-plaza"><section class="estate-photo-card">${data.image?`<img class="estate-cover" src="${esc(data.image)}" alt="${esc(data.estateName)} 대표 이미지">`:'<div class="estate-photo-empty"><svg><use href="#i-leaf"/></svg><h2>우리 영지의 풍경을 담아보세요</h2><p>함께 만든 마을, 기억하고 싶은 순간</p></div>'}<div class="estate-photo-caption"><div><span>OUR HOME</span><h2>${esc(data.estateName)}</h2><p>레벨 ${data.estateLevel??0} · ${data.ownedCount}/${data.chunkLimit??1}청크 · 마을원 ${(data.members||[]).length}/${data.memberLimit??5}명</p></div>${data.isLord?`<div class="estate-photo-actions"><button data-estate-image ${busy?'disabled':''}>대표 이미지 변경</button>${data.image?`<button data-estate-image-delete ${busy?'disabled':''}>대표이미지 삭제</button>`:''}</div><input type="file" data-estate-image-file accept="image/png,image/jpeg,image/webp" hidden>`:''}</div><div class="estate-photo-foot"><span>우리의 땅, 함께하는 이야기</span><button data-estate-manage>영토 둘러보기 ${glyph('arrow')}</button></div></section><div class="estate-plaza-right"><section class="estate-community-card"><header><div><span>LORD’S MESSAGE</span><h2>영주 공지</h2></div>${data.isLord?'<button data-estate-notice>공지 수정</button>':''}</header><p class="estate-announcement">${esc(data.announcement||'아직 등록된 영주 공지가 없습니다.')}</p></section><section class="estate-community-card estate-plaza-roster"><header><div><span>OUR PEOPLE</span><h2>함께하는 마을원</h2></div><button data-estate-tab="members">모두 보기</button></header>${roster()}</section></div></div>`;
    if(tab==='members')return `<section class="estate-members-page"><header class="estate-members-heading"><div><span>OUR PEOPLE</span><h2>마을원 관리 · ${(data.members||[]).length}/${data.memberLimit??5}명</h2><p>영주 · 부영주 · 영지민${data.isLord?' — 영주만 초대·추방·등급 변경을 할 수 있습니다.':' — 영주가 마을원을 관리합니다.'}</p></div>${data.isLord?`<button class="primary-button" data-estate-invite ${(data.members||[]).length>=(data.memberLimit??5)?'disabled':''}>${(data.members||[]).length>=(data.memberLimit??5)?'정원 가득 참':'마을원 초대'}</button>`:''}</header>${data.hasEstate?roster(true):'<p class="estate-empty-copy">소속된 영지가 없습니다. 영지를 생성하거나 초대를 수락해 주세요.</p>'}${invitations()}${data.isLord?`<section class="estate-outgoing"><h3>초대 수락 대기</h3>${(data.outgoingInvites||[]).map(i=>`<p>${window.PocketmatePeople.markup(i)}<span>${esc(date(i.at))} 초대 · 7일간 유효</span></p>`).join('')||'<p>대기 중인 초대가 없습니다.</p>'}</section>`:''}</section>`;
    return `${tab==='overview'?invitations():''}<div class="estate-workspace">${mapPane()}<aside class="estate-sidebar">${sidebar()}</aside></div>`;
  }
  function modal(markup,wide=false){
    if(busy||!host||host.querySelector('dialog[open]'))return null;
    const dialog=document.createElement('dialog');dialog.className='estate-confirm'+(wide?' estate-invite':'');dialog.innerHTML=markup;
    host.append(dialog);dialog.querySelector('[data-cancel]')?.addEventListener('click',()=>dialog.close());
    dialog.addEventListener('close',()=>{dialog.remove();render();});dialog.showModal();return dialog;
  }
  function actionConfirm(title,copy,action,payload,person){
    const dialog=modal(`<h2>${esc(title)}</h2><p>${esc(copy)}</p>${person?window.PocketmatePeople.markup(person):''}<div class="estate-confirm-actions"><button class="back-button" data-cancel>취소</button><button class="primary-button" data-confirm>확인</button></div>`);
    if(dialog){window.PocketmatePeople.hydrate(dialog);dialog.querySelector('[data-confirm]').onclick=()=>{dialog.close();send(action,payload);};}
  }
  function editNotice(){
    const dialog=modal(`<h2>영주 공지 작성</h2><label class="estate-field">마을원들에게 전할 이야기<textarea maxlength="1000" rows="7" id="estate-notice-text">${esc(data.announcement||'')}</textarea></label><div class="estate-confirm-actions"><button class="back-button" data-cancel>취소</button><button class="primary-button" data-save-notice>공지 저장</button></div>`);
    if(dialog)dialog.querySelector('[data-save-notice]').onclick=()=>{const text=dialog.querySelector('textarea').value;dialog.close();send('notice',{text});};
  }
  function deleteDialog(){
    if(!data.isLord)return;
    const dialog=modal(`<p class="eyebrow">DELETE ESTATE</p><h2>정말 영지를 삭제할까요?</h2><p>영지의 모든 청크 소유권, 마을원, 초대, 공지와 대표 이미지가 삭제됩니다. 금고 잔액 ${money(data.treasury)}과 성장 기록도 함께 삭제됩니다. 이 작업은 되돌릴 수 없습니다.</p><label class="estate-field">영지 이름을 똑같이 입력해 주세요: <strong>${esc(data.estateName)}</strong><input id="estate-delete-name" autocomplete="off" spellcheck="false"></label><div class="estate-confirm-actions"><button class="back-button" data-cancel>취소</button><button class="estate-danger-button" data-confirm-delete disabled>영지 영구 삭제</button></div>`);
    if(!dialog)return;const input=dialog.querySelector('input'),button=dialog.querySelector('[data-confirm-delete]');
    input.oninput=()=>button.disabled=input.value!==data.estateName;
    button.onclick=()=>{if(input.value!==data.estateName)return;const name=input.value;dialog.close();send('deleteEstate',{name});};
  }
  function renderPlayers(dialog,players){
    const results=dialog.querySelector('.estate-invite-results');
    results.innerHTML=players.map(p=>`<div class="estate-invite-player"><div>${window.PocketmatePeople.markup(p)}<small class="member-status ${p.online?'online':''}">${p.online?'접속 중':'오프라인'} · ${esc(p.status)}</small></div><button data-invite-user="${esc(p.id)}" ${p.available?'':'disabled'}>${p.available?'초대':esc(p.status)}</button></div>`).join('')||'<p>검색 결과가 없습니다.</p>';
    window.PocketmatePeople.hydrate(results);
    results.querySelectorAll('[data-invite-user]').forEach(button=>button.onclick=()=>{const target=button.dataset.inviteUser;dialog.close();send('invite',{target});});
  }
  function inviteDialog(){
    if(!data.isLord)return;
    const dialog=modal('<h2>마을원 초대</h2><label class="estate-field">유저 이름 검색<input id="estate-player-search" placeholder="닉네임을 검색하세요" maxlength="32" autocomplete="off"></label><p class="estate-search-help">기본 목록은 현재 접속 중인 유저입니다. 검색하면 서버에 접속했던 유저도 찾을 수 있습니다.</p><div class="estate-invite-results"><p>접속 중인 유저를 확인하고 있습니다…</p></div><div class="estate-confirm-actions"><button class="back-button" data-cancel>닫기</button></div>',true);
    if(!dialog)return;let searchTimer;const input=dialog.querySelector('input');input.oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{if(dialog.isConnected)send('players',{query:input.value});},300);};dialog.addEventListener('close',()=>clearTimeout(searchTimer));send('players',{query:''});
  }
  async function chooseImage(file){
    if(!file||!data.isLord)return;
    if(file.size>10*1024*1024||!['image/png','image/jpeg','image/webp'].includes(file.type)){alertDialog('10MB 이하의 PNG, JPEG 또는 WebP 이미지를 선택해 주세요.');return;}
    const url=URL.createObjectURL(file),image=new Image();
    try{
      image.src=url;await image.decode();const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');let width=Math.min(960,image.naturalWidth),encoded='';
      for(let attempt=0;attempt<12;attempt++){
        canvas.width=Math.round(width);canvas.height=Math.max(1,Math.round(width*9/16));ctx.fillStyle='#16242a';ctx.fillRect(0,0,canvas.width,canvas.height);
        const scale=Math.max(canvas.width/image.naturalWidth,canvas.height/image.naturalHeight);ctx.drawImage(image,(canvas.width-image.naturalWidth*scale)/2,(canvas.height-image.naturalHeight*scale)/2,image.naturalWidth*scale,image.naturalHeight*scale);
        encoded=canvas.toDataURL('image/jpeg',.72);if(encoded.length<=17500)break;width*=.8;
      }
      if(encoded.length>17500){alertDialog('이 이미지는 압축할 수 없습니다. 다른 이미지를 선택해 주세요.');return;}
      const dialog=modal(`<h2>대표 이미지로 사용할까요?</h2><img class="estate-image-preview" src="${encoded}" alt="대표 이미지 미리보기"><p>16:9 비율로 맞춰 영지 광장에 표시합니다.</p><div class="estate-confirm-actions"><button class="back-button" data-cancel>취소</button><button class="primary-button" data-image-save>이미지 저장</button></div>`);
      if(dialog)dialog.querySelector('[data-image-save]').onclick=()=>{dialog.close();send('image',{image:encoded});};
    }catch(_){alertDialog('이미지를 읽지 못했습니다. 다른 파일을 선택해 주세요.');}finally{URL.revokeObjectURL(url);}
  }
  function bindCommunity(){
    host.querySelector('[data-estate-set-home]')?.addEventListener('click',()=>actionConfirm('현재 위치를 영지 홈으로 지정할까요?','마을 이동 버튼의 도착 지점이 바뀝니다. 서버가 현재 위치와 영주 권한을 다시 확인합니다.','setHome',{}));
    host.querySelector('[data-estate-travel-home]')?.addEventListener('click',()=>window.PocketmateTravel.go());
    host.querySelector('[data-growth-schedule]')?.addEventListener('click',()=>host.querySelector('.estate-level-schedule')?.scrollIntoView({block:'start'}));
    host.querySelector('[data-vault-deposit]')?.addEventListener('click',depositDialog);
    host.querySelector('[data-estate-upgrade]')?.addEventListener('click',()=>{const next=data.levels.find(row=>row.level===data.estateLevel+1);if(next)actionConfirm('영지 레벨을 올릴까요?',`금고에서 ${money(next.cost)}을 사용해 Lv. ${next.level}로 승급합니다. 최대 ${next.limit}청크까지 구매할 수 있습니다.`,'upgrade',{expectedLevel:data.estateLevel});});
    host.querySelector('[data-estate-delete]')?.addEventListener('click',deleteDialog);
    host.querySelector('[data-estate-notice]')?.addEventListener('click',editNotice);
    host.querySelector('[data-estate-invite]')?.addEventListener('click',inviteDialog);
    host.querySelector('[data-estate-image-delete]')?.addEventListener('click',()=>actionConfirm('대표이미지를 삭제할까요?','등록한 이미지를 지우고 기본 화면으로 되돌립니다.','image',{image:''}));
    host.querySelector('[data-estate-image]')?.addEventListener('click',()=>host.querySelector('[data-estate-image-file]').click());
    host.querySelector('[data-estate-image-file]')?.addEventListener('change',event=>chooseImage(event.target.files[0]));
    host.querySelectorAll('[data-role-target]').forEach(select=>select.onchange=()=>{const target=select.dataset.roleTarget,role=select.value;actionConfirm('마을원 등급을 변경할까요?',roleName(role)+' 등급으로 변경합니다.','role',{target,role},data.members.find(m=>m.id===target));});
    host.querySelectorAll('[data-member-kick]').forEach(button=>button.onclick=()=>{const target=button.dataset.memberKick,member=data.members.find(m=>m.id===target);actionConfirm('마을원을 추방할까요?',member.name+' 님이 영지에서 제외됩니다.','kick',{target},member);});
    host.querySelectorAll('[data-invite-accept]').forEach(button=>button.onclick=()=>actionConfirm('영지 초대를 수락할까요?','해당 영지에 영지민으로 가입합니다.','acceptInvite',{estate:button.dataset.inviteAccept}));
    host.querySelectorAll('[data-invite-decline]').forEach(button=>button.onclick=()=>actionConfirm('초대를 거절할까요?','해당 초대를 거절합니다.','declineInvite',{estate:button.dataset.inviteDecline}));
  }
  window.PocketmateEstates={
    mount(element){for(const request of pending.values())clearTimeout(request.timer);pending.clear();host=element;data=null;selected=new Map();view=null;map=null;retainedPane=null;tab='overview';accepted='';mapSession='map_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,9);busy=false;loading=false;notice='';document.body.classList.add('estate-active');render();refresh();poll=setInterval(()=>{if(host&&!loading&&!busy&&!document.hidden&&!host.querySelector('dialog[open]')&&!host.querySelector('input:focus,textarea:focus,select:focus')&&!map?.isInteracting())refresh();},5000);},
    unmount(){cancelAnimationFrame(renderFrame);renderFrame=0;map?.destroy();map=null;retainedPane=null;host=null;clearInterval(poll);poll=null;document.body.classList.remove('estate-active');},
    diagnostics:()=>({...map?.diagnostics(),selectedCount:selected.size})
  };
})();
