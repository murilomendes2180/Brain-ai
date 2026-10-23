'use strict';
const {Plugin,PluginSettingTab,Notice}=require('obsidian');
const {BrainView}=require('./view');
const {normalizeFolder,readProfiles,createIndexController,createMetadataTracker}=require('./indexer');
class BrainSettings extends PluginSettingTab{
 display(){const root=this.containerEl;root.replaceChildren();const doc=root.ownerDocument;const el=(tag,text)=>{const n=doc.createElement(tag);if(text)n.textContent=text;root.appendChild(n);return n;};el('h2','Codex Brain 3D');el('p','O mapa lê perfis sincronizados. Suas notas e o banco do Brain não são alterados.');
  const folderLabel=el('label','Pasta de origem dos perfis');const folder=doc.createElement('input');folder.type='text';folder.value=this.plugin.settingsData.sourceFolder;folder.placeholder='Projetos';folderLabel.appendChild(folder);folder.style.display='block';folder.style.marginBottom='16px';
  const motionLabel=el('label');const motion=doc.createElement('input');motion.type='checkbox';motion.checked=this.plugin.settingsData.motion;motionLabel.appendChild(motion);const text=doc.createElement('span');text.textContent=' Permitir rotação e pulsos (respeita movimento reduzido)';motionLabel.appendChild(text);
  const save=el('button','Salvar preferências');save.type='button';save.style.display='block';save.style.marginTop='16px';const status=el('p');status.setAttribute('role','status');save.addEventListener('click',async()=>{save.disabled=true;try{await this.plugin.applySettings(folder.value,motion.checked);status.textContent='Preferências salvas.';}catch(e){status.textContent=e.message||String(e);}finally{save.disabled=false;}});
 }
}
class BrainPlugin extends Plugin{
 async onload(){
  this.disposed=false;this.listeners=new Set();this.views=new Set();this.settingsData={sourceFolder:'Projetos',motion:true};const raw=await this.loadData();if(this.disposed)return;
  if(raw){try{this.settingsData={sourceFolder:normalizeFolder(raw.sourceFolder||'Projetos'),motion:typeof raw.motion==='boolean'?raw.motion:true};}catch{new Notice('Pasta de origem inválida; usando Projetos.');}}
  this.metadataTracker=createMetadataTracker();
  this.state={status:'indexing',graph:null,message:'Aguardando o índice do Obsidian…',revision:0};
  this.controller=createIndexController({read:()=>readProfiles(this.app,this.settingsData.sourceFolder,this.metadataTracker),onState:state=>{this.state=state;for(const listener of this.listeners)listener(state);}});
  this.registerView('codex-brain-3d',leaf=>{let view;const services={getState:()=>this.state,getSettings:()=>this.settingsData,readLatest:()=>readProfiles(this.app,this.settingsData.sourceFolder,this.metadataTracker),subscribe:listener=>{this.listeners.add(listener);return ()=>{this.listeners.delete(listener);this.views.delete(view);};}};view=new BrainView(leaf,services);this.views.add(view);return view;});
  this.addCommand({id:'open-brain',name:'Abrir Codex Brain',callback:()=>void this.openBrain()});this.addSettingTab(new BrainSettings(this.app,this));
  const schedule=()=>this.controller.schedule();
  for(const name of ['create','modify'])this.registerEvent(this.app.vault.on(name,file=>{if(file.extension==='md')this.metadataTracker.invalidate(file.path);schedule();}));
  this.registerEvent(this.app.vault.on('rename',(file,oldPath)=>{if(file.extension==='md'||this.metadataTracker.tracks(oldPath))this.metadataTracker.rename(oldPath,file.path);schedule();}));
  this.registerEvent(this.app.vault.on('delete',file=>{if(file.extension==='md'||this.metadataTracker.tracks(file.path))this.metadataTracker.forget(file.path);schedule();}));
  this.registerEvent(this.app.metadataCache.on('changed',(file,data,cache)=>{if(file.path.startsWith(this.settingsData.sourceFolder+'/'))this.metadataTracker.accept(file.path,data,cache);schedule();}));
  this.registerEvent(this.app.metadataCache.on('resolved',()=>{this.metadataTracker.resolved();schedule();}));
  this.app.workspace.onLayoutReady(()=>{if(!this.disposed)void this.controller.refresh();});
 }
 async applySettings(sourceFolder,motion){const next={sourceFolder:normalizeFolder(sourceFolder),motion:Boolean(motion)};await this.saveData(next);if(this.disposed)return;this.settingsData=next;await this.controller.refresh();}
 async openBrain(){try{const leaf=this.app.workspace.getLeavesOfType('codex-brain-3d')[0]||this.app.workspace.getLeaf(true);await leaf.setViewState({type:'codex-brain-3d',active:true});await this.app.workspace.revealLeaf(leaf);}catch(e){new Notice('Não foi possível abrir o Brain: '+(e.message||String(e)));}}
 onunload(){this.disposed=true;this.controller?.dispose();this.metadataTracker?.dispose();for(const view of this.views||[])void view.onClose();this.views?.clear();this.listeners?.clear();}
}
module.exports=BrainPlugin;
