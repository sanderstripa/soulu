(() => {
  'use strict';
  if(globalThis.__souluTranslate)return;
  const originals=new Map(),ids=new WeakMap(),pending=new Set();
  let serial=0,active=false,observer=null;
  const excluded='script,style,noscript,code,pre,textarea,input,select,option,[contenteditable],[translate="no"],.notranslate,svg,canvas';
  const allowed=node=>node.nodeType===Node.TEXT_NODE&&node.parentElement&&
    !node.parentElement.closest(excluded)&&node.nodeValue.trim().length>1&&
    node.nodeValue.length<=16000&&node.parentElement.getClientRects().length&&
    getComputedStyle(node.parentElement).visibility!=='hidden'&&
    !/^\s*(https?:\/\/|www\.)\S+\s*$/.test(node.nodeValue);
  function add(root){
    if(root.nodeType===Node.TEXT_NODE){if(allowed(root))pending.add(root);return;}
    if(root.nodeType!==Node.ELEMENT_NODE||root.matches(excluded))return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    let node;while(node=walker.nextNode())if(allowed(node))pending.add(node);
  }
  function start(){
    if(active)return;active=true;add(document.body);
    observer=new MutationObserver(records=>{for(const r of records){
      if(r.type==='characterData'){
        const old=originals.get(ids.get(r.target));
        if(old&&r.target.nodeValue===old.translated)continue;
        if(old){old.original=r.target.nodeValue;old.translated=null;}
        add(r.target);
      }else for(const node of r.addedNodes)add(node);
    }});observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  }
  globalThis.__souluTranslate={
    probe(){return {lang:document.documentElement.lang,sample:(document.body?.innerText||'').slice(0,12000)};},
    collect(){
      start();const nodes=[];let total=0;
      for(const node of pending){
        pending.delete(node);if(!node.isConnected||!allowed(node))continue;
        let id=ids.get(node);if(!id){id=++serial;ids.set(node,id);originals.set(id,{node,original:node.nodeValue,translated:null});}
        const row=originals.get(id);nodes.push({id,text:row.original});total+=row.original.length;
        if(nodes.length>=32||total>=24000)break;
      }
      for(const [id,row] of originals)if(!row.node.isConnected)originals.delete(id);
      const sample=(document.body?.innerText||'').slice(0,12000);
      return {nodes,remaining:pending.size,lang:document.documentElement.lang,sample};
    },
    apply(rows){
      if(!active)return {applied:0};let count=0;
      for(const row of rows){const old=originals.get(row.id);
        if(!old||!old.node.isConnected||old.node.nodeValue!==old.original||typeof row.text!=='string')continue;
        old.translated=row.text;old.node.nodeValue=row.text;count++;
      }return {applied:count};
    },
    restore(){
      active=false;observer?.disconnect();observer=null;
      for(const row of originals.values())if(row.node.isConnected&&row.node.nodeValue===row.translated)row.node.nodeValue=row.original;
      originals.clear();pending.clear();return {restored:true};
    }
  };
})()
