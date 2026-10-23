'use strict';
function hash(text){let n=2166136261;for(let i=0;i<text.length;i++)n=Math.imul(n^text.charCodeAt(i),16777619);return n>>>0;}
function layoutNodes(nodes){
 const result=new Map(),profiles=nodes.filter(n=>n.kind==='profile').sort((a,b)=>a.id.localeCompare(b.id));
 profiles.forEach((p,i)=>{const angle=i*2.399963,spread=profiles.length===1?0:.6+Math.sqrt(i+1)*.43,center=[Math.cos(angle)*spread,Math.sin(angle)*spread*.76,Math.sin(i*1.7)*.45];result.set(p.id,center);
  const children=nodes.filter(n=>n.profileId===p.id&&n.kind==='section').sort((a,b)=>a.id.localeCompare(b.id));children.forEach((n,j)=>{const a=j*2.399963,r=.35+.45*Math.sqrt((j+1)/children.length),z=(hash(n.id)%1000/1000-.5)*.9;result.set(n.id,[center[0]+Math.cos(a)*r,center[1]+Math.sin(a)*r*.83,center[2]+z]);});
 });return new Map([...result].sort((a,b)=>a[0].localeCompare(b[0])));
}
function fitPositions(positions){const radius=Math.max(1.6,...[...positions.values()].map(p=>Math.hypot(...p))),scale=1.6/radius;return new Map([...positions].map(([id,p])=>[id,p.map(x=>x*scale)]));}
function projectPoint(point,camera,{width,height}){const cy=Math.cos(camera.yaw),sy=Math.sin(camera.yaw),cp=Math.cos(camera.pitch),sp=Math.sin(camera.pitch),x=point[0]*cy+point[2]*sy,z=-point[0]*sy+point[2]*cy,y=point[1]*cp-z*sp,depth=point[1]*sp+z*cp,k=depth<=-4.9?0:5/(5+depth),s=Math.min(width/5,height/4)*camera.zoom;return {x:width/2+x*s*k,y:height/2-y*s*k,depth,k,visible:depth>-4.9};}
module.exports={layoutNodes,fitPositions,projectPoint};
