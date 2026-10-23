'use strict';
const {ItemView}=require('obsidian');
const {buildGraph,selectGraphPage}=require('./model');
const {createRenderer}=require('./renderer');
async function openOrigin(app,node,readLatest,isCurrent=()=>true){
 const file=app.vault.getAbstractFileByPath(node.path);
 if(!file||file.extension!=='md')return {opened:false,message:'A nota de origem não existe mais. Atualize o mapa.'};
 let line=0;
 if(node.kind==='section'){
  const latest=await readLatest();if(latest.pending)return {opened:false,message:'A origem está sendo indexada. Aguarde ou abra o perfil inteiro.'};
  const r=latest.records.find(r=>r.path===node.path);if(!r)return {opened:false,message:'A origem deixou de ser um perfil sincronizado. Você pode abrir a nota inteira.'};
  const sections=buildGraph([r]).nodes.filter(n=>n.kind==='section'&&n.label===node.label);let match;
  if(r.mtime===node.mtime)match=sections.find(n=>n.startOffset===node.startOffset&&n.text===node.text);
  if(!match){const same=sections.filter(n=>n.text===node.text);match=same.length===1?same[0]:sections.length===1?sections[0]:null;}
  if(!match)return {opened:false,message:'O trecho mudou, desapareceu ou tem títulos ambíguos. Abra o perfil inteiro e atualize o mapa.'};line=match.startLine;
 }
 const current=app.vault.getAbstractFileByPath(node.path);if(!current||current.extension!=='md')return {opened:false,message:'A nota de origem foi removida.'};
 if(!isCurrent())return {opened:false,message:'Navegação cancelada.'};
 await app.workspace.getLeaf(true).openFile(current,{active:true,eState:{line}});return {opened:true,message:'Origem aberta.'};
}
class BrainView extends ItemView{
 constructor(leaf,services){super(leaf);this.services=services;this.controls={};this.selection=null;this.profileId=null;this.pageNumber=0;this.tab='network';this.cleanups=[];this.detailCleanups=[];this.dashboardCleanups=[];this.navigationGeneration=0;this.disposed=false;}
 getViewType(){return 'codex-brain-3d';}getDisplayText(){return 'Codex Brain';}getIcon(){return 'brain-circuit';}
 el(tag,parent,text='',cls=''){const e=this.contentEl.ownerDocument.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;if(parent)parent.appendChild(e);return e;}
 listen(el,name,fn,scope=this.cleanups){el.addEventListener(name,fn);scope.push(()=>el.removeEventListener(name,fn));}
 button(parent,text,fn,label,scope=this.cleanups){const b=this.el('button',parent,text);b.type='button';if(label)b.setAttribute('aria-label',label);this.listen(b,'click',fn,scope);return b;}
 async onOpen(){
  this.disposed=false;const root=this.contentEl;root.replaceChildren();root.className+=' codex-brain-3d';const c=this.controls;
  const header=this.el('header',root,'','cb-header');this.el('strong',header,'Codex Brain');this.el('span',header,'Conhecimento registrado · origem verificável','cb-muted');const tabs=this.el('div',header,'','cb-tabs');tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','Visualização do Brain');
  const resizeLayout=()=>{const compact=root.clientWidth<820;root.className=root.className.replace(/\s*cb-compact\b/g,'')+(compact?' cb-compact':'');};
  this.paneObserver=new root.ownerDocument.defaultView.ResizeObserver(resizeLayout);this.paneObserver.observe(root);resizeLayout();
  const suffix=Math.random().toString(36).slice(2);c.network=this.el('section',root,'','cb-network');c.dashboard=this.el('section',root,'','cb-dashboard');
  const setTab=tab=>{this.tab=tab;const network=tab==='network';c.network.hidden=!network;c.dashboard.hidden=network;c.networkTab.setAttribute('aria-selected',String(network));c.panelTab.setAttribute('aria-selected',String(!network));this.renderer?.setVisible(network);};
  this.setTab=setTab;
  c.networkTab=this.button(tabs,'Rede 3D',()=>setTab('network'));c.panelTab=this.button(tabs,'Painel',()=>setTab('panel'));
  for(const [button,panel,key] of [[c.networkTab,c.network,'network'],[c.panelTab,c.dashboard,'panel']]){button.id='cb-tab-'+key+'-'+suffix;panel.id='cb-'+key+'-'+suffix;button.setAttribute('role','tab');button.setAttribute('aria-controls',panel.id);panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby',button.id);}
  c.status=this.el('div',c.network,'','cb-status');c.status.setAttribute('role','status');c.status.setAttribute('aria-live','polite');
  const top=this.el('div',c.network,'','cb-top');const intro=this.el('div',top);this.el('h2',intro,'Conhecimento conectado');this.el('p',intro,'Arraste para girar. Selecione um ponto para ver a origem.','cb-muted');
  const toolbar=this.el('div',top,'','cb-tools'),win=root.ownerDocument.defaultView;this.motionQuery=win.matchMedia('(prefers-reduced-motion: reduce)');this.paused=this.motionQuery.matches||!this.services.getSettings().motion;
  c.pause=this.button(toolbar,'',()=>{this.paused=!this.paused;this.updatePause();this.renderer.setPaused(this.paused);});this.updatePause();
  c.zoomOut=this.button(toolbar,'−',()=>this.renderer.zoom(-.15),'Diminuir zoom');c.zoomIn=this.button(toolbar,'+',()=>this.renderer.zoom(.15),'Aumentar zoom');
  c.left=this.button(toolbar,'←',()=>this.renderer.rotate(-.2,0),'Girar para a esquerda');c.right=this.button(toolbar,'→',()=>this.renderer.rotate(.2,0),'Girar para a direita');c.up=this.button(toolbar,'↑',()=>this.renderer.rotate(0,-.2),'Girar para cima');c.down=this.button(toolbar,'↓',()=>this.renderer.rotate(0,.2),'Girar para baixo');
  const layout=this.el('div',c.network,'','cb-layout'),map=this.el('div',layout,'','cb-map'),stage=this.el('div',map,'','cb-stage');c.canvas=this.el('canvas',stage);c.canvas.setAttribute('role','img');c.canvas.setAttribute('aria-label','Rede 3D de perfis e seções. Use os botões de rotação e a lista para navegar pelo teclado.');
  this.el('p',map,'○ Perfil · • Seção    ┄ Contém · ─ Link de nota','cb-legend');this.el('p',map,'Rotação e pulsos são efeitos visuais. Distância não mede semelhança.','cb-muted cb-caption');
  const aside=this.el('aside',layout),projectLabel=this.el('label',aside,'Projeto','cb-label');c.projects=this.el('select',projectLabel);this.listen(c.projects,'change',()=>{this.profileId=c.projects.value||null;this.pageNumber=0;this.selection=null;this.renderState(this.services.getState());});
  const label=this.el('label',aside,'Conhecimento','cb-label');c.select=this.el('select',label);this.listen(c.select,'change',()=>this.choose(c.select.value));
  c.detail=this.el('div',aside,'','cb-detail');c.detail.setAttribute('aria-live','polite');c.origin=this.button(aside,'Abrir origem',()=>void this.navigate(false));c.fallback=this.button(aside,'Abrir perfil inteiro',()=>void this.navigate(true));c.fallback.hidden=true;c.navigationStatus=this.el('p',aside,'','cb-muted');c.navigationStatus.setAttribute('role','status');
  const footer=this.el('footer',c.network);c.counter=this.el('span',footer);const pager=this.el('div',footer,'','cb-tools');c.previous=this.button(pager,'Anterior',()=>{this.pageNumber--;this.renderState(this.services.getState());});c.page=this.el('span',pager);c.next=this.button(pager,'Próxima',()=>{this.pageNumber++;this.renderState(this.services.getState());});
  this.renderer=createRenderer(c.canvas,{onSelect:id=>this.choose(id),reducedMotion:this.paused});
  const onMotion=e=>{if(e.matches){this.paused=true;this.updatePause();this.renderer.setPaused(true);}};this.motionQuery.addEventListener('change',onMotion);this.cleanups.push(()=>this.motionQuery.removeEventListener('change',onMotion));
  this.unsubscribe=this.services.subscribe(state=>{if(!this.disposed)this.renderState(state);});this.renderState(this.services.getState());setTab(this.tab);
 }
 updatePause(){this.controls.pause.textContent=this.paused?'Retomar animação':'Pausar animação';this.controls.pause.setAttribute('aria-pressed',String(this.paused));}
 option(parent,value,text){const o=this.el('option',parent,text);o.value=value;return o;}
 renderState(state){
  if(this.disposed)return;const c=this.controls;c.status.textContent=state.message||(state.status==='indexing'?'Indexando notas…':'');c.status.hidden=!c.status.textContent;
  const graph=state.graph||{nodes:[],edges:[],profiles:[]};this.graph=graph;
  if(!graph.nodes.some(n=>n.id===this.profileId&&n.kind==='profile'))this.profileId=null;
  c.projects.replaceChildren();this.option(c.projects,'','Todos os projetos');for(const p of graph.nodes.filter(n=>n.kind==='profile'))this.option(c.projects,p.id,p.label+' — '+p.path);c.projects.value=this.profileId||'';
  this.currentPage=selectGraphPage(graph,{profileId:this.profileId,page:this.pageNumber});this.pageNumber=this.currentPage.page;
  c.select.replaceChildren();for(const n of this.currentPage.nodes)this.option(c.select,n.id,(n.kind==='profile'?'○ ':'• ')+n.label);c.select.disabled=!this.currentPage.nodes.length;
  this.renderer.setPage(this.currentPage);const chosen=this.currentPage.nodes.find(n=>n.id===this.selection)||this.currentPage.nodes[0];this.choose(chosen?.id||null);
  c.counter.textContent=this.currentPage.shownNodes+' pontos exibidos de '+this.currentPage.totalNodes+' indexados';c.page.textContent=(this.pageNumber+1)+' / '+this.currentPage.pageCount;c.previous.disabled=this.pageNumber===0;c.next.disabled=this.pageNumber+1>=this.currentPage.pageCount;
  this.renderDashboard(state);
 }
 choose(id){this.navigationGeneration++;for(const f of this.detailCleanups.splice(0))f();this.selection=id;const c=this.controls,n=this.currentPage.nodes.find(n=>n.id===id);this.renderer.setSelection(id);c.select.value=id||'';c.detail.replaceChildren();c.navigationStatus.textContent='';c.fallback.hidden=true;c.origin.disabled=!n;
  if(!n){this.el('p',c.detail,'Nenhum ponto disponível. Sincronize um perfil para começar.','cb-muted');return;}
  this.el('span',c.detail,n.kind==='profile'?'Perfil sincronizado':'Seção · registrado no perfil','cb-kicker');this.el('h3',c.detail,n.label);this.el('p',c.detail,n.path,'cb-path');this.el('p',c.detail,'Sincronização: '+(n.syncedAt||'não disponível'),'cb-muted');this.el('pre',c.detail,n.text.length>2400?n.text.slice(0,2400)+'\n… Abra a origem para ler o texto completo.':n.text,'cb-excerpt');
  const r=this.graph.profiles.find(r=>r.path===n.path);if(!r)return;
  if(n.kind==='profile'){const count=this.graph.nodes.filter(x=>x.profileId===n.id&&x.kind==='section').length;this.el('p',c.detail,'Contém '+count+' seções.','cb-muted');}
  else this.el('p',c.detail,'Faz parte do perfil '+n.project+'.','cb-muted');
  for(const link of r.resolved){const outgoing=this.graph.nodes.some(x=>x.kind==='profile'&&x.path===link.path);this.button(c.detail,'→ '+link.path+' ('+link.count+')'+(outgoing?'':' · fora do mapa'),()=>void this.openLink(link.path),undefined,this.detailCleanups);}
  const incoming=this.graph.edges.filter(e=>e.kind==='link'&&e.target===n.profileId);for(const e of incoming){const src=this.graph.nodes.find(x=>x.id===e.source);this.el('p',c.detail,'← '+src.path+' ('+e.count+')','cb-muted');}
  if(r.unresolved.length){this.el('h4',c.detail,'Links não resolvidos');for(const u of r.unresolved)this.el('p',c.detail,u.target+' ('+u.count+')','cb-muted');}
 }
 async openLink(path){try{if(!this.app.vault.getAbstractFileByPath(path)){this.controls.navigationStatus.textContent='A nota vinculada não existe mais.';return;}await this.app.workspace.openLinkText(path,this.currentPage.nodes.find(n=>n.id===this.selection)?.path||'',true);}catch(e){if(!this.disposed)this.controls.navigationStatus.textContent=String(e.message||e);}}
 async navigate(whole){const n=this.currentPage.nodes.find(n=>n.id===this.selection);if(!n)return;const id=n.id,generation=++this.navigationGeneration;this.controls.origin.disabled=true;try{const result=await openOrigin(this.app,whole?{...n,kind:'profile'}:n,this.services.readLatest,()=>!this.disposed&&this.selection===id&&this.navigationGeneration===generation);if(this.disposed||this.selection!==id||this.navigationGeneration!==generation)return;this.controls.navigationStatus.textContent=result.message;this.controls.fallback.hidden=result.opened||n.kind==='profile';}catch(e){if(!this.disposed&&this.selection===id)this.controls.navigationStatus.textContent='Falha ao abrir a origem: '+String(e.message||e);}finally{if(!this.disposed)this.controls.origin.disabled=false;}}
 renderDashboard(state){for(const f of this.dashboardCleanups.splice(0))f();const d=this.controls.dashboard;d.replaceChildren();this.el('h2',d,'Painel dos projetos');this.el('p',d,state.message||'Valores dos perfis sincronizados.','cb-muted');this.el('p',d,this.graph.profiles.length+' perfis · '+this.graph.nodes.filter(n=>n.kind==='section').length+' seções');const list=this.el('div',d,'','cb-projects');for(const p of this.graph.profiles){const card=this.el('article',list);this.el('h3',card,p.project);this.el('p',card,p.path,'cb-path');this.el('p',card,'Sincronizado em: '+(p.syncedAt||'não disponível'),'cb-muted');this.button(card,'Explorar projeto',()=>{this.profileId=this.graph.nodes.find(n=>n.path===p.path&&n.kind==='profile').id;this.pageNumber=0;this.renderState(this.services.getState());this.setTab('network');},undefined,this.dashboardCleanups);}}
 async onClose(){this.disposed=true;this.navigationGeneration++;this.paneObserver?.disconnect();this.unsubscribe?.();this.renderer?.dispose();for(const scope of [this.cleanups,this.detailCleanups,this.dashboardCleanups])for(const f of scope.splice(0))f();this.contentEl.replaceChildren();}
}
module.exports={BrainView,openOrigin};
