(() => {
  'use strict';
  const categories=[['all','전체 상품','bag'],['adventure','모험 용품','compass'],['pokemon','포켓몬 용품','ball'],['building','건축 · 생활','home'],['style','꾸미기','spark']];
  let category='all',query='';
  window.PocketmateShop={mount(host,close){
    const icon=window.PocketmateIcons;
    host.innerHTML=`<header class="shop-heading"><div><span class="shop-eyebrow">POCKETMATE / MARKET</span><h1>상점</h1></div><div class="shop-heading-actions"><button data-go="home">${icon('arrow')} 홈으로</button><button data-shop-close aria-label="상점 닫고 게임으로">${icon('x')}</button></div></header><div class="shop-window"><aside class="shop-sidebar"><div class="shop-sidebar-title">카테고리</div><nav aria-label="상품 분류">${categories.map(([id,name,glyph])=>`<button data-shop-category="${id}" aria-pressed="${id===category}">${icon(glyph)}<span>${name}</span></button>`).join('')}</nav><div class="shop-sidebar-note">필요한 물건을 찾고<br>다음 모험을 준비하세요.</div></aside><main class="shop-main"><section class="shop-welcome"><span class="shop-eyebrow">YOUR NEXT ADVENTURE</span><h2>모험의 준비는 여기서.</h2><p>모험 용품부터 일상을 꾸미는 물건까지.</p>${icon('bag')}</section><div class="shop-toolbar"><div><h2 id="shop-category-title"></h2><span class="shop-count">등록 상품 0개</span></div><label class="shop-search"><span class="shop-search-label">상품 검색</span><input type="search" maxlength="80" placeholder="상품 이름으로 검색" autocomplete="off"></label></div><section class="shop-empty" aria-live="polite">${icon('bag')}<h3></h3><p></p></section><footer class="shop-status">상품 등록 준비 중 · 구매 기능은 상품과 결제 연결 후 열립니다.</footer></main></div>`;
    const input=host.querySelector('input');input.value=query;
    const render=()=>{host.querySelector('#shop-category-title').textContent=categories.find(c=>c[0]===category)[1];host.querySelectorAll('[data-shop-category]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.shopCategory===category)));host.querySelector('.shop-empty h3').textContent=query?'검색된 상품이 없습니다':'아직 등록된 상품이 없습니다';host.querySelector('.shop-empty p').textContent=query?'다른 검색어나 카테고리를 선택해 보세요.':'상품이 등록되면 이곳에서 확인할 수 있어요.';};
    host.querySelectorAll('[data-shop-category]').forEach(b=>b.onclick=()=>{category=b.dataset.shopCategory;render();});input.oninput=()=>{query=input.value.trim();render();};host.querySelector('[data-shop-close]').onclick=close;render();host.querySelector('[data-go]').focus({preventScroll:true});
  }};
})();
