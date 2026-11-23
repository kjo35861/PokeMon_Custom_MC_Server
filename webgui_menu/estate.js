(() => {
  'use strict';
  const CHANNEL = 'pocketmate:estate';
  let host = null, data = null, tab = 'overview', selected = null, center = null;
  let busy = false, loading = false, connected = false, notice = '', poll = null, observer = null, latestView = '';
  const pending = new Map();
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const label = (x,z) => `[${x}, ${z}]`;
  const cellAt = (x,z) => data?.cells?.find(c => c.x === x && c.z === z);
  function send(action, extra = {}) {
    if (action !== 'view' && (busy || !connected || !data)) return;
    const requestId = 'estate_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2,9);
    if (action === 'view') { latestView = requestId; loading = true; } else busy = true;
    const timer = setTimeout(() => {
      const request = pending.get(requestId); if (!request) return;
      pending.delete(requestId);
      if (action === 'view' && requestId !== latestView) return;
      loading = false; busy = false;
      notice = action === 'view' ? '영지 서버에 연결하지 못했습니다. 영지 모드 설치와 서버 상태를 확인해주세요.' : '구매 결과 확인이 지연되었습니다. 다시 구매하기 전에 상태를 새로고침해주세요.';
      if (action === 'view') connected = false;
      render();
      if (action !== 'view' && host) setTimeout(refresh,400);
    },7000);
    pending.set(requestId,{action,timer});
    const payload = {channel:CHANNEL,action,requestId,...extra};
    try {
      if (typeof window.webgui?.postToGame === 'function') window.webgui.postToGame(payload);
      else if (typeof window.cefQuery === 'function') window.cefQuery({request:JSON.stringify(payload),onSuccess:()=>{},onFailure:()=>fail(requestId,'게임에 영지 요청을 전달하지 못했습니다.')});
      else fail(requestId,'영지 기능은 영지 모드가 설치된 Minecraft 안에서 사용할 수 있습니다.');
    } catch (_) { fail(requestId,'영지 요청을 전달하지 못했습니다.'); }
    render();
  }
  function fail(id,message) {
    const request=pending.get(id);if(request){clearTimeout(request.timer);pending.delete(id);}
    loading=false;busy=false;notice=message;render();
  }
  function refresh() { if(host)send('view',center?{centerX:center.x,centerZ:center.z}:{}); }
  function receive(event) {
    const response=event.detail;
    if (!response || typeof response !== 'object') return;
    const request=pending.get(response.requestId);if(!request)return;
    clearTimeout(request.timer);pending.delete(response.requestId);
    if(request.action==='view' && response.requestId!==latestView)return;
    loading=false;
    if(request.action!=='view')busy=false;
    if(response.type==='error') {notice=response.message||'영지 요청이 거절되었습니다.';render();if(request.action!=='view')setTimeout(refresh,500);return;}
    if(response.type!=='snapshot'||!Array.isArray(response.cells))return;
    data=response;connected=true;center={x:response.centerX,z:response.centerZ};
    if(response.message){notice=response.message;tab='manage';selected={x:response.centerX,z:response.centerZ};}
    render();
  }
  window.addEventListener('webgui:'+CHANNEL,receive);
  function tabs() {
    return `<div class="estate-tabs"><button data-estate-tab="overview" class="${tab==='overview'?'active':''}">영지 현황</button><button data-estate-tab="manage" class="${tab==='manage'?'active':''}">영지관리</button><button data-estate-refresh class="estate-refresh" ${loading?'disabled':''}>${loading?'확인 중…':'새로고침'}</button></div>`;
  }
  function render() {
    if(!host)return;
    observer?.disconnect();observer=null;
    const ready=connected&&data;
    let html=tabs();
    html+=`<div class="estate-notice" role="status" ${notice?'':'hidden'}>${esc(notice)}</div>`;
    if(!ready){
      html+=`<div class="feature-panel estate-wait"><h2>${loading?'영지 서버 연결 중':'영지 정보를 불러와주세요'}</h2><p>청크 소유권은 Minecraft 서버에서 확인합니다. 서버 연결 전에는 생성과 구매가 비활성화됩니다.</p><button class="primary-button" data-estate-refresh ${loading?'disabled':''}>${loading?'응답 기다리는 중…':'서버 다시 확인'}</button></div>`;
    }else{
      html+=`<div class="estate-mode ${data.freeTestMode?'test-mode':'locked-mode'}">${data.freeTestMode?'재화 연동 전 · 무료 테스트 모드':'서버 재화 연동 대기 · 구매 잠김'}<span>오버월드 전용 · 1청크 = 16 × 16블록</span></div>`;
      html+=tab==='overview'?overview():management();
    }
    host.innerHTML=html;
    host.querySelectorAll('[data-estate-tab]').forEach(button=>button.onclick=()=>{tab=button.dataset.estateTab;render();if(tab==='manage'&&!data)refresh();});
    host.querySelectorAll('[data-estate-refresh]').forEach(button=>button.onclick=()=>{notice='';refresh();});
    host.querySelector('[data-estate-create]')?.addEventListener('click',()=>confirmPurchase('create',data.currentX,data.currentZ));
    host.querySelector('[data-estate-buy]')?.addEventListener('click',()=>{if(selected)confirmPurchase('buy',selected.x,selected.z);});
    host.querySelector('[data-estate-manage]')?.addEventListener('click',()=>{tab='manage';render();});
    host.querySelectorAll('[data-pan]').forEach(button=>button.onclick=()=>{
      if(loading)return;const [dx,dz]=button.dataset.pan.split(',').map(Number);center={x:Math.max(-1874998,Math.min(1874998,center.x+dx)),z:Math.max(-1874998,Math.min(1874998,center.z+dz))};refresh();
    });
    host.querySelector('[data-estate-home]')?.addEventListener('click',()=>{if(data.homeX!==undefined){center={x:data.homeX,z:data.homeZ};refresh();}});
    host.querySelector('[data-estate-location]')?.addEventListener('click',()=>{center={x:data.currentX,z:data.currentZ};refresh();});
    const canvas=host.querySelector('#estate-map');
    if(canvas){
      canvas.addEventListener('click',event=>{
        const rect=canvas.getBoundingClientRect(),n=data.radius*2+1;
        const x=Math.floor((event.clientX-rect.left)/rect.width*n),z=Math.floor((event.clientY-rect.top)/rect.height*n);
        if(x<0||z<0||x>=n||z>=n)return;
        selected={x:data.centerX-data.radius+x,z:data.centerZ-data.radius+z};render();
      });
      observer=new ResizeObserver(drawMap);observer.observe(canvas);drawMap();
    }
  }
  function overview() {
    const has=data.ownedCount>0;
    let reason='현재 서 있는 무주 청크를 첫 영지로 등록합니다.';
    if(!data.inOverworld)reason='오버월드로 이동한 뒤 영지를 생성해주세요.';
    else if(data.currentOwner)reason=data.currentMine?'현재 서 있는 청크는 내 영지입니다.':`현재 청크는 ${data.currentOwner}님의 소유입니다. 다른 청크로 이동해주세요.`;
    return `<div class="estate-overview"><div class="feature-panel estate-summary"><span class="feature-badge">MY ESTATE</span><h2>${has?'나의 영지가 준비되었습니다':'아직 소유한 영지가 없습니다'}</h2><div class="estate-total">${data.ownedCount}<span>개 청크</span></div><p>${has?'영지관리 지도에서 내 청크와 한 면 이상 맞닿은 청크를 선택해 확장할 수 있습니다.':'처음에는 본인이 서 있는 청크에서만 영지를 생성할 수 있습니다. 다른 소유주가 없는지 서버가 다시 확인합니다.'}</p><button class="primary-button" ${has?'data-estate-manage':'data-estate-create'} ${busy||!has&&(!data.purchaseEnabled||!data.inOverworld||data.currentOwner)?'disabled':''}>${busy?'처리 중…':has?'영지관리 열기':'영지 생성'}</button></div><div class="feature-panel estate-standing"><span class="feature-badge">CURRENT CHUNK</span><h2>${label(data.currentX,data.currentZ)}</h2><p>${esc(reason)}</p><dl><dt>차원</dt><dd>${data.inOverworld?'오버월드':'다른 차원'}</dd><dt>소유주</dt><dd>${esc(data.currentOwner||'없음')}</dd><dt>구매 비용</dt><dd>${data.freeTestMode?'무료 테스트':'재화 연동 대기'}</dd></dl></div></div>`;
  }
  function management() {
    const cell=selected?cellAt(selected.x,selected.z):null;
    let description='지도에서 청크를 선택해주세요.';
    if(cell)description=cell.mine?'이미 소유한 내 청크입니다.':cell.owner?`${cell.owner}님 소유입니다. 구매할 수 없습니다.`:data.ownedCount===0?'먼저 영지 현황에서 현재 위치의 영지를 생성해주세요.':cell.adjacent?'내 청크와 한 면 이상 닿아 구매할 수 있습니다.':'내 청크와 동서남북 중 한 면 이상 맞닿아야 합니다. 대각선은 제외됩니다.';
    const canBuy=cell&&!cell.owner&&cell.adjacent&&data.ownedCount>0&&data.purchaseEnabled&&data.inOverworld&&!busy;
    return `<div class="estate-management"><div class="estate-map-pane"><div class="estate-map-toolbar"><strong>오버월드 지도</strong><span>북쪽 ↑</span><button data-estate-home ${data.ownedCount===0?'disabled':''}>내 영지</button><button data-estate-location>내 위치</button></div><div class="estate-map-wrap"><canvas id="estate-map" aria-label="오버월드 청크별 영지 지도. 선택은 아래 청크 좌표 입력으로도 가능합니다."></canvas><div class="estate-pan"><button data-pan="0,-3" aria-label="지도 북쪽">↑</button><button data-pan="-3,0" aria-label="지도 서쪽">←</button><button data-pan="3,0" aria-label="지도 동쪽">→</button><button data-pan="0,3" aria-label="지도 남쪽">↓</button></div></div><div class="estate-legend"><span class="mine">내 영지</span><span class="other">다른 소유주</span><span class="available">확장 가능</span><span class="unmapped">미확인 지형</span></div><p class="estate-map-note">중심 청크 ${label(data.centerX,data.centerZ)} · 서버가 불러온 실제 지형을 표시합니다. 미확인 지형은 회색이며 지도 탐색으로 새 청크를 생성하지 않습니다.</p></div><aside class="feature-panel estate-selection"><span class="feature-badge">SELECTED CHUNK</span><h2>${selected?label(selected.x,selected.z):'청크 선택'}</h2><p>${esc(description)}</p>${cell?`<dl><dt>소유주</dt><dd>${esc(cell.owner||'없음')}</dd><dt>크기</dt><dd>16 × 16블록</dd><dt>구매 비용</dt><dd>${data.freeTestMode?'무료 테스트':'연동 대기'}</dd></dl>`:''}<button class="primary-button" data-estate-buy ${canBuy?'':'disabled'}>${busy?'처리 중…':'선택 청크 구매'}</button><div class="estate-coordinate-select"><label>청크 X<input type="number" id="estate-input-x" value="${selected?.x??data.centerX}" min="-1874998" max="1874998"></label><label>청크 Z<input type="number" id="estate-input-z" value="${selected?.z??data.centerZ}" min="-1874998" max="1874998"></label><button type="button" id="estate-select-coordinates">좌표 선택</button></div><p class="estate-selection-note">구매 직전에 서버가 소유권과 인접 조건을 다시 검사합니다.</p></aside></div>`;
  }
  // Keyboard-friendly alternative to selecting the canvas; coordinates are still validated server-side.
  document.addEventListener('click',event=>{
    if(event.target.id!=='estate-select-coordinates'||!host||!data)return;
    const x=Number(host.querySelector('#estate-input-x').value),z=Number(host.querySelector('#estate-input-z').value);
    if(!Number.isInteger(x)||!Number.isInteger(z)||Math.abs(x)>1874998||Math.abs(z)>1874998){notice='올바른 청크 좌표를 입력해주세요.';render();return;}
    selected={x,z};
    if(!cellAt(x,z)){center={x,z};refresh();}else render();
  });
  function confirmPurchase(action,x,z) {
    if(!host||busy)return;
    const dialog=document.createElement('dialog');dialog.className='estate-confirm';
    dialog.innerHTML=`<p class="eyebrow">${action==='create'?'CREATE ESTATE':'EXPAND ESTATE'}</p><h2>${action==='create'?'첫 영지를 생성할까요?':'이 청크를 구매할까요?'}</h2><p>오버월드 청크 ${label(x,z)}<br>재화 연동 전 무료 테스트입니다.<br>${action==='create'?'서버가 현재 서 있는 청크인지 다시 확인합니다.':'소유권과 내 영지에 닿는 면을 서버가 다시 확인합니다.'}</p><div class="estate-confirm-actions"><button class="back-button" data-cancel>취소</button><button class="primary-button" data-confirm>${action==='create'?'영지 생성 요청':'구매 요청'}</button></div>`;
    host.append(dialog);dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();dialog.addEventListener('close',()=>dialog.remove());
    dialog.querySelector('[data-confirm]').onclick=()=>{dialog.close();notice='';send(action,{x,z});};dialog.showModal();
  }
  function drawMap() {
    const canvas=host?.querySelector('#estate-map');if(!canvas||!data)return;
    const rect=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1,size=rect.width;
    canvas.width=Math.max(1,Math.round(size*ratio));canvas.height=Math.max(1,Math.round(size*ratio));
    const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);ctx.imageSmoothingEnabled=false;
    const n=data.radius*2+1,unit=size/n;
    for(const cell of data.cells){
      const ix=cell.x-(data.centerX-data.radius),iz=cell.z-(data.centerZ-data.radius),left=ix*unit,top=iz*unit;
      if(cell.colors?.length===16){for(let z=0;z<4;z++)for(let x=0;x<4;x++){ctx.fillStyle='#'+(cell.colors[z*4+x]>>>0).toString(16).padStart(6,'0').slice(-6);ctx.fillRect(left+x*unit/4,top+z*unit/4,unit/4+1,unit/4+1);}}
      else{ctx.fillStyle=(ix+iz)%2?'#23303b':'#293642';ctx.fillRect(left,top,unit,unit);}
      if(cell.owner){ctx.fillStyle=cell.mine?'#22e1d150':'#f060785a';ctx.fillRect(left,top,unit,unit);}
      ctx.strokeStyle=cell.mine?'#5ef4e3':cell.owner?'#ff8c9a':cell.adjacent?'#54e3e6aa':'#07131b70';ctx.lineWidth=cell.owner?2:1;ctx.strokeRect(left+.5,top+.5,unit-1,unit-1);
      if(selected?.x===cell.x&&selected?.z===cell.z){ctx.strokeStyle='#ffd46a';ctx.lineWidth=3;ctx.strokeRect(left+2,top+2,unit-4,unit-4);}
      if(data.inOverworld&&cell.x===data.currentX&&cell.z===data.currentZ){ctx.beginPath();ctx.arc(left+unit/2,top+unit/2,Math.max(3,unit*.09),0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle='#132331';ctx.lineWidth=2;ctx.stroke();}
    }
  }
  window.PocketmateEstates={
    mount(element){
      for(const request of pending.values())clearTimeout(request.timer);pending.clear();
      host=element;data=null;connected=false;loading=false;busy=false;selected=null;center=null;notice='';
      render();refresh();clearInterval(poll);poll=setInterval(()=>{if(host&&!loading&&!busy&&!document.hidden&&!host.querySelector('dialog[open]')&&!host.querySelector('input:focus'))refresh();},4000);
    },
    unmount(){host=null;observer?.disconnect();observer=null;clearInterval(poll);poll=null;},
    updateClient(){/* Server snapshots remain the sole ownership authority. */}
  };
})();
