'use strict';
/** @typedef {{title:string,level:number,startOffset:number,startLine:number,endOffset:number}} Heading */
/** @typedef {{path:string,project:string,sourcePath:string,syncedAt:string|null,mtime:number,text:string,headings:Heading[],resolved:{path:string,count:number}[],unresolved:{target:string,count:number}[]}} ProfileRecord */
/** @typedef {{id:string,kind:'profile'|'section',label:string,project:string,profileId:string,path:string,startLine:number,startOffset:number,endOffset:number,text:string,syncedAt:string|null,mtime:number}} GraphNode */
/** @typedef {{id:string,kind:'contains'|'link',source:string,target:string,count:number}} GraphEdge */
/** @typedef {{nodes:GraphNode[],edges:GraphEdge[],profiles:ProfileRecord[]}} Graph */
/** @typedef {{nodes:GraphNode[],edges:GraphEdge[],totalNodes:number,shownNodes:number,page:number,pageCount:number}} GraphPage */
/** @typedef {{status:'indexing'|'ready'|'stale'|'error',graph:Graph|null,message:string,revision:number}} IndexState */
/** @typedef {{sourceFolder:string,motion:boolean}} Settings */
function cleanProfile(text){return text.replace(/^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/,'').replace(/^> \[!info\] Perfil espelhado automaticamente\r?\n(?:>[^\n]*(?:\n|$))*/m,'').trim();}
/** @param {ProfileRecord[]} records @returns {Graph} */
function buildGraph(records){
 const profiles=records.slice().sort((a,b)=>a.path.localeCompare(b.path)),nodes=[],edges=[],profileIds=new Map();
 for(const r of profiles)profileIds.set(r.path,JSON.stringify(['profile',r.path]));
 for(const r of profiles){const profileId=profileIds.get(r.path),common={project:r.project,profileId,path:r.path,syncedAt:r.syncedAt,mtime:r.mtime};
  nodes.push({...common,id:profileId,kind:'profile',label:r.project,startLine:0,startOffset:0,endOffset:r.text.length,text:cleanProfile(r.text)});
  const headings=r.headings.slice().sort((a,b)=>a.startOffset-b.startOffset);
  for(let i=0;i<headings.length;i++){const hd=headings[i];if(!hd.title.trim())continue;const next=headings.slice(i+1).find(h=>h.level<=hd.level),end=next?next.startOffset:r.text.length,body=r.text.slice(hd.endOffset,end).trim();if(!body)continue;
   const id=JSON.stringify(['section',r.path,hd.startOffset,hd.title]);nodes.push({...common,id,kind:'section',label:hd.title,startLine:hd.startLine,startOffset:hd.startOffset,endOffset:end,text:body});edges.push({id:JSON.stringify(['contains',profileId,id]),kind:'contains',source:profileId,target:id,count:1});
  }
  for(const link of r.resolved){const target=profileIds.get(link.path);if(target&&target!==profileId)edges.push({id:JSON.stringify(['link',profileId,target]),kind:'link',source:profileId,target,count:link.count});}
 }
 return {nodes,edges,profiles};
}
/** @param {Graph} graph @param {{profileId:string|null,page:number}} selection @returns {GraphPage} */
function selectGraphPage(graph,selection,limit=500){
 limit=Math.max(2,Math.min(500,Math.floor(limit)||500));const root=graph.nodes.find(n=>n.kind==='profile'&&n.id===selection.profileId);let candidates,fixed=[];
 if(root){fixed=[root];candidates=graph.nodes.filter(n=>n.profileId===root.id&&n.kind==='section');}
 else candidates=graph.nodes.length>limit?graph.nodes.filter(n=>n.kind==='profile'):graph.nodes;
 const size=limit-fixed.length,pageCount=Math.max(1,Math.ceil(candidates.length/size)),page=Math.min(pageCount-1,Math.max(0,Math.floor(selection.page)||0));
 const nodes=fixed.concat(candidates.slice(page*size,(page+1)*size)),ids=new Set(nodes.map(n=>n.id));return {nodes,edges:graph.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)),totalNodes:graph.nodes.length,shownNodes:nodes.length,page,pageCount};
}
module.exports={buildGraph,selectGraphPage};
