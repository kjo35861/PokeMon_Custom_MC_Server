/* Ask the server for our own estate's home; the browser never supplies a destination. */
(() => {
  'use strict';
  let pending=null;
  function finish(success,message){
    if(!pending)return;
    clearTimeout(pending.timer);pending=null;
    window.dispatchEvent(new CustomEvent('pocketmate:travel-result',{detail:{success,message}}));
  }
  window.PocketmateTravel={go(){
    if(pending)return;
    const requestId='travel_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,8);
    pending={requestId,timer:setTimeout(()=>finish(false,'마을 이동 결과 확인이 지연되었습니다. 현재 위치와 서버 상태를 확인해 주세요.'),10000)};
    const payload={channel:'pocketmate:estate',action:'teleportHome',requestId};
    const fail=()=>finish(false,'마을 이동은 영지 모드가 연결된 게임 안에서 사용할 수 있습니다.');
    try{
      if(typeof window.webgui?.postToGame==='function')window.webgui.postToGame(payload);
      else if(typeof window.cefQuery==='function')window.cefQuery({request:JSON.stringify(payload),onSuccess:()=>{},onFailure:fail});
      else fail();
    }catch(_){fail();}
  }};
  window.addEventListener('webgui:pocketmate:estate',event=>{
    const value=event.detail;
    if(!pending||value?.requestId!==pending.requestId)return;
    if(value.type==='travel')finish(true,value.message||'영지 홈으로 이동했습니다.');
    else if(value.type==='error')finish(false,value.message||'마을로 이동하지 못했습니다.');
  });
})();
