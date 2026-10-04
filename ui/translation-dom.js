(() => {
  'use strict';
  if(globalThis.__souluTranslate)return;
  const originals=new Map(),ids=new WeakMap(),pending=new Set();
  let serial=0,active=false,observer=null,cleanup=null;
  const excluded='script,style,noscript,code,pre,textarea,input,select,option,[contenteditable],[translate="no"],.notranslate,svg,canvas';
  const allowed=node=>node.nodeType===Node.TEXT_NODE&&node.parentElement&&
    !node.parentElement.closest(excluded)&&node.nodeValue.trim().length>1&&
    node.nodeValue.length<=128000&&node.parentElement.getClientRects().length&&
    getComputedStyle(node.parentElement).visibility!=='hidden'&&
    !/^\s*(https?:\/\/|www\.)\S+\s*$/.test(node.nodeValue);
  const roots=[];let walker=null,queued=new WeakSet();
  function add(root){if(!root||queued.has(root))return;if(root.nodeType!==Node.TEXT_NODE&&root.nodeType!==Node.ELEMENT_NODE)return;queued.add(root);roots.push(root);}
  function scan(){
    const deadline=performance.now()+8;let count=0;
    while(pending.size<64&&count++<500&&performance.now()<deadline){
      if(!walker){const root=roots.shift();if(!root)return;queued.delete(root);if(!root.isConnected)continue;
        if(root.nodeType===Node.TEXT_NODE){if(allowed(root))pending.add(root);continue;}
        if(root.matches(excluded))continue;walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);}
      const node=walker.nextNode();if(!node){walker=null;continue;}if(allowed(node))pending.add(node);
    }
  }
  function sample(){if(!document.body)return '';const tree=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let text='',node,count=0;const deadline=performance.now()+20;
    while(text.length<12000&&count++<2000&&performance.now()<deadline&&(node=tree.nextNode()))if(allowed(node))text+=node.nodeValue.slice(0,12000-text.length)+' ';return text.slice(0,12000);
  }
  function start(){
    if(active||!document.body)return;active=true;add(document.body);
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
    probe(){return {lang:document.documentElement.lang,sample:sample()};},
    collect(){
      start();scan();const nodes=[];let total=0;
      for(const node of pending){
        pending.delete(node);if(!node.isConnected||!allowed(node))continue;
        let id=ids.get(node);if(!id||!originals.has(id)){id=++serial;ids.set(node,id);originals.set(id,{node,original:node.nodeValue,translated:null});}
        const row=originals.get(id);nodes.push({id,text:row.original});total+=row.original.length;
        if(nodes.length>=32||total>=24000)break;
      }
      cleanup??=originals.entries();for(let i=0;i<64;i++){const entry=cleanup.next();if(entry.done){cleanup=null;break;}const [id,row]=entry.value;if(!row.node.isConnected)originals.delete(id);}
      return {nodes,remaining:pending.size+roots.length+(walker?1:0)};
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
      originals.clear();cleanup=null;pending.clear();roots.length=0;walker=null;queued=new WeakSet();return {restored:true};
    }
  };
})()
