(() => {
  'use strict';
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const categories=['채집 · 벌목 · 채굴','포켓몬 전투','포켓몬 포획','농사 · 낚시 · 제작','탐험 · 육성'];
  const rules='임무를 받은 이후의 행동만 집계합니다.\n설치한 원목·광석 재채굴은 제외합니다.\n서로 다른 유형으로 5개를 배정합니다.\n매일 오전 6시(한국시간)에 초기화하며 재접속·서버 재시작으로 초기화되지 않습니다.\n무료 교체는 하루 전체 임무 중 1회이며, 미완료 임무만 같은 슬롯의 다른 유형으로 바꿀 수 있습니다.\n픽셀몬 연동 시 PvP·소환·출처 불명 포켓몬은 집계하지 않습니다.';
  const symbols=['leaf','target','ball','bag','compass'];
  let host=null,data=null,pending=null,poll=null,ticker=null,feedback='',failed=false,confirmId=null;
  const icon=name=>window.PocketmateIcons?.(name)||'';
  function countdown(){
    const output=host?.querySelector('[data-mission-reset]');if(!output||!data)return;
    const seconds=Math.max(0,Math.ceil((data.missions.resetAt-Date.now())/1000));
    const h=Math.floor(seconds/3600),m=Math.floor(seconds%3600/60),s=seconds%60;
    output.textContent=`${h}시간 ${String(m).padStart(2,'0')}분 ${String(s).padStart(2,'0')}초 후 초기화`;
  }
  function request(action,taskId){
    if(!host||pending)return;
    const requestId='mission_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,8);
    const payload={channel:'pocketmate:missions',action,requestId};
    if(action==='claim'||action==='reroll'){payload.taskId=taskId;payload.date=data?.missions.date;}
    pending={requestId,action,timer:setTimeout(()=>error('임무 서버 응답을 확인하지 못했습니다. 다시 시도해주세요.'),7000)};
    if(action==='claim'||action==='reroll'){feedback=action==='reroll'?'새 임무로 교체하고 있습니다.':'보상 수령을 확인하고 있습니다.';failed=false;render();}
    try{
      if(typeof window.webgui?.postToGame==='function')window.webgui.postToGame(payload);
      else if(typeof window.cefQuery==='function')window.cefQuery({request:JSON.stringify(payload),onSuccess:()=>{},onFailure:()=>error('게임 서버에 연결하면 일일 임무를 확인할 수 있습니다.')});
      else error('게임 서버에 연결하면 일일 임무를 확인할 수 있습니다.');
    }catch(_){error('임무 서버에 연결하지 못했습니다.');}
  }
  function error(message){if(pending)clearTimeout(pending.timer);pending=null;feedback=message;failed=true;render();}
  function valid(value){
    return value?.type==='snapshot'&&typeof value.pokemonReady==='boolean'&&typeof value.missions?.date==='string'&&Number.isFinite(value.missions.resetAt)&&typeof value.missions.finalClaimed==='boolean'&&Number.isInteger(value.missions.rerollsRemaining)&&value.missions.rerollsRemaining>=0&&value.missions.rerollsRemaining<=1&&Array.isArray(value.missions.tasks)&&value.missions.tasks.length===5&&value.missions.tasks.every((t,i)=>t.slot===i&&typeof t.id==='string'&&typeof t.name==='string'&&typeof t.description==='string'&&Number.isInteger(t.progress)&&Number.isInteger(t.target)&&t.target>0&&t.progress>=0&&t.progress<=t.target&&typeof t.claimed==='boolean');
  }
  window.addEventListener('webgui:pocketmate:missions',event=>{
    const value=event.detail;if(!host||!pending||value?.requestId!==pending.requestId)return;
    const action=pending.action;clearTimeout(pending.timer);pending=null;
    if(value.type==='error'){error(value.message||'임무 정보를 확인하지 못했습니다.');if(action==='claim'||action==='reroll')setTimeout(()=>request('view'),350);return;}
    if(!valid(value)){error('올바른 임무 응답을 받지 못했습니다.');return;}
    data=value;feedback=value.message||'';failed=false;render();
  });
  function render(){
    if(!host)return;
    window.PocketmateHelp?.hide();
    const focused=host.contains(document.activeElement)?document.activeElement?.dataset.missionClaim:null;
    if(!data){host.innerHTML=`<div class="mission-empty"><p role="status">${esc(feedback||'오늘의 임무를 불러오고 있습니다.')}</p><button class="primary-button" data-mission-retry>다시 불러오기</button></div>`;host.querySelector('button').onclick=()=>request('view');return;}
    const view=data.missions,done=view.tasks.filter(t=>t.progress>=t.target).length;
    host.innerHTML=`<section class="missions" aria-label="일일 임무"><header class="mission-summary"><div><span class="mission-day">${esc(view.date)} · 일일 임무</span><strong>오늘의 임무 <span>${done} / 5</span></strong><span class="mission-reroll-quota">오늘 무료 교체 ${view.rerollsRemaining} / 1회 남음 <button class="mission-rules-help" data-help="${esc(rules)}" aria-label="임무 집계 및 무료 교체 규칙">?</button></span></div><div class="mission-reset"><span>매일 오전 6시 · 한국시간</span><span data-mission-reset></span></div></header>${data.pokemonReady?'':'<p class="mission-connection">포켓몬 전투·포획 임무는 픽셀몬 서버 연결 후 진행할 수 있습니다.</p>'}<div class="mission-list">${view.tasks.map(t=>{
      const complete=t.progress>=t.target,waiting=!data.pokemonReady&&(t.slot===1||t.slot===2),status=t.claimed?'수령 완료':complete?'완료':waiting?'연결 대기':'진행 중';
      return `<article class="mission-card ${complete?'is-complete':''}"><span class="mission-symbol">${icon(symbols[t.slot])}</span><div class="mission-copy"><div class="mission-category">${esc(categories[t.slot])}<span>${status}</span></div><h2>${esc(t.name)}</h2><p tabindex="0" data-help="${esc(t.description)}">${esc(t.description.replace(/^종류에 상관없이 /,'').replace(/^돌·심층암·화강암·섬록암·안산암 /,'돌 계열 ').replace(/^도보·수영·탑승으로 총 /,'총 '))}</p><div class="mission-progress" role="progressbar" aria-label="${esc(t.name)} 진행도" aria-valuenow="${t.progress}" aria-valuemin="0" aria-valuemax="${t.target}"><span style="width:${Math.min(100,t.progress/t.target*100)}%"></span></div><span class="mission-count">${t.progress.toLocaleString()} / ${t.target.toLocaleString()}</span></div><div class="mission-actions"><button class="primary-button mission-claim" data-mission-claim="${esc(t.id)}" ${pending||!complete||t.claimed?'disabled':''}>${t.claimed?icon('check')+' 수령 완료':'보상 수령'}</button><button class="mission-reroll" data-mission-reroll="${esc(t.id)}" aria-label="${esc(t.name)} 무료 교체" ${pending||complete||t.claimed||view.rerollsRemaining===0?'disabled':''}>무료 교체</button></div></article>`;
    }).join('')}</div><section class="mission-final" aria-label="전체 완료 보상"><span class="mission-symbol">${icon('spark')}</span><div><span class="mission-category">ALL CLEAR</span><h2>오늘의 모든 임무 완료</h2><p>5개 임무를 모두 완료하면 추가 보상을 받을 수 있습니다.</p></div><button class="primary-button" data-mission-claim="final" ${pending||done!==5||view.finalClaimed?'disabled':''}>${view.finalClaimed?'최종 보상 수령 완료':'최종 보상 수령'}</button></section><p class="mission-reward-note">보상 구성은 준비 중입니다. 수령 버튼을 누르면 수령 기록만 저장되며, 아직 아이템이나 재화는 지급되지 않습니다.</p><p class="mission-feedback" role="status" data-error="${failed}">${esc(feedback)}</p><dialog class="mission-reroll-dialog" aria-labelledby="mission-reroll-title"><h2 id="mission-reroll-title">이 임무를 교체할까요?</h2><p>같은 슬롯의 다른 임무로 교체합니다. 기존 진행도는 사라지며, 새 임무는 교체 후 행동부터 집계됩니다.</p><p>무료 교체는 하루 전체 임무 중 1회 사용할 수 있습니다.</p><div><button data-reroll-cancel>취소</button><button class="primary-button" data-reroll-confirm>무료 교체하기</button></div></dialog></section>`;
    host.querySelectorAll('[data-mission-claim]').forEach(b=>b.onclick=()=>request('claim',b.dataset.missionClaim));
    const dialog=host.querySelector('.mission-reroll-dialog');
    host.querySelectorAll('[data-mission-reroll]').forEach(b=>b.onclick=()=>{if(pending)return;confirmId=b.dataset.missionReroll;dialog.showModal();});
    dialog.addEventListener('close',()=>{confirmId=null;});
    host.querySelector('[data-reroll-cancel]').onclick=()=>{dialog.close();confirmId=null;};
    host.querySelector('[data-reroll-confirm]').onclick=()=>{const id=confirmId;dialog.close();confirmId=null;if(id)request('reroll',id);};
    if(focused){const b=[...host.querySelectorAll('[data-mission-claim]')].find(b=>b.dataset.missionClaim===focused);if(b&&!b.disabled)b.focus({preventScroll:true});}
    countdown();
  }
  window.PocketmateMissions={mount(element){this.unmount();host=element;data=null;feedback='';failed=false;render();request('view');poll=setInterval(()=>{if(!document.hidden&&!confirmId)request('view');},5000);ticker=setInterval(countdown,1000);},unmount(){host?.querySelector('.mission-reroll-dialog')?.close();confirmId=null;if(pending)clearTimeout(pending.timer);pending=null;clearInterval(poll);clearInterval(ticker);host=null;data=null;}};
})();
