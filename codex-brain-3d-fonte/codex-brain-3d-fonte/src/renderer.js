'use strict';
const {layoutNodes,fitPositions,projectPoint}=require('./scene');
function createRenderer(canvas,{onSelect,reducedMotion=false}){
 const doc=canvas.ownerDocument,win=doc.defaultView,ctx=canvas.getContext('2d'),camera={yaw:-.15,pitch:.14,zoom:1};
 let page={nodes:[],edges:[]},positions=new Map(),points=[],selected=null,paused=reducedMotion,visible=true,intersected=true,disposed=false,frame=null,last=0,clock=0,drag=null,moved=false;
 let width=600,height=480,palette;
 const listeners=[];function listen(el,name,fn){el.addEventListener(name,fn);listeners.push(()=>el.removeEventListener(name,fn));}
 function colors(){const style=win.getComputedStyle(canvas),color=k=>style.getPropertyValue(k).trim()||style.color;palette={text:color('--text-normal'),muted:color('--text-muted'),bg:color('--background-primary'),line:color('--background-modifier-border'),nodes:['--color-cyan','--color-purple','--color-orange','--color-green'].map(color)};}
 function draw(){if(!ctx||disposed||!visible)return;const dpr=Math.min(2,win.devicePixelRatio||1);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);if(!palette)colors();
  points=page.nodes.map(n=>({...projectPoint(positions.get(n.id)||[0,0,0],camera,{width,height}),node:n})).filter(p=>p.visible);const byId=new Map(points.map(p=>[p.node.id,p]));
  for(let i=0;i<page.edges.length;i++){const e=page.edges[i],a=byId.get(e.source),b=byId.get(e.target);if(!a||!b)continue;const active=e.source===selected||e.target===selected;ctx.globalAlpha=active?.72:.32;ctx.strokeStyle=active?palette.text:palette.line;ctx.lineWidth=active?1.1:.7;ctx.setLineDash(e.kind==='contains'?[3,4]:[]);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.setLineDash([]);
   if(!paused&&(active||i%7===0)){const t=(clock*.25+i*.17)%1;ctx.globalAlpha=.75;ctx.fillStyle=palette.text;ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,1.5,0,Math.PI*2);ctx.fill();}
  }
  const roots=page.nodes.filter(n=>n.kind==='profile').map(n=>n.id).sort(),colorFor=n=>palette.nodes[Math.max(0,roots.indexOf(n.profileId))%palette.nodes.length];
  for(const p of points.slice().sort((a,b)=>b.depth-a.depth)){const n=p.node,r=(n.kind==='profile'?5:2.7)*p.k,isSelected=n.id===selected;ctx.globalAlpha=1;
   if(n.kind==='profile'||isSelected){ctx.globalAlpha=.13;ctx.fillStyle=colorFor(n);ctx.beginPath();ctx.arc(p.x,p.y,r*3.7,0,Math.PI*2);ctx.fill();}
   ctx.globalAlpha=isSelected||n.kind==='profile'?1:.8;ctx.fillStyle=colorFor(n);ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fill();if(isSelected){ctx.strokeStyle=palette.text;ctx.globalAlpha=.9;ctx.lineWidth=1;ctx.beginPath();ctx.arc(p.x,p.y,r+4,0,Math.PI*2);ctx.stroke();}
  }
  const boxes=[];for(const p of points.slice().sort((a,b)=>Number(b.node.id===selected)-Number(a.node.id===selected)||Number(b.node.kind==='profile')-Number(a.node.kind==='profile')||a.depth-b.depth)){
   const n=p.node,important=n.id===selected||n.kind==='profile';ctx.font=(important?'500 ':'400 ')+'12px system-ui';const label=n.label.length>48?n.label.slice(0,45)+'…':n.label,tw=ctx.measureText(label).width;let x=p.x+10,y=p.y+4;if(x+tw>width-6)x=p.x-tw-10;const box=[x-3,y-13,x+tw+3,y+5];if(box[0]<3||box[1]<3||box[2]>width-3||box[3]>height-3)continue;if(boxes.some(b=>box[0]<b[2]&&box[2]>b[0]&&box[1]<b[3]&&box[3]>b[1]))continue;boxes.push(box);ctx.globalAlpha=important?1:.72;ctx.fillStyle=palette.bg;ctx.fillRect(box[0],box[1],tw+6,18);ctx.fillStyle=important?palette.text:palette.muted;ctx.fillText(label,x,y);
  }ctx.globalAlpha=1;
 }
 function animating(){return ctx&&!disposed&&!paused&&visible&&intersected&&!doc.hidden&&page.nodes.length>0;}
 function sync(){if(animating()){if(frame===null)frame=win.requestAnimationFrame(tick);}else if(frame!==null){win.cancelAnimationFrame(frame);frame=null;last=0;}}
 function tick(t){frame=null;if(!animating())return;const dt=last?Math.min(.05,(t-last)/1000):0;last=t;if(!drag){camera.yaw+=dt*.04;clock+=dt;}draw();sync();}
 function resize(){width=canvas.clientWidth||600;height=canvas.clientHeight||480;const dpr=Math.min(2,win.devicePixelRatio||1);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);draw();}
 listen(canvas,'pointerdown',e=>{drag={x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY};moved=false;canvas.setPointerCapture(e.pointerId);});
 listen(canvas,'pointermove',e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;moved=moved||Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)>4;camera.yaw+=dx*.006;camera.pitch=Math.max(-1.2,Math.min(1.2,camera.pitch+dy*.006));drag={...drag,x:e.clientX,y:e.clientY};draw();});
 listen(canvas,'pointerup',e=>{if(!moved&&drag){const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top,hit=points.map(p=>({id:p.node.id,d:Math.hypot(p.x-x,p.y-y)})).sort((a,b)=>a.d-b.d)[0];if(hit&&hit.d<24)onSelect(hit.id);}drag=null;});listen(canvas,'pointercancel',()=>{drag=null;});
 listen(doc,'visibilitychange',sync);
 const resizeObserver=new win.ResizeObserver(resize);resizeObserver.observe(canvas);
 const themeObserver=new win.MutationObserver(()=>{colors();draw();});themeObserver.observe(doc.body,{attributes:true,attributeFilter:['class','style']});
 const intersection=win.IntersectionObserver?new win.IntersectionObserver(entries=>{intersected=entries.some(e=>e.isIntersecting);draw();sync();}):null;intersection?.observe(canvas);
 colors();resize();
 return {
  setPage(value){page=value;positions=fitPositions(layoutNodes(page.nodes));draw();sync();},
  setSelection(id){selected=id;draw();},setPaused(value){paused=value;draw();sync();},setVisible(value){visible=value;if(value)resize();sync();},
  rotate(dx,dy){camera.yaw+=dx;camera.pitch=Math.max(-1.2,Math.min(1.2,camera.pitch+dy));draw();},zoom(delta){camera.zoom=Math.max(.5,Math.min(4,camera.zoom+delta));draw();},
  dispose(){if(disposed)return;disposed=true;sync();listeners.forEach(f=>f());resizeObserver.disconnect();themeObserver.disconnect();intersection?.disconnect();}
 };
}
module.exports={createRenderer};
