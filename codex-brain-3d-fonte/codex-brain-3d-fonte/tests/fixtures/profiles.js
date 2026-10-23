'use strict';
function record(path='Projetos/A/Perfil do Codex Brain.md', text='# Arquitetura\nConteúdo registrado.\n', extra={}) {
  const headings=[];let offset=0;for(const [line,value] of text.split('\n').entries()){const m=/^(#{1,6}) (.+?)\r?$/.exec(value);if(m)headings.push({title:m[2],level:m[1].length,startOffset:offset,startLine:line,endOffset:offset+value.replace(/\r$/,'').length});offset+=value.length+1;}
  return {path,project:path.split('/')[1],sourcePath:'C:\\repo',syncedAt:'2026-10-22T12:00:00-03:00',mtime:1,text,headings,resolved:[],unresolved:[],...extra};
}
function pair(){return [record(),record('Projetos/B/Perfil do Codex Brain.md','# Fluxo\nOutro trecho.\n')];}
module.exports={record,pair};
