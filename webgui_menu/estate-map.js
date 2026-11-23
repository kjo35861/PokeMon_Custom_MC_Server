(() => {
  'use strict';
  window.PocketmateMap={create(pane,callbacks){
    const canvas=pane.querySelector('canvas'),ctx=canvas.getContext('2d'),tiles=new Map(),cells=new Map();
    const portraits=new Map();
    function portrait(url){
      if(!url)return null;if(portraits.has(url))return portraits.get(url);
      const img=new Image();img.onload=draw;img.src=url;portraits.set(url,img);
      if(portraits.size>16)portraits.delete(portraits.keys().next().value);return img;
    }
    let data=null,selected=[],cx=0,cz=0,scale=32,w=1,h=1,initialized=false,pointer=null,hover=null;
    let frame=0,timer=null,destroyed=false,grid=true,claims=true,status='connecting',message='Xaero 지형 연결 중';
    const key=(x,z)=>x+':'+z,limit=v=>Math.max(-1874998,Math.min(1874998,v));
    const screen=(x,z)=>({x:w/2+(x-cx)*scale,y:h/2+(z-cz)*scale});
    const world=p=>({x:cx+(p.x-w/2)/scale,z:cz+(p.y-h/2)/scale});
    const point=e=>{const r=canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};};
    const viewport=()=>({centerX:Math.floor(cx),centerZ:Math.floor(cz),radius:Math.max(2,Math.min(48,Math.ceil(Math.max(w,h)/scale/2)+2))});
    function draw(){if(!frame)frame=requestAnimationFrame(()=>{frame=0;if(!destroyed)paint();});}
    function changed(){clearTimeout(timer);timer=setTimeout(()=>callbacks.onViewport(viewport()),360);draw();}
    function setView(x,z){cx=x+.5;cz=z+.5;changed();}
    function zoom(factor,p={x:w/2,y:h/2}){
      const before=world(p),next=Math.max(32,Math.max(w,h)/95,Math.min(224,scale*factor));
      if(Math.abs(next-scale)<.01)return;scale=next;cx=limit(before.x-(p.x-w/2)/scale);cz=limit(before.z-(p.y-h/2)/scale);changed();
    }
    canvas.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(-e.deltaY*.0015),point(e));},{passive:false});
    canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;const p=point(e);pointer={id:e.pointerId,start:p,last:p,moved:false};canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');});
    canvas.addEventListener('pointermove',e=>{
      const p=point(e),v=world(p);hover={x:Math.floor(v.x),z:Math.floor(v.z),px:p.x,py:p.y};
      if(pointer){if(Math.hypot(p.x-pointer.start.x,p.y-pointer.start.y)>4)pointer.moved=true;if(pointer.moved){cx=limit(cx-(p.x-pointer.last.x)/scale);cz=limit(cz-(p.y-pointer.last.y)/scale);}pointer.last=p;}draw();
    });
    canvas.addEventListener('pointerup',e=>{if(!pointer||pointer.id!==e.pointerId)return;const moved=pointer.moved,p=point(e);pointer=null;canvas.classList.remove('dragging');if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);if(moved)changed();else{const v=world(p);callbacks.onSelect({x:Math.floor(v.x),z:Math.floor(v.z)});}});
    canvas.addEventListener('pointercancel',()=>{pointer=null;canvas.classList.remove('dragging');changed();});
    canvas.addEventListener('pointerleave',()=>{hover=null;draw();});
    pane.querySelector('[data-map-zoom-in]').onclick=()=>zoom(1.35);
    pane.querySelector('[data-map-zoom-out]').onclick=()=>zoom(1/1.35);
    pane.querySelector('[data-estate-location]').onclick=()=>{if(data)setView(data.currentX,data.currentZ);};
    pane.querySelector('[data-estate-home]').onclick=()=>{if(data?.homeX!==undefined)setView(data.homeX,data.homeZ);};
    function paint(){
      const dpr=window.devicePixelRatio||1,light=document.documentElement.dataset.theme==='light';
      const colors=light?{empty:'#e3e9df',hatch:'#526b5420',mine:'#24705b',other:'#a54059',available:'#24705b88',selection:'#885b0d',hover:'#26392fcc',tooltip:'#fcfdf5f5',text:'#26392f'}:{empty:'#101a20',hatch:'#bbcbd00c',mine:'#6ee8da',other:'#ee849e',available:'#b3ecd454',selection:'#ffcd66',hover:'#ffffffaa',tooltip:'#0c151ef2',text:'#e1ebed'};
      if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
      ctx.setTransform(dpr,0,0,dpr,0,0);ctx.imageSmoothingEnabled=false;ctx.fillStyle=colors.empty;ctx.fillRect(0,0,w,h);
      ctx.strokeStyle=colors.hatch;ctx.lineWidth=1;ctx.beginPath();for(let x=-h;x<w;x+=9){ctx.moveTo(x,0);ctx.lineTo(x+h,h);}ctx.stroke();
      for(const tile of tiles.values())if(tile.ready){const p=screen(tile.x*4,tile.z*4);if(p.x<w&&p.y<h&&p.x+4*scale>0&&p.y+4*scale>0)ctx.drawImage(tile.image,p.x,p.y,4*scale+.2,4*scale+.2);}
      if(grid&&scale>=36){
        ctx.strokeStyle='#07100e30';ctx.lineWidth=1;ctx.beginPath();
        for(let x=Math.floor(cx-w/scale/2);x<=Math.ceil(cx+w/scale/2);x++){const p=screen(x,0);ctx.moveTo(Math.round(p.x)+.5,0);ctx.lineTo(Math.round(p.x)+.5,h);}
        for(let z=Math.floor(cz-h/scale/2);z<=Math.ceil(cz+h/scale/2);z++){const p=screen(0,z);ctx.moveTo(0,Math.round(p.y)+.5);ctx.lineTo(w,Math.round(p.y)+.5);}ctx.stroke();
      }
      if(claims)for(const c of cells.values()){
        if(!c.owner&&!c.adjacent)continue;const p=screen(c.x,c.z);
        if(c.owner){
          ctx.fillStyle=c.mine?'#62d9c51d':'#e3779225';ctx.fillRect(p.x,p.y,scale,scale);ctx.strokeStyle=c.mine?colors.mine:colors.other;ctx.lineWidth=2;ctx.beginPath();
          const same=(x,z)=>{const n=cells.get(key(x,z));return n?.owner===c.owner&&n?.mine===c.mine;};
          if(!same(c.x,c.z-1)){ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+scale,p.y);}if(!same(c.x+1,c.z)){ctx.moveTo(p.x+scale,p.y);ctx.lineTo(p.x+scale,p.y+scale);}
          if(!same(c.x,c.z+1)){ctx.moveTo(p.x,p.y+scale);ctx.lineTo(p.x+scale,p.y+scale);}if(!same(c.x-1,c.z)){ctx.moveTo(p.x,p.y);ctx.lineTo(p.x,p.y+scale);}ctx.stroke();
        }else{ctx.strokeStyle=colors.available;ctx.setLineDash([3,4]);ctx.lineWidth=1;ctx.strokeRect(p.x+2,p.y+2,scale-4,scale-4);ctx.setLineDash([]);}
      }
      for(const selection of selected){const p=screen(selection.x,selection.z);ctx.fillStyle='#ffcd6621';ctx.fillRect(p.x,p.y,scale,scale);ctx.strokeStyle=colors.selection;ctx.lineWidth=2.5;ctx.strokeRect(p.x+1,p.y+1,scale-2,scale-2);}
      if(hover&&!pointer){
        const p=screen(hover.x,hover.z);ctx.strokeStyle=colors.hover;ctx.lineWidth=1;ctx.strokeRect(p.x+1,p.y+1,scale-2,scale-2);
        const c=cells.get(key(hover.x,hover.z)),text=`청크 · ${c?.owner?(c.mine?'내 영지':c.owner+'님의 영지'):c?'소유주 없음':'소유권 확인 중'}`;
        ctx.font='12px NanumSquareRound';const tw=ctx.measureText(text).width+20,tx=Math.min(w-tw-9,Math.max(9,hover.px+14)),ty=Math.max(54,Math.min(h-54,hover.py-38));ctx.fillStyle=colors.tooltip;ctx.fillRect(tx,ty,tw,29);ctx.fillStyle=colors.text;ctx.fillText(text,tx+10,ty+19);
      }
      if(data?.inOverworld){
        const person=window.PocketmatePeople?.remember({id:data.playerId,name:data.playerName,appearance:data.appearance});
        const face=portrait(window.PocketmatePeople?.avatarUrl(person)),banner=portrait(person?.appearance.bannerImage);
        const p=screen((data.playerX??data.currentX*16+8)/16,(data.playerZ??data.currentZ*16+8)/16);
        if(p.x>-20&&p.x<w+20&&p.y>-20&&p.y<h+20){
          ctx.shadowColor='#000a';ctx.shadowBlur=10;ctx.fillStyle='#14232b';ctx.beginPath();ctx.arc(p.x,p.y,15,0,2*Math.PI);ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle='#f8f7ea';ctx.lineWidth=2;ctx.stroke();
          if(face?.complete&&face.naturalWidth){ctx.save();ctx.beginPath();ctx.arc(p.x,p.y,13,0,2*Math.PI);ctx.clip();const size=person?.appearance.icon==='skin'?26:42;ctx.drawImage(face,p.x-size/2,p.y-size/2,size,size);ctx.restore();}
          else{ctx.fillStyle='#f5efda';ctx.font='bold 13px NanumSquareRound';ctx.textAlign='center';ctx.fillText((data.playerName||'P').slice(0,1),p.x,p.y+5);}
          ctx.font='11px NanumSquareRound';ctx.textAlign='center';const text=(data.playerName||'플레이어')+' (나)',tw=ctx.measureText(text).width+16;
          if(banner?.complete&&banner.naturalWidth){ctx.drawImage(banner,p.x-tw/2,p.y+20,tw,23);ctx.fillStyle='#101a22cc';}else ctx.fillStyle='#101a22ee';
          ctx.fillRect(p.x-tw/2,p.y+20,tw,23);ctx.fillStyle='#f7f5ec';ctx.fillText(text,p.x,p.y+36);ctx.textAlign='left';
        }
      }
      const barWidth=Math.min(256,w*.38);
      const unit=[128,64,32,16].find(blocks=>blocks/16*scale<=barWidth)||16;
      pane.querySelector('.map-scale-line').style.width=unit/16*scale+'px';pane.querySelector('.map-scale-label').textContent=unit+' 블록';
      pane.querySelector('.map-position').textContent='영토 지도';pane.querySelector('.map-zoom-value').textContent=Math.round(scale/64*100)+'%';
      const source=pane.querySelector('.map-source');source.textContent=message;source.dataset.state=status;
    }
    window.addEventListener('pocketmate:themechange',draw);
    window.addEventListener('pocketmate:peoplechange',draw);
    const observer=new ResizeObserver(()=>{const r=canvas.getBoundingClientRect();if(!r.width||!r.height)return;const nw=Math.max(1,r.width),nh=Math.max(1,r.height);if(Math.abs(nw-w)<.5&&Math.abs(nh-h)<.5)return;w=nw;h=nh;scale=Math.max(32,Math.max(w,h)/95,scale);draw();if(initialized)changed();});observer.observe(canvas);
    return {
      update(snapshot,selection){data=snapshot;selected=selection;cells.clear();for(const c of data.cells)cells.set(key(c.x,c.z),c);if(!initialized){cx=data.centerX+.5;cz=data.centerZ+.5;initialized=true;}draw();},
      receive(event){
        if(event.type==='status'){status=event.state;message=event.message;draw();return;}
        if(event.type!=='tile'||event.source!=='xaero'||event.blocks!==64||typeof event.png!=='string'||event.png.length>30000)return;
        const tile={x:event.tileX,z:event.tileZ,image:new Image(),ready:false},k=key(tile.x,tile.z);tiles.set(k,tile);
        tile.image.onload=()=>{if(tiles.get(k)!==tile||destroyed)return;tile.ready=true;status='ready';message='Xaero 월드맵 · 실제 지형';draw();};tile.image.src='data:image/png;base64,'+event.png;
        if(tiles.size>1024)tiles.delete(tiles.keys().next().value);
      },setView,viewport,
      options(value){grid=value.grid;claims=value.claims;draw();},isInteracting:()=>Boolean(pointer),diagnostics:()=>({tiles:[...tiles.values()].filter(t=>t.ready).length,status,scale,cx,cz,visibleBlocksX:w/scale*16,visibleBlocksZ:h/scale*16,radius:viewport().radius}),
      destroy(){destroyed=true;window.removeEventListener('pocketmate:themechange',draw);window.removeEventListener('pocketmate:peoplechange',draw);observer.disconnect();cancelAnimationFrame(frame);clearTimeout(timer);tiles.clear();portraits.clear();}
    };
  }};
})();
