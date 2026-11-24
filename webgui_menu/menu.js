(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const meta = {
    home: ['홈', 'PLAYER HUB', ''],
    warp: ['워프', 'WARP / DESTINATIONS', '이동할 목적지를 확인하세요.'],
    shop: ['상점', '03 / SUPPLY', '아이템과 거래 기능을 한곳에서 확인하세요.'],
    warehouse: ['창고', '03 / STORAGE', '보관한 물건을 확인하는 공간입니다.'],
    quests: ['임무', '04 / MISSIONS', '진행할 목표와 보상을 확인하세요.'],
    travel: ['마을 이동', '05 / FAST TRAVEL', '목적지를 선택하고 다음 지역으로 이동하세요.'],
    estate: ['영지관리', '06 / ESTATES', '현재 위치에서 영지를 만들고, 오버월드 지도로 소유 청크를 관리하세요.'],
    profile: ['프로필 꾸미기', 'MY PROFILE / COLLECTION', '보유한 아이콘·칭호·배너로 나만의 프로필카드를 꾸며보세요.'],
    settings: ['메뉴 설정', '07 / PREFERENCES', '플레이 허브의 표시 설정을 변경하세요.']
  };
  const icons = {warp:'warp', shop:'bag', quests:'flag', travel:'compass'};
  const icon = window.PocketmateIcons;
  let liveClient = null;
  let reducedMotion = false;
  try { reducedMotion = localStorage.getItem('pocketmate.reducedMotion') === 'true'; } catch (_) {}
  document.body.classList.toggle('reduce-motion', reducedMotion);
  const TEXT_MIN = 80, TEXT_MAX = 160, TEXT_STEP = 10;
  let textPercent = 100;
  try {
    const saved = Number(localStorage.getItem('pocketmate.textPercent'));
    if (Number.isFinite(saved) && saved >= TEXT_MIN && saved <= TEXT_MAX) textPercent = Math.round(saved / TEXT_STEP) * TEXT_STEP;
  } catch (_) {}
  function applyTextSize() {
    document.documentElement.style.setProperty('--text-scale', String(textPercent / 100));
    $('text-size-value').textContent = `${textPercent}%`;
    $('text-size-decrease').disabled = textPercent <= TEXT_MIN;
    $('text-size-increase').disabled = textPercent >= TEXT_MAX;
    document.querySelectorAll('[data-estate-text-value]').forEach(output=>output.textContent=`${textPercent}%`);
    document.querySelectorAll('[data-estate-text-size]').forEach(button=>button.disabled=Number(button.dataset.estateTextSize)<0?textPercent<=TEXT_MIN:textPercent>=TEXT_MAX);
  }
  function adjustTextSize(direction) {
    textPercent = Math.min(TEXT_MAX, Math.max(TEXT_MIN, textPercent + direction * TEXT_STEP));
    applyTextSize();
    try { localStorage.setItem('pocketmate.textPercent', String(textPercent)); } catch (_) {}
  }
  $('text-size-decrease').addEventListener('click', () => adjustTextSize(-1));
  $('text-size-increase').addEventListener('click', () => adjustTextSize(1));
  document.querySelectorAll('[data-estate-text-size]').forEach(button=>button.addEventListener('click',()=>adjustTextSize(Number(button.dataset.estateTextSize))));
  applyTextSize();

  const showInfo = (title, message) => {
    $('dialog-title').textContent = title;
    $('dialog-body').textContent = message;
    if (!$('info-dialog').open) $('info-dialog').showModal();
  };
  const notConnected = name => showInfo(name, '이 메뉴의 기본 화면이 준비되었어요.\n서버 기능을 연결하면 실제 정보를 확인하고 이용할 수 있어요.');
  function selectPage(page) {
    if(page==='travel'){window.PocketmateTravel.go();return;}
    window.PocketmateEstates?.unmount();
    window.PocketmateProfile?.unmount();
    window.PocketmateMissions?.unmount();
    $('estate-page').hidden=true;
    $('shop-page').hidden=true;
    if (!meta[page]) page = 'home';
    const [title, kicker, description] = meta[page];
    $('breadcrumb').textContent = title;
    document.querySelectorAll('[data-page]').forEach(button => {
      const selected = button.dataset.page === page;
      button.classList.toggle('selected', selected);
      if (selected) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
    });
    $('home-page').hidden = page !== 'home';
    $('feature-page').hidden = page === 'home';
    document.body.dataset.activePage=page;
    $('page-scroll').classList.toggle('missions-page', page === 'quests');
    $('page-scroll').classList.toggle('home-fixed', page === 'home');
    $('page-scroll').classList.toggle('profile-fixed-actions', page === 'profile');
    $('page-scroll').scrollTop = 0;
    if (page === 'home') return;
    if (page === 'shop') {
      $('shop-page').hidden=false;
      window.PocketmateShop.mount($('shop-page'),closeMenu);
      return;
    }
    if (page === 'estate') {
      $('estate-page').hidden=false;
      window.PocketmateEstates.mount($('estate-content'));
      $('estate-page').querySelector('[data-go="home"]').focus({preventScroll:true});
      return;
    }
    $('feature-title').textContent = title;
    $('feature-kicker').textContent = kicker;
    $('feature-description').textContent = description;
    const panel = $('feature-content');
    if (page === 'profile') {
      window.PocketmateProfile.mount(panel);
    } else if (page === 'quests') {
      window.PocketmateMissions.mount(panel);
    } else if (page === 'warehouse') {
      panel.innerHTML = `<div class="feature-panel"><span class="empty-symbol">${icon('vault')}</span><h2>창고를 준비하고 있어요</h2><p>창고 기능을 연결하면 보관한 물건을 이곳에서 확인할 수 있어요.</p></div>`;
    } else if (page === 'warp') {
      panel.innerHTML = `<div class="feature-panel"><span class="empty-symbol">${icon('warp')}</span><h2>워프 지점을 준비하고 있어요</h2><p>등록된 워프 지점이 생기면 이곳에서 목적지를 선택할 수 있어요.</p></div>`;
    } else if (page === 'settings') {
      panel.innerHTML = `<div class="feature-panel"><label class="setting-row" for="theme-select"><span><strong>화면 테마</strong><small>일반 메뉴·영지 관리소·상점에 함께 적용되며, 다음에도 선택이 유지돼요.</small></span><select class="theme-select" id="theme-select"><option value="dark">다크 모드</option><option value="light">라이트 모드</option></select></label><label class="setting-row"><span><strong>움직임 줄이기</strong><small>버튼과 상태 막대의 전환 효과를 줄여요.</small></span><input type="checkbox" id="motion-toggle" ${reducedMotion?'checked':''}></label><div class="setting-row"><span><strong>메뉴 열기</strong><small>Shift+F 연결 전의 기본 단축키예요.</small></span><span class="setting-value">F6</span></div><div class="setting-row"><span><strong>메뉴 닫기</strong><small>오른쪽 위 닫기 버튼으로도 돌아갈 수 있어요.</small></span><span class="setting-value">Esc</span></div></div>`;
      $('theme-select').value = window.PocketmateTheme.get();
      $('theme-select').addEventListener('change', event => window.PocketmateTheme.set(event.target.value));
      $('motion-toggle').addEventListener('change', event => {
        reducedMotion = event.target.checked;
        document.body.classList.toggle('reduce-motion', reducedMotion);
        try { localStorage.setItem('pocketmate.reducedMotion', String(reducedMotion)); } catch (_) {}
      });
    } else {
      const copy = ['아직 도착하지 않은 이야기','서버의 임무 기능을 연결하면 목표와 보상, 진행 상황을 볼 수 있어요. 지금은 수락할 수 있는 임무가 없어요.'];
      panel.innerHTML = `<div class="feature-panel"><span class="empty-symbol">${icon(icons[page])}</span><h2>${copy[0]}</h2><p>${copy[1]}</p><button class="primary-button" data-guide>메뉴 이용 안내 ${icon('arrow')}</button></div>`;
    }
  }
  document.addEventListener('click', event => {
    const go = event.target.closest('[data-go], [data-page]');
    if (go) { selectPage(go.dataset.go || go.dataset.page); return; }
    const tile = event.target.closest('[data-placeholder]');
    if (tile) { notConnected(tile.dataset.placeholder); return; }
    if (event.target.closest('[data-guide]')) showInfo('포켓메이트에 오신 걸 환영해요', '왼쪽 탭과 기능 타일로 워프, 상점, 임무와 영지관리 메뉴를 둘러보세요.\n\n현재는 메뉴의 기본 틀을 테스트하는 단계예요. 서버 기능이 필요한 항목은 연결 후 이용할 수 있어요.\n\nF6으로 메뉴를 열고 Esc로 게임으로 돌아갈 수 있어요.');
  });
  document.querySelector('.brand').addEventListener('click', event => { event.preventDefault(); selectPage('home'); });
  ['dialog-x','dialog-ok'].forEach(id => $(id).addEventListener('click', () => $('info-dialog').close()));
  $('info-dialog').addEventListener('click', event => { if (event.target === $('info-dialog')) { const r = event.target.getBoundingClientRect(); if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) event.target.close(); } });
  function closeMenu() {
    try {
      if (typeof window.webgui?.closeGui === 'function') { window.webgui.closeGui(); return; }
      if (typeof window.webgui?.postToGame === 'function') { window.webgui.postToGame({channel:'close'}); return; }
      if (typeof window.cefQuery === 'function') { window.cefQuery({request:JSON.stringify({channel:'close'}),onSuccess:()=>{},onFailure:()=>showInfo('게임으로 돌아가기','Esc 키를 눌러 메뉴를 닫아주세요.')}); return; }
    } catch (_) {}
    showInfo('메뉴 미리보기', '게임 안에서는 이 버튼으로 메뉴를 닫을 수 있어요.\n지금은 브라우저 미리보기 화면이에요.');
  }
  $('close-menu').addEventListener('click',closeMenu);
  $('close-estate').addEventListener('click',closeMenu);
  window.addEventListener('pocketmate:travel-result',event=>{
    if(event.detail?.success)closeMenu();
    else showInfo('마을 이동',event.detail?.message||'마을 이동을 확인해 주세요.');
  });
  function applyClient(client) {
    if (!client || typeof client.username !== 'string' || !client.username.trim()) return;
    liveClient = client;
    $('player-greeting').textContent = window.PocketmateProfile?.displayName?.()||client.username;
    $('player-name').textContent = window.PocketmateProfile?.displayName?.()||client.username;
    $('connection-label').textContent = client.server?.address ? '월드 연결됨' : '싱글플레이';
    $('connection-dot').classList.add('connected');
    const hp=Number(client.health), max=Number(client.maxHealth);
    const valid=Number.isFinite(hp)&&Number.isFinite(max)&&max>0;
    $('health-text').textContent = valid ? `${Math.max(0,hp).toFixed(0)} / ${max.toFixed(0)}` : '—';
    $('health-fill').style.width = valid ? `${Math.min(100,Math.max(0,hp/max*100))}%` : '0%';
    $('player-level').textContent = Number.isFinite(Number(client.xpLevel)) ? `Lv. ${Math.max(0,Math.floor(Number(client.xpLevel)))}` : '—';
    const dimension = typeof client.dimension === 'string' ? client.dimension : '';
    $('player-dimension').textContent = ({'minecraft:overworld':'오버월드','minecraft:the_nether':'네더','minecraft:the_end':'엔드'})[dimension] || (dimension ? dimension.split(':').pop().replace(/_/g,' ') : '—');
    const pos=client.pos;
    $('player-coordinates').textContent = pos && ['x','y','z'].every(k=>Number.isFinite(Number(pos[k]))) ? `X ${Math.floor(pos.x)}  ·  Y ${Math.floor(pos.y)}  ·  Z ${Math.floor(pos.z)}` : '현재 위치를 확인하고 있어요.';
  }
  window.addEventListener('webgui:client', event => applyClient(event.detail));
  applyClient(window.webgui?.client);
  $('date-label').textContent = new Intl.DateTimeFormat('ko-KR',{month:'long',day:'numeric',weekday:'short'}).format(new Date());
  // Extension point: register trusted server event handlers here when gameplay features are connected.
  // Feature modules own their server requests; navigation never modifies progress.
})();
