#pragma once
namespace soulu {
// Compensate viewport-anchored controls when native page pixels extend behind
// chrome. No page wrapper, body padding, duplicated document or navigation.
inline constexpr char kPageGlassInsetScript[] = R"JS((()=>{
 let cover=0,pending=0,observer=null,sheet=null;
 const marked=new Map(),raf=requestAnimationFrame.bind(window);
 function restore(node){node.removeAttribute('data-soulu-top-control');node.style.removeProperty('--soulu-original-top');marked.delete(node)}
 function mark(node,force=false){
  if(!(node instanceof HTMLElement)||!node.isConnected||node===document.documentElement||node===document.body)return;
  if(marked.has(node)&&!force)return;
  if(force)node.removeAttribute('data-soulu-top-control');
  const css=getComputedStyle(node),top=parseFloat(css.top),r=node.getBoundingClientRect();
  if(!['fixed','sticky'].includes(css.position)||!Number.isFinite(top)||top<0||top>128||r.bottom<=0||r.top>=cover){if(marked.has(node))restore(node);return}
  for(let parent=node.parentElement;parent&&parent!==document.documentElement;parent=parent.parentElement){const c=getComputedStyle(parent);if(c.transform!=='none'||c.filter!=='none'||c.perspective!=='none'){if(marked.has(node))restore(node);return}}
  marked.set(node,{top:node.style.top,cls:node.className});
  node.style.setProperty('--soulu-original-top',top+'px');node.setAttribute('data-soulu-top-control','');
 }
 function scan(){pending=0;if(!cover||!document.documentElement)return;
  if(!sheet||!sheet.isConnected){sheet=document.createElement('style');sheet.textContent='[data-soulu-top-control]{top:calc(var(--soulu-original-top) + var(--soulu-page-cover,0px))!important}';(document.head||document.documentElement).append(sheet)}
  for(const node of marked.keys())if(!node.isConnected)marked.delete(node);
  const nodes=new Set();for(const x of [.1,.5,.9])for(const y of [1,24,48,Math.max(1,cover-1)])for(const n of document.elementsFromPoint(innerWidth*x,y))nodes.add(n);
  for(const n of nodes)mark(n);
 }
 function schedule(){if(cover&&!pending)pending=setTimeout(scan,100)}
 function apply(value){cover=Number.isFinite(value)?Math.max(0,Math.min(160,value)):0;
  if(document.documentElement)document.documentElement.style.setProperty('--soulu-page-cover',cover+'px');
  if(!cover){if(observer)observer.disconnect();for(const n of [...marked.keys()])restore(n);return}
  if(!observer)observer=new MutationObserver(records=>{for(const r of records){const old=marked.get(r.target);if(old&&(old.top!==r.target.style.top||old.cls!==r.target.className))mark(r.target,true)}schedule()});
  observer.observe(document,{subtree:true,childList:true,attributes:true,attributeFilter:['style','class']});scan();
 }
 Object.defineProperty(window,'__souluApplyGlassInset',{value:apply,writable:false,configurable:false});
 addEventListener('scroll',schedule,{capture:true,passive:true});
 addEventListener('resize',()=>{for(const n of [...marked.keys()])mark(n,true);schedule()},{passive:true});
 addEventListener('DOMContentLoaded',()=>apply(cover),{once:true});
})())JS";
}
