'use strict';
const Module=require('node:module');const {fakeDocument}=require('./fake-dom');
class ItemView{constructor(leaf){this.leaf=leaf;this.app=leaf.app;this.contentEl=leaf.doc.createElement('div');}}
class Plugin{constructor(app,manifest){this.app=app;this.manifest=manifest;this.cleanups=[];this.commands=[];this.settings=[];this.factories={};}registerView(id,f){this.factories[id]=f;}addCommand(c){this.commands.push(c);}addSettingTab(t){this.settings.push(t);}registerEvent(ref){this.cleanups.push(()=>ref.off());}async loadData(){return this.saved||null;}async saveData(data){this.saved=data;}register(f){this.cleanups.push(f);}unload(){this.onunload?.();for(const f of this.cleanups.splice(0))f();}}
class PluginSettingTab{constructor(app,plugin){this.app=app;this.plugin=plugin;this.containerEl=app.doc.createElement('div');}}
class Notice{constructor(message){Notice.messages.push(message);}}Notice.messages=[];
const api={ItemView,Plugin,PluginSettingTab,Notice};
function loadWithObsidian(path){const original=Module._load;Module._load=function(request,...args){return request==='obsidian'?api:original.call(this,request,...args)};try{delete require.cache[require.resolve(path)];return require(path);}finally{Module._load=original;}}
function leaf(app,doc=fakeDocument()){return {app,doc,opened:[],async openFile(file,state){this.opened.push({file,state})}};}
module.exports={api,loadWithObsidian,leaf};
