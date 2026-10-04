#pragma once
namespace soulu {
// Fixed, local program. Downloaded lists provide CSS selectors only.
inline constexpr const char* kCosmeticBootstrap=R"JS((()=>{
  const send=window.__souluCosmeticSend;delete window.__souluCosmeticSend;
  const state={sheet:new CSSStyleSheet(),selectors:new Set(),classes:new Set(),ids:new Set(),queue:[],timer:0};
  Object.defineProperty(window,'__souluCosmetic',{value:state,configurable:true});
  document.adoptedStyleSheets=[...document.adoptedStyleSheets,state.sheet];
  function collect(root){
    if(root.nodeType!==1&&root!==document)return;
    const nodes=root===document?[...document.querySelectorAll('[class],[id]')]:[root,...root.querySelectorAll('[class],[id]')];
    let classes=[],ids=[];
    const flush=()=>{if(classes.length||ids.length){send(JSON.stringify({classes,ids}));classes=[];ids=[];}};
    for(const node of nodes.slice(0,10000)){
      for(const c of node.classList||[])if(c.length<=256&&!state.classes.has(c)&&state.classes.size<20000){state.classes.add(c);classes.push(c);if(classes.length+ids.length>=256)flush();}
      if(node.id&&node.id.length<=256&&!state.ids.has(node.id)&&state.ids.size<20000){state.ids.add(node.id);ids.push(node.id);if(classes.length+ids.length>=256)flush();}
    }flush();
  }
  state.refresh=()=>{state.classes.clear();state.ids.clear();state.selectors.clear();state.sheet.replaceSync('');send('{}');collect(document);};
  const observer=new MutationObserver(records=>{
    for(const r of records){if(r.type==='attributes')state.queue.push(r.target);else for(const n of r.addedNodes)if(n.nodeType===1)state.queue.push(n);}
    if(!state.timer)state.timer=setTimeout(()=>{state.timer=0;const roots=state.queue.splice(0);for(const root of new Set(roots))collect(root);},200);
  });
  observer.observe(document,{subtree:true,childList:true,attributes:true,attributeFilter:['class','id']});
  send('{}');
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>collect(document),{once:true});else collect(document);
})())JS";
}
