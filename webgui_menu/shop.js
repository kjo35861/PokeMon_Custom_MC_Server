(() => {
 'use strict';
 const groups=[['바닐라',[['building','건축블럭','home'],['colored','색깔블럭','spark'],['decoration','장식블럭','leaf'],['minerals','광물','vault'],['crops','농작물','leaf']]],['포켓몬',[['balls','몬스터볼','ball'],['held','지니는 물건','bag'],['zcrystals','Z크리스탈','spark'],['megastones','메가나이트','spark']]]];
 const categories=groups.flatMap(g=>g[1]),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money=n=>Number(n||0).toLocaleString('ko-KR')+'원',icon=n=>window.PocketmateIcons(n),icons=new Map();
 let host=null,mode='buy',category='building',query='',page=0,data=null,pending=null,accepted='',feedback='',failed=false,closeMenu=null,poll=null,searchTimer=null;
 function clearPending(){if(pending)clearTimeout(pending.timer);pending=null;}
 function request(action='view',extra={}){
  if(!host||pending?.action==='trade')return;
  clearPending();const requestId='shop_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,9);
  const payload={channel:'pocketmate:shop',requestId,action,mode,category,page,query,...extra};
  pending={action,requestId,timer:setTimeout(()=>{clearPending();failed=true;feedback='상점 응답을 받지 못했습니다. 새 모드 적용 여부를 확인하고 새로고침해주세요.';render();},7000)};
  if(action==='trade'){feedback='거래를 처리하고 있습니다…';failed=false;render();}
  try{if(typeof window.webgui?.postToGame==='function')window.webgui.postToGame(payload);else if(typeof window.cefQuery==='function')window.cefQuery({request:JSON.stringify(payload),onSuccess:()=>{},onFailure:fail});else fail();}catch(_){fail();}
 }
 function fail(){clearPending();failed=true;feedback='상점 모드가 적용된 월드에 연결해주세요.';render();}
 function receive(event){
  const value=event.detail;if(!host||!pending||value?.requestId!==pending.requestId)return;
  clearPending();
  if(value.type==='error'){failed=true;feedback=value.message||'거래를 처리하지 못했습니다.';render();return;}
  if(value.type!=='snapshot'||!Array.isArray(value.items)||!categories.some(c=>c[0]===value.category)||!['buy','sell'].includes(value.mode)||!Number.isSafeInteger(value.balance)||value.balance<0||typeof value.priceVersion!=='string'){failed=true;feedback='올바른 상점 정보를 받지 못했습니다.';render();return;}
  data=value;accepted=value.requestId;mode=value.mode;category=value.category;page=value.page;feedback=value.message||'';failed=false;render();
 }
 window.addEventListener('webgui:pocketmate:shop',receive);
 window.addEventListener('webgui:pocketmate:shop-assets',event=>{
  if(!host||event.detail?.requestId!==accepted)return;
  for(const [id,url] of Object.entries(event.detail.icons||{}))if(typeof url==='string'&&/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(url)&&url.length<23000)icons.set(id,url);
  hydrate();if(searchFocused){const input=host.querySelector('.shop-search input');input.focus({preventScroll:true});try{input.setSelectionRange(selection,selection);}catch(_){}}
 });
 function hydrate(){host?.querySelectorAll('[data-shop-icon]').forEach(el=>{const src=icons.get(el.dataset.shopIcon);if(src){el.innerHTML=`<img src="${src}" alt="" decoding="async">`;}});}
 function choose(next){if(pending?.action==='trade')return;category=next;page=0;data=null;render();request();}
 function render(){
  if(!host)return;
  const busy=pending?.action==='trade',label=categories.find(c=>c[0]===category)[1],rows=data?.items||[];
  const searchFocused=host.querySelector('.shop-search input')===document.activeElement,selection=searchFocused?document.activeElement.selectionStart:null;
  host.innerHTML=`<header class="shop-heading"><div><span class="shop-eyebrow">POCKETMATE / MARKET</span><h1>상점</h1></div><div class="shop-heading-actions"><span class="shop-wallet">내 재화 <strong>${data?money(data.balance):'확인 중'}</strong></span><button data-go="home">${icon('arrow')} 홈으로</button><button data-shop-close aria-label="상점 닫고 게임으로">${icon('x')}</button></div></header><div class="shop-window"><aside class="shop-sidebar"><nav aria-label="상품 분류">${groups.map(([group,list])=>`<div class="shop-category-group"><div class="shop-sidebar-title">카테고리 · ${group}</div>${list.map(([id,name,glyph])=>`<button data-shop-category="${id}" aria-pressed="${id===category}" ${busy||mode==='sell'&&!['minerals','crops'].includes(id)?'disabled':''}>${icon(glyph)}<span>${name}</span></button>`).join('')}</div>`).join('')}</nav></aside><main class="shop-main"><div class="shop-trade-toolbar"><div class="shop-mode" role="group" aria-label="거래 종류"><button data-shop-mode="buy" aria-pressed="${mode==='buy'}" ${busy?'disabled':''}>구매</button><button data-shop-mode="sell" aria-pressed="${mode==='sell'}" ${busy?'disabled':''}>판매</button></div><p>${mode==='buy'?'아이템을 골라 수량을 선택하세요.':'광물과 농작물만 판매할 수 있습니다.'}</p><button data-shop-refresh ${busy?'disabled':''}>새로고침</button></div><div class="shop-toolbar"><div><h2 id="shop-category-title">${esc(label)}</h2><span class="shop-count">${data?data.total+'종':'불러오는 중'}</span></div><label class="shop-search"><span class="shop-search-label">상품 검색</span><input type="search" maxlength="80" placeholder="아이템 이름 또는 ID" autocomplete="off" value="${esc(query)}" ${busy?'disabled':''}></label></div><p class="shop-feedback" role="status" data-error="${failed}">${esc(feedback)}</p>${rows.length?`<div class="shop-products">${rows.map(item=>{const price=mode==='buy'?item.buy:item.sell;return `<article class="shop-product"><div class="shop-item-art" data-shop-icon="${esc(item.id)}">${icon(categories.find(c=>c[0]===category)[2])}</div><div class="shop-item-copy"><h3>${esc(item.name)}</h3><small>${esc(item.id.replace('minecraft:',''))}</small><span>보유 ${Number(item.owned).toLocaleString()}개</span></div><div class="shop-product-bottom"><strong>${money(price)}<small> / 개</small></strong><button class="primary-button" data-shop-item="${esc(item.id)}" ${busy||price<=0||mode==='sell'&&item.owned<1?'disabled':''}>${mode==='buy'?'구매':'판매'}</button></div></article>`;}).join('')}</div>`:`<section class="shop-empty" aria-live="polite">${icon('bag')}<h3>${data?(query?'검색된 상품이 없습니다':'아직 등록된 상품이 없습니다'):'상품 정보를 불러오고 있습니다'}</h3><p>${data?(category==='balls'||category==='held'||category==='zcrystals'||category==='megastones'?'포켓몬 상품은 추후 추가됩니다.':query?'다른 이름이나 카테고리로 검색해 보세요.':'등록 상품을 확인해주세요.'):'서버에서 가격과 보유 수량을 확인합니다.'}</p></section>`}<footer class="shop-catalog-footer"><span>${data?.randomPrices?'주기별 변동 가격 적용':'고정 가격 적용'}</span><div class="shop-pagination"><button data-shop-page="-1" aria-label="이전 상품 페이지" ${busy||!data||page<=0?'disabled':''}>${icon('up')}</button><span>${data?page+1:1} / ${data?.pages||1}</span><button data-shop-page="1" aria-label="다음 상품 페이지" ${busy||!data||page+1>=data.pages?'disabled':''}>${icon('down')}</button></div></footer><p class="shop-status">판매는 가방·단축바의 일반 아이템만 집계합니다. 이름·인챈트 등 추가 정보가 있는 아이템은 제외됩니다.</p></main></div>`;
  host.querySelector('[data-shop-close]').onclick=closeMenu;
  host.querySelectorAll('[data-shop-category]').forEach(b=>b.onclick=()=>choose(b.dataset.shopCategory));
  host.querySelectorAll('[data-shop-mode]').forEach(b=>b.onclick=()=>{if(busy)return;mode=b.dataset.shopMode;if(mode==='sell'&&!['minerals','crops'].includes(category))category='minerals';page=0;data=null;render();request();});
  host.querySelector('[data-shop-refresh]').onclick=()=>request();
  host.querySelector('input').oninput=e=>{query=e.target.value;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{page=0;request();},300);};
  host.querySelectorAll('[data-shop-page]').forEach(b=>b.onclick=()=>{page+=Number(b.dataset.shopPage);request();});
  host.querySelectorAll('[data-shop-item]').forEach(b=>b.onclick=()=>confirm(rows.find(i=>i.id===b.dataset.shopItem)));
  hydrate();if(searchFocused){const input=host.querySelector('.shop-search input');input.focus({preventScroll:true});try{input.setSelectionRange(selection,selection);}catch(_){}}
 }
 function confirm(item){
  if(!item||!data||pending?.action==='trade')return;
  const price=mode==='buy'?item.buy:item.sell,version=data.priceVersion,actionMode=mode;
  const dialog=document.createElement('dialog');dialog.className='shop-trade-dialog';dialog.innerHTML=`<h2>${esc(item.name)} ${actionMode==='buy'?'구매':'판매'}</h2><p>개당 ${money(price)} · 보유 ${item.owned}개</p><label class="estate-field">수량<input type="number" min="1" max="2304" step="1" value="1" inputmode="numeric"></label><div class="shop-quantity-presets">${[1,16,64].map(n=>`<button data-shop-qty="${n}">${n}개</button>`).join('')}</div><p class="shop-trade-total" aria-live="polite"></p><p>최신 가격·보유 수량·인벤토리 공간은 서버에서 다시 확인합니다.</p><div class="estate-confirm-actions"><button class="back-button" data-shop-cancel>취소</button><button class="primary-button" data-shop-confirm>${actionMode==='buy'?'구매 확정':'판매 확정'}</button></div>`;
  host.append(dialog);const input=dialog.querySelector('input'),submit=dialog.querySelector('[data-shop-confirm]');
  const update=()=>{const n=Number(input.value),valid=Number.isInteger(n)&&n>=1&&n<=2304,total=valid?n*price:0;dialog.querySelector('.shop-trade-total').textContent=valid?`총 ${money(total)}`:'1~2,304개의 정수 수량을 입력하세요.';submit.disabled=!valid||actionMode==='buy'&&total>data.balance||actionMode==='sell'&&n>item.owned;};
  input.oninput=update;dialog.querySelectorAll('[data-shop-qty]').forEach(b=>b.onclick=()=>{input.value=b.dataset.shopQty;update();});dialog.querySelector('[data-shop-cancel]').onclick=()=>dialog.close();submit.onclick=()=>{if(submit.disabled)return;const quantity=Number(input.value);dialog.close();request('trade',{item:item.id,quantity,priceVersion:version});};dialog.addEventListener('close',()=>dialog.remove(),{once:true});update();dialog.showModal();input.focus();
 }
 window.PocketmateShop={mount(element,close){this.unmount();host=element;closeMenu=close;data=null;feedback='';failed=false;render();request();poll=setInterval(()=>{if(host&&!document.hidden&&!host.querySelector('dialog[open]')&&!host.querySelector('input:focus')&&!pending)request();},15000);},unmount(){host?.querySelector('dialog')?.close();clearPending();clearInterval(poll);clearTimeout(searchTimer);host=null;data=null;accepted='';}};
})();
