'use strict';
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const files=['model','indexer','scene','renderer','view','main'];
function build(){
 const modules=files.map(name=>{const source=fs.readFileSync(path.join(root,'src',name+'.js'),'utf8');for(const m of source.matchAll(/require\(['"]([^'"]+)['"]\)/g))if(m[1]!=='obsidian'&&!files.some(f=>'./'+f===m[1]))throw Error('Importação não permitida: '+m[1]);return JSON.stringify('./'+name)+':function(module,exports,require){\n'+source+'\n}';}).join(',\n');
 const result="'use strict';\n// Generated from src/ by scripts/build.js. Obsidian is provided by the host.\nmodule.exports=(function(hostRequire){\nconst modules={\n"+modules+"\n};\nconst cache=Object.create(null);\nfunction localRequire(id){if(id==='obsidian')return hostRequire(id);if(!Object.prototype.hasOwnProperty.call(modules,id))throw Error('Unknown module '+id);if(cache[id])return cache[id].exports;const module={exports:{}};cache[id]=module;modules[id](module,module.exports,localRequire);return module.exports;}\nreturn localRequire('./main');\n})(require);\n";
 const dir=path.join(root,'dist','codex-brain-3d');fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'main.js'),result);for(const name of ['manifest.json','styles.css','README.md','VALIDACAO.md'])if(fs.existsSync(path.join(root,name)))fs.copyFileSync(path.join(root,name),path.join(dir,name));return result;
}
if(require.main===module){build();console.log('Build: dist/codex-brain-3d');}module.exports={build};
