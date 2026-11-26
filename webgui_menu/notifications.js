(() => {
 'use strict';
 let popup=null,timer=null;
 function close(){clearTimeout(timer);if(popup)popup.hidden=true;}
 function show(message,{error=false}={}){
  if(!message)return;
  if(!popup){
   popup=document.createElement('aside');popup.className='pm-notification';popup.hidden=true;
   const text=document.createElement('span'),button=document.createElement('button');
   text.className='pm-notification-text';button.type='button';button.textContent='×';button.setAttribute('aria-label','알림 닫기');button.onclick=close;
   popup.append(text,button);document.body.append(popup);
  }
  clearTimeout(timer);popup.dataset.error=String(error);popup.setAttribute('role',error?'alert':'status');popup.setAttribute('aria-live',error?'assertive':'polite');
  popup.querySelector('span').textContent=String(message);popup.hidden=false;
  timer=setTimeout(close,error?8000:4500);
 }
 window.PocketmateNotify={show,close};
})();
