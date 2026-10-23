'use strict';
const {buildGraph}=require('./model');
function normalizeFolder(value){if(typeof value!=='string')throw Error('Pasta de origem inválida.');const p=value.trim().replace(/\\/g,'/');if(!p||p.startsWith('/')||/^[A-Za-z]:/.test(p)||p.split('/').some(s=>s==='..'||s==='.'))throw Error('Use uma pasta relativa ao cofre, sem .. ou caminho absoluto.');return p.replace(/\/+$/,'');}
/** Public cache metadata has no file revision. Bind changed-event data to it.
 * The initial getFileCache snapshot is the host baseline. After any Markdown
 * edit, reject that baseline until changed(data, cache) and resolved arrive.
 */
function createMetadataTracker(){
 const entries=new Map();let resolving=false;
 const within=(path,prefix)=>path===prefix||path.startsWith(prefix+'/');
 return {
  invalidate(path){if(!path)return;entries.set(path,{dirty:true});resolving=true;},
  accept(path,text,cache){if(typeof text!=='string'||!cache)return;entries.set(path,{text,cache,dirty:false});resolving=true;},
  resolved(){resolving=false;},
  rename(oldPath,newPath){const moves=[...entries].filter(([p])=>within(p,oldPath));for(const [p,entry] of moves){entries.delete(p);entries.set(newPath+p.slice(oldPath.length),entry);}resolving=true;},
  forget(path){for(const p of entries.keys())if(within(p,path))entries.delete(p);resolving=true;},
  tracks(path){return [...entries.keys()].some(p=>within(p,path));},
  isPending(path){return resolving||entries.get(path)?.dirty===true;},
  cacheFor(path,fallback){return entries.get(path)?.cache||fallback;},
  match(path,cache,text){const entry=entries.get(path);if(resolving||entry?.dirty||(entry&&entry.text!==text))return null;if(!entry)entries.set(path,{cache,text,dirty:false});return entry?.cache||cache;},
  dispose(){entries.clear();resolving=false;}
 };
}
/** Reads only owned profile bodies. Cached metadata supplies Markdown structure. */
async function readProfiles(app,sourceFolder,tracker=null){
 const prefix=normalizeFolder(sourceFolder)+'/',records=[];let pending=false;
 for(const file of app.vault.getMarkdownFiles().filter(f=>f.path.startsWith(prefix)).sort((a,b)=>a.path.localeCompare(b.path))){
  if(tracker?.isPending(file.path)){pending=true;continue;}
  const cache=tracker?.cacheFor(file.path,app.metadataCache.getFileCache(file))||app.metadataCache.getFileCache(file);if(!cache){pending=true;continue;}const fm=cache.frontmatter||{};
  if(fm.gerenciado_por!=='sync_obsidian.py'||typeof fm.caminho_origem!=='string'||!fm.caminho_origem.trim())continue;
  const mtime=file.stat.mtime,size=file.stat.size,text=await app.vault.cachedRead(file);if(file.stat.mtime!==mtime||file.stat.size!==size){pending=true;continue;}
  if(tracker&&!tracker.match(file.path,cache,text)){pending=true;continue;}
  const headings=(cache.headings||[]).map(h=>({title:h.heading,level:h.level,startOffset:h.position.start.offset,startLine:h.position.start.line,endOffset:h.position.end.offset}));
  const lines=text.split('\n');let invalid=false;
  for(const h of headings){const line=lines[h.startLine]||'',fragment=text.slice(h.startOffset,h.endOffset);if(!Number.isInteger(h.startOffset)||h.startOffset<0||h.endOffset>text.length||h.endOffset<h.startOffset||!line.includes(h.title)||!fragment.includes(h.title)){invalid=true;break;}}
  if(invalid){pending=true;continue;}
  const resolved=Object.entries(app.metadataCache.resolvedLinks[file.path]||{}).map(([path,count])=>({path,count}));
  const unresolved=Object.entries(app.metadataCache.unresolvedLinks[file.path]||{}).map(([target,count])=>({target,count}));
  records.push({path:file.path,project:typeof fm.projeto==='string'&&fm.projeto.trim()?fm.projeto:file.path.split('/').slice(-2,-1)[0]||file.path,sourcePath:fm.caminho_origem,syncedAt:typeof fm.sincronizado_em==='string'&&fm.sincronizado_em?fm.sincronizado_em:null,mtime,text,headings,resolved,unresolved});
 }
 return {records,pending};
}
function createIndexController({read,onState,delayMs=150}){
 let revision=0,disposed=false,timer=null,graph=null;
 const emit=(status,message,rev)=>{if(!disposed&&rev===revision)onState({status,message,graph,revision:rev});};
 async function refresh(){if(disposed)return;if(timer!==null){clearTimeout(timer);timer=null;}const rev=++revision;emit('indexing','Indexando notas…',rev);
  try{const result=await read();if(disposed||rev!==revision)return;if(result.pending){emit('indexing','Aguardando o índice de notas do Obsidian; último mapa preservado.',rev);return;}graph=buildGraph(result.records);emit('ready',graph.nodes.length?'':'Nenhum perfil sincronizado encontrado na pasta configurada.',rev);}
  catch(error){emit(graph?'stale':'error','Não foi possível atualizar: '+(error instanceof Error?error.message:String(error)),rev);}
 }
 function schedule(){if(disposed)return;++revision;if(timer!==null)clearTimeout(timer);timer=setTimeout(()=>{timer=null;void refresh();},delayMs);}
 function dispose(){disposed=true;++revision;if(timer!==null)clearTimeout(timer);timer=null;}
 return {refresh,schedule,dispose};
}
module.exports={normalizeFolder,readProfiles,createIndexController,createMetadataTracker};
