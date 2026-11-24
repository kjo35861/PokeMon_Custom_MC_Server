/* The single live profile stays outside both the hub and estate windows. */
(() => {
  const dock=document.getElementById('profile-card');
  let frame=0;
  function measure(){
    frame=0;
    document.body.classList.toggle('large-text',parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--text-scale'))>=1.3);
    const reserve=Math.ceil(dock.getBoundingClientRect().bottom)+10;
    if(document.documentElement.style.getPropertyValue('--profile-reserve')!==reserve+'px')document.documentElement.style.setProperty('--profile-reserve',reserve+'px');
  }
  const update=()=>{if(!frame)frame=requestAnimationFrame(measure);};
  new ResizeObserver(update).observe(dock);new MutationObserver(update).observe(document.documentElement,{attributes:true,attributeFilter:['style']});window.addEventListener('resize',update);measure();
})();
