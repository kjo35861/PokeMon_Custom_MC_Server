/* A viewport-positioned help bubble stays outside the sidebar's scroll clipping. */
(() => {
  'use strict';
  const bubble=document.createElement('div');
  bubble.id='pocketmate-help-tooltip';bubble.className='help-tooltip';bubble.role='tooltip';bubble.hidden=true;
  document.body.append(bubble);
  let active=null;
  function hide(){
    if(active)active.removeAttribute('aria-describedby');
    active=null;bubble.hidden=true;
  }
  function show(button){
    if(active!==button)hide();
    active=button;bubble.textContent=button.dataset.help;
    button.setAttribute('aria-describedby',bubble.id);bubble.hidden=false;
    const rect=button.getBoundingClientRect(),box=bubble.getBoundingClientRect(),gap=10;
    const left=Math.max(gap,Math.min(window.innerWidth-box.width-gap,rect.right-box.width));
    let top=rect.bottom+8;
    if(top+box.height>window.innerHeight-gap)top=rect.top-box.height-8;
    bubble.style.left=Math.round(left)+'px';bubble.style.top=Math.round(Math.max(gap,top))+'px';
  }
  document.addEventListener('pointerover',event=>{const button=event.target.closest('[data-help]');if(button)show(button);});
  document.addEventListener('pointerout',event=>{
    if(active?.contains(event.target)&&!active.contains(event.relatedTarget)&&document.activeElement!==active)hide();
  });
  document.addEventListener('focusin',event=>{const button=event.target.closest('[data-help]');if(button)show(button);else hide();});
  document.addEventListener('focusout',event=>{if(event.target===active)hide();});
  document.addEventListener('click',event=>{const button=event.target.closest('[data-help]');if(button)show(button);else hide();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&active){event.stopPropagation();hide();}},true);
  window.addEventListener('resize',hide);
  document.addEventListener('scroll',event=>{if(event.target!==bubble)hide();},true);
  window.PocketmateHelp={hide};
})();
