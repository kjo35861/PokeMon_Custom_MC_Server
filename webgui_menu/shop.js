(() => {
 'use strict';
 const groups=[['바닐라',[['building','건축블럭','cube'],['colored','색깔블럭','palette'],['decoration','장식블럭','torch'],['minerals','광물','ore'],['crops','농작물','wheat']]],['포켓몬',[['balls','몬스터볼','ball'],['held','지니는 물건','charm'],['zcrystals','Z크리스탈','zgem'],['megastones','메가나이트','mega'],['gimmicks','기믹도구','gimmick']]]];
 const categoryGlyphs={"cube": "M12 2 21 7v10l-9 5-9-5V7zm0 10v10M3 7l9 5 9-5", "palette": "M4 4h7v7H4zm9 0h7v7h-7zM4 13h7v7H4zm9 0h7v7h-7z", "torch": "M9 12h6l-2 9h-2zm3-10c1 3 4 4 4 7a4 4 0 0 1-8 0c0-2 2-4 4-7Z", "ore": "m4 9 4-5h8l4 5-8 11zm0 0h16m-8-5-3 5 3 11 3-11z", "wheat": "M12 22V5m0 6C6 11 5 7 5 5c4 0 7 2 7 6Zm0 5c-6 0-7-4-7-6 4 0 7 2 7 6Zm0-5c6 0 7-4 7-6-4 0-7 2-7 6Zm0 5c6 0 7-4 7-6-4 0-7 2-7 6Z", "charm": "M12 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 0 6 6-6 7-6-7z", "zgem": "m12 2 7 4v12l-7 4-7-4V6zm-3 6h6l-6 8h6", "mega": "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm2 3-7 8h5l-2 6 7-8h-5z", "gimmick":"M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 4 4 6-4 6-4-6z","favorite": "m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z"};
 const categoryIcon=name=>categoryGlyphs[name]?`<svg class="pm-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${categoryGlyphs[name]}"/></svg>`:window.PocketmateIcons(name);
 const categories=[['favorites','즐겨찾기','favorite'],...groups.flatMap(g=>g[1])],esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money=n=>Number(n||0).toLocaleString('ko-KR')+'원',icon=n=>window.PocketmateIcons(n),icons=new Map();
 let shownFeedback='',saleCategories=new Set(['minerals','crops']);
 const saleEnabled=id=>id==='favorites'||saleCategories.has(id);
 const firstSale=()=>categories.find(([id])=>saleCategories.has(id))?.[0]||'favorites';
 let host=null,mode='buy',category='building',query='',page=0,data=null,pending=null,accepted='',feedback='',failed=false,closeMenu=null,poll=null,searchTimer=null,observer=null,loadedPage=-1,acceptedIds=new Set(),quoteHandler=null,opening=false;
 function clearPending(){if(pending)clearTimeout(pending.timer);pending=null;}
 function reset(){clearPending();data=null;page=0;loadedPage=-1;acceptedIds.clear();const main=host?.querySelector('.shop-main');if(main)main.scrollTop=0;render();request();}
 function more(){if(host&&data&&!pending&&!host.querySelector('dialog[open]')&&loadedPage+1<data.pages)request('view',{page:loadedPage+1});}
 function request(action='view',extra={}){
  if(!host||['trade','bulk','favorite'].includes(pending?.action))return;
  clearPending();const requestId='shop_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,9);
  const payload={channel:'pocketmate:shop',requestId,action,mode,category,page,query,...extra};
  pending={action,requestId,page:payload.page,timer:setTimeout(()=>{clearPending();if(quoteHandler){quoteHandler({type:'error',message:'서버 응답을 받지 못했습니다. 창을 닫고 다시 시도해주세요.'});return;}failed=true;feedback='상점 응답을 받지 못했습니다. 새 모드 적용 여부를 확인하고 새로고침해주세요.';render();},7000)};
  if(['trade','bulk','favorite'].includes(action)){feedback='거래를 처리하고 있습니다…';failed=false;render();}
  try{if(typeof window.webgui?.postToGame==='function')window.webgui.postToGame(payload);else if(typeof window.cefQuery==='function')window.cefQuery({request:JSON.stringify(payload),onSuccess:()=>{},onFailure:fail});else fail();}catch(_){fail();}
 }
 function fail(){clearPending();failed=true;feedback='상점 모드가 적용된 월드에 연결해주세요.';render();}
 function receive(event){
  const value=event.detail;if(!host||!pending||value?.requestId!==pending.requestId)return;
  const action=pending.action;clearPending();
  if(action==='quote'){const handler=quoteHandler;quoteHandler=null;if(value.type==='quote'&&data)Object.assign(data,{balance:value.balance});handler?.(value);return;}
  if(Array.isArray(value.saleCategories))saleCategories=new Set(value.saleCategories);
  if(value.type==='error'){failed=true;feedback=value.message||'거래를 처리하지 못했습니다.';render();return;}
  if(value.type==='status'){if(data&&value.priceVersion!==data.priceVersion){reset();return;}if(data){const changed=['buyPaused','sellPaused','maintenanceReason'].some(key=>data[key]!==value[key]);Object.assign(data,value,{type:'snapshot'});if(changed)render();else {const balance=host.querySelector('.shop-wallet strong');if(balance)balance.textContent=money(data.balance);}}return;}
  if(value.type!=='snapshot'||!Array.isArray(value.items)||!categories.some(c=>c[0]===value.category)||!['buy','sell'].includes(value.mode)||!Number.isSafeInteger(value.balance)||value.balance<0||typeof value.priceVersion!=='string'){failed=true;feedback='올바른 상점 정보를 받지 못했습니다.';render();return;}
  if(value.mode==='sell'&&!saleEnabled(value.category)){category=firstSale();reset();return;}
  if(data&&value.priceVersion!==data.priceVersion&&(value.page>0||['trade','bulk'].includes(action))){const message=value.message;reset();feedback=message||'';return;}
  if(opening){
   opening=false;
   if(value.favorites?.length&&category!=='favorites'){category='favorites';reset();return;}
  }
  if(action==='favorite'&&category==='favorites'){reset();return;}
  const previous=data?.items||[];
  if(value.page===0&&!['trade','bulk','favorite'].includes(action)){data=value;loadedPage=0;acceptedIds.clear();}
  else {const merged=new Map(previous.map(item=>[item.id,item]));value.items.forEach(item=>merged.set(item.id,item));data={...value,items:[...merged.values()]};loadedPage=Math.max(loadedPage,value.page);}
  acceptedIds.add(value.requestId);if(acceptedIds.size>128)acceptedIds.delete(acceptedIds.values().next().value);accepted=value.requestId;mode=value.mode;category=value.category;page=loadedPage;feedback=value.message||'';failed=false;render();
 }
 window.addEventListener('webgui:pocketmate:shop',receive);
 window.addEventListener('webgui:pocketmate:shop-assets',event=>{
  if(!host||!acceptedIds.has(event.detail?.requestId))return;
  for(const [id,url] of Object.entries(event.detail.icons||{}))if(typeof url==='string'&&/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(url)&&url.length<100000)icons.set(id,url);
  hydrate();
 });
 function hydrate(){host?.querySelectorAll('[data-shop-icon]').forEach(el=>{const src=icons.get(el.dataset.shopIcon);if(src&&el.firstElementChild?.getAttribute('src')!==src){el.innerHTML=`<img src="${src}" alt="" decoding="async">`;}});}
 let itemTextureIndex;
 function showItemTextures(){
  itemTextureIndex??=fetch('./shop-item-icons/index.json',{cache:'no-cache'})
   .then(response=>response.ok?response.json():{}).catch(()=>({}));
  itemTextureIndex.then(index=>{
   host?.querySelectorAll('[data-shop-ball],[data-shop-icon]').forEach(el=>{
    const filename=index[el.dataset.shopBall||el.dataset.shopIcon];
    if(typeof filename!=='string'||!/^(?:pixelmon|pocketmate(?:_mega)?)_[a-z0-9_]+\.png$/.test(filename))return;
    const src='./shop-item-icons/'+filename+(/^pocketmate_mega_mega_stone_5[4-8]\.png$/.test(filename)?'?v=restored':'');
    if(el.firstElementChild?.getAttribute('src')===src)return;
    const img=new Image();
    img.alt='';img.decoding='async';
    img.onload=()=>{el.replaceChildren(img);delete el.dataset.shopIcon;};
    img.setAttribute('src',src);
   });
  });
 }
 function choose(next){if(['trade','bulk','favorite'].includes(pending?.action))return;category=next;page=0;reset();}
 function render(){
  const noticeKey=String(failed)+feedback;if(feedback&&noticeKey!==shownFeedback){window.PocketmateNotify.show(feedback,{error:failed});shownFeedback=noticeKey;}else if(!feedback)shownFeedback='';
  if(!host)return;
  const busy=['trade','bulk','favorite'].includes(pending?.action),label=categories.find(c=>c[0]===category)[1],rows=data?.items||[];
  const searchFocused=host.querySelector('.shop-search input')===document.activeElement,selection=searchFocused?document.activeElement.selectionStart:null;
  const scroll=host.querySelector('.shop-main')?.scrollTop||0;observer?.disconnect();
  const layout=document.createElement('template');layout.innerHTML=`<header class="shop-heading"><div><span class="shop-eyebrow">POCKETMATE / MARKET</span><h1>상점</h1></div><div class="shop-heading-actions"><span class="shop-wallet">내 재화 <strong>${data?money(data.balance):'확인 중'}</strong></span><button data-go="home">${icon('arrow')} 홈으로</button><button data-shop-close aria-label="상점 닫고 게임으로">${icon('x')}</button></div></header><div class="shop-window"><aside class="shop-sidebar"><nav aria-label="상품 분류"><button class="shop-favorite-tab" data-shop-category="favorites" aria-pressed="${category==='favorites'}" ${busy?'disabled':''}>${categoryIcon('favorite')} <span>즐겨찾기</span></button>${groups.map(([group,list])=>`<div class="shop-category-group"><div class="shop-sidebar-title">카테고리 · ${group}</div>${list.map(([id,name,glyph])=>`<button data-shop-category="${id}" aria-pressed="${id===category}" ${busy||mode==='sell'&&!saleEnabled(id)?'disabled':''}>${categoryIcon(glyph)}<span>${name}</span></button>`).join('')}</div>`).join('')}</nav></aside><main class="shop-main"><div class="shop-trade-toolbar"><div class="shop-mode" role="group" aria-label="거래 종류"><button data-shop-mode="buy" aria-pressed="${mode==='buy'}" ${busy?'disabled':''}>구매</button><button data-shop-mode="sell" aria-pressed="${mode==='sell'}" ${busy?'disabled':''}>판매</button></div><p>${mode==='buy'?'아이템을 골라 수량을 선택하세요.':'판매할 아이템을 골라 수량을 선택하세요.'}</p><button data-shop-refresh ${busy?'disabled':''}>새로고침</button></div>${data&&(data.buyPaused||data.sellPaused)?`<section class="shop-maintenance" role="status"><strong>${data.buyPaused?'구매 일시정지':''}${data.buyPaused&&data.sellPaused?' · ':''}${data.sellPaused?'판매 일시정지':''}</strong><p>${esc(data.maintenanceReason||'관리자 점검으로 해당 거래를 잠시 이용할 수 없습니다.')}</p></section>`:''}<div class="shop-toolbar"><div><h2 id="shop-category-title">${esc(label)}</h2><span class="shop-count">${data?data.total+'종':'불러오는 중'}</span></div><label class="shop-search"><span class="shop-search-label">상품 검색</span><input type="search" maxlength="80" placeholder="아이템 이름 또는 ID" autocomplete="off" value="${esc(query)}" ${busy?'disabled':''}></label></div>${category==='gimmicks'?'<p class="shop-status">메가링과 Z링은 함께 해금됩니다. 다이맥스밴드와 테라스탈오브는 별도로 해금됩니다.</p>':''}${category==='favorites'?`<div class="shop-bulk"><button data-shop-bulk ${busy||query||!data||rows.length!==data.total||!(mode==='buy'?rows.length:rows.some(i=>i.owned>0))||(mode==='buy'?data.buyPaused:data.sellPaused)?'disabled':''}>${mode==='buy'?'모두 구매':'모두 판매'}</button></div>`:''}${rows.length?`<div class="shop-products">${rows.map(item=>{const price=mode==='buy'?item.buy:item.sell;return `<article class="shop-product"><button class="shop-star" data-shop-star="${esc(item.id)}" aria-label="${esc(item.name)} 즐겨찾기" aria-pressed="${data.favorites?.includes(item.id)??false}" ${busy?'disabled':''}>${data.favorites?.includes(item.id)?'★':'☆'}</button>${mode==='buy'&&item.description?`<button type="button" class="help-button shop-item-help" data-help="${esc(item.description)}" aria-label="${esc(item.name)} 설명">?</button>`:''}<div class="shop-item-art" ${item.ball?`data-shop-ball="${esc(item.id)}"`:`data-shop-icon="${esc(item.id)}"`}>${categoryIcon(categories.find(c=>c[0]===category)[2])}</div><div class="shop-item-copy"><h3>${esc(item.name)}</h3><small>${esc(item.id.replace('minecraft:',''))}</small><span>보유 ${item.unlock?(item.owned?'해금됨':'계정당 1회 해금'):Number(item.owned).toLocaleString()+'개'}</span></div><div class="shop-product-bottom"><strong>${money(price)}<small> / 개</small></strong><button class="primary-button" data-shop-item="${esc(item.id)}" ${busy||(mode==='buy'?data.buyPaused:data.sellPaused)||price<=0||item.unlock&&item.owned>0||mode==='sell'&&item.owned<1?'disabled':''}>${(mode==='buy'?data.buyPaused:data.sellPaused)?(mode==='buy'?'구매 중지':'판매 중지'):(mode==='buy'?'구매':'판매')}</button></div></article>`;}).join('')}</div>`:`<section class="shop-empty" aria-live="polite">${icon('bag')}<h3>${data?(query?'검색된 상품이 없습니다':'아직 등록된 상품이 없습니다'):'상품 정보를 불러오고 있습니다'}</h3><p>${data?(category==='balls'||category==='held'||category==='zcrystals'||category==='megastones'?'포켓몬 상품은 추후 추가됩니다.':query?'다른 이름이나 카테고리로 검색해 보세요.':'등록 상품을 확인해주세요.'):'서버에서 가격과 보유 수량을 확인합니다.'}</p></section>`}<footer class="shop-catalog-footer"><span>${data?.randomPrices?'주기별 변동 가격 적용':'고정 가격 적용'}</span><span>${rows.length} / ${data?.total||0}종</span></footer><div class="shop-load-more" aria-live="polite">${data&&loadedPage+1<data.pages?`<button data-shop-more>${failed?'다시 불러오기':'상품 더 불러오기'}</button>`:(data?'모든 상품을 확인했습니다.':'상품을 불러오는 중입니다.')}</div><p class="shop-status">판매는 가방·단축바의 일반 아이템만 집계합니다. 이름·인챈트 등 추가 정보가 있는 아이템은 제외됩니다.</p></main></div>`;
  const panel=host.querySelector('.shop-main');
  if(panel){
   const next=layout.content;
   host.querySelector('.shop-heading').replaceWith(next.querySelector('.shop-heading'));
   host.querySelector('.shop-sidebar').replaceWith(next.querySelector('.shop-sidebar'));
   panel.replaceChildren(...next.querySelector('.shop-main').childNodes);
  }else host.replaceChildren(layout.content);
  host.querySelector('[data-shop-close]').onclick=closeMenu;
  host.querySelectorAll('[data-shop-category]').forEach(b=>b.onclick=()=>choose(b.dataset.shopCategory));
  host.querySelectorAll('[data-shop-mode]').forEach(b=>b.onclick=()=>{if(busy)return;mode=b.dataset.shopMode;if(mode==='sell'&&!saleEnabled(category))category=firstSale();page=0;reset();});
  host.querySelector('[data-shop-refresh]').onclick=()=>reset();
  host.querySelector('input').oninput=e=>{query=e.target.value;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{page=0;reset();},300);};
  host.querySelector('[data-shop-more]')?.addEventListener('click',more);
  host.querySelectorAll('[data-shop-item]').forEach(b=>b.onclick=()=>confirm(rows.find(i=>i.id===b.dataset.shopItem)));
  const main=host.querySelector('.shop-main');main.scrollTop=scroll;const sentinel=host.querySelector('.shop-load-more');observer=new IntersectionObserver(entries=>{if(!failed&&entries.some(e=>e.isIntersecting))more();},{root:main,rootMargin:'300px'});if(sentinel)observer.observe(sentinel);if(category==='favorites'&&!failed)queueMicrotask(more);
  host.querySelectorAll('[data-shop-star]').forEach(b=>b.onclick=()=>request('favorite',{item:b.dataset.shopStar,page:Math.floor(rows.findIndex(i=>i.id===b.dataset.shopStar)/24)}));
  host.querySelector('[data-shop-bulk]')?.addEventListener('click',()=>confirmBulk(rows));
  hydrate();showItemTextures();if(searchFocused){const input=host.querySelector('.shop-search input');input.focus({preventScroll:true});try{input.setSelectionRange(selection,selection);}catch(_){}}
 }
 function confirmBulk(rows){
  const buy=mode==='buy',version=data.priceVersion;
  const unlocks=new Set();
  const items=[];
  for(const item of [...rows].sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0)){
   if(buy&&item.unlock&&(item.owned||unlocks.has(item.unlockGroup)))continue;
   const quantity=buy?1:Math.min(2304,item.owned);
   if(quantity<=0)continue;
   if(buy&&item.unlockGroup)unlocks.add(item.unlockGroup);
   items.push({...item,quantity});
  }
  const reviewed=items.map(item=>item.id+'='+item.quantity).sort().join(',');
  const total=items.reduce((sum,item)=>sum+item.quantity*(buy?item.buy:item.sell),0);
  const dialog=document.createElement('dialog');
  dialog.className='shop-trade-dialog';
  dialog.innerHTML=`<h2>${buy?'즐겨찾기 모두 구매':'즐겨찾기 모두 판매'}</h2><p>${buy?'구매 가능한 품목을 1개씩 구매합니다.':'판매 가능한 품목의 일반 아이템을 전량 판매합니다.'}</p><ul class="shop-bulk-items">${items.map(item=>`<li>${esc(item.name)} × ${item.quantity}</li>`).join('')}</ul><p class="shop-trade-total">총 ${money(total)}</p><div class="estate-confirm-actions"><button data-cancel>취소</button><button class="primary-button" data-confirm>거래 확정</button></div>`;
  clearPending();
  host.append(dialog);
  dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();
  dialog.querySelector('[data-confirm]').onclick=()=>{dialog.close();request('bulk',{reviewed,priceVersion:version,page:0});};
  dialog.addEventListener('close',()=>{dialog.remove();more();},{once:true});
  dialog.showModal();
 }
 function confirm(item){
  if(!item||!data||['trade','bulk','favorite'].includes(pending?.action))return;
  clearPending();const actionMode=mode,itemPage=Math.floor(data.items.findIndex(i=>i.id===item.id)/24);
  let quote=null;
  const dialog=document.createElement('dialog');dialog.className='shop-trade-dialog';dialog.innerHTML=`<h2>${esc(item.name)} ${actionMode==='buy'?'구매':'판매'}</h2>${actionMode==='buy'&&item.description?`<p class="shop-description-text">${esc(item.description)}</p>`:''}<p data-quote-status role="status">서버에서 가능한 수량을 확인하고 있습니다…</p><label class="estate-field">수량<input type="number" min="1" max="2304" step="1" value="1" inputmode="numeric"></label><div class="shop-quantity-presets">${[1,16,64].map(n=>`<button data-shop-qty="${n}" disabled>${n}개</button>`).join('')}<button data-shop-max disabled>MAX</button></div><p class="shop-trade-total" aria-live="polite"></p><p>${actionMode==='buy'?'MAX: 기존 스택의 남은 공간과 빈 슬롯, 현재 잔액을 기준으로 구매 가능한 최대 수량을 선택합니다.':'MAX: 가방·단축바에 있는 판매 가능한 일반 아이템 전량을 선택합니다.'}</p><div class="estate-confirm-actions"><button class="back-button" data-shop-cancel>취소</button><button class="primary-button" data-shop-confirm disabled>${actionMode==='buy'?'구매 확정':'판매 확정'}</button></div>`;
  host.append(dialog);const input=dialog.querySelector('input'),submit=dialog.querySelector('[data-shop-confirm]'),max=dialog.querySelector('[data-shop-max]');
  const update=()=>{const n=Number(input.value),valid=quote&&Number.isSafeInteger(n)&&n>=1&&n<=quote.maxQuantity;dialog.querySelector('.shop-trade-total').textContent=quote?(valid?`총 ${money(n*quote.unitPrice)}`:`거래 가능 수량: ${quote.maxQuantity.toLocaleString()}개`):'';submit.disabled=!valid;};
  input.oninput=update;dialog.querySelectorAll('[data-shop-qty]').forEach(b=>b.onclick=()=>{input.value=b.dataset.shopQty;update();});max.onclick=()=>{if(quote){input.value=quote.maxQuantity;update();}};
  dialog.querySelector('[data-shop-cancel]').onclick=()=>dialog.close();submit.onclick=()=>{if(submit.disabled)return;const quantity=Number(input.value),version=quote.priceVersion;dialog.close();request('trade',{item:item.id,quantity,priceVersion:version,page:itemPage});};
  dialog.addEventListener('close',()=>{quoteHandler=null;if(pending?.action==='quote')clearPending();dialog.remove();},{once:true});dialog.showModal();input.focus();
  quoteHandler=value=>{if(!dialog.open)return;const status=dialog.querySelector('[data-quote-status]');if(value.type!=='quote'||value.item!==item.id||value.mode!==actionMode||!Number.isSafeInteger(value.maxQuantity)||value.maxQuantity<0||value.maxQuantity>2304||!Number.isSafeInteger(value.unitPrice)||value.unitPrice<1||typeof value.priceVersion!=='string'){status.textContent=value.message||'수량 정보를 확인하지 못했습니다.';return;}quote=value;input.max=quote.maxQuantity;status.textContent=`개당 ${money(quote.unitPrice)} · 보유 ${quote.owned}개 · 최대 ${quote.maxQuantity}개`+(quote.maxQuantity===0?' · 공간·잔액 또는 판매 가능한 수량이 부족합니다.':'');max.disabled=quote.maxQuantity===0;dialog.querySelectorAll('[data-shop-qty]').forEach(b=>b.disabled=Number(b.dataset.shopQty)>quote.maxQuantity);update();};
  request('quote',{item:item.id});
 }
 window.PocketmateShop={mount(element,close){this.unmount();host=element;closeMenu=close;opening=true;category=mode==='sell'?firstSale():'building';query='';page=0;loadedPage=-1;data=null;feedback='';failed=false;render();request();poll=setInterval(()=>{if(host&&!document.hidden&&!host.querySelector('dialog[open]')&&!pending)request('status');},5000);},unmount(){host?.querySelector('dialog')?.close();clearPending();clearInterval(poll);clearTimeout(searchTimer);observer?.disconnect();quoteHandler=null;host=null;data=null;loadedPage=-1;acceptedIds.clear();accepted='';}};
})();
