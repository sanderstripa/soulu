/* Same incremental collection policy as cef/soulu/adblock_cosmetic.h. */
export class SouluCosmeticChild extends JSWindowActorChild{
 handleEvent(){if(this.state)return;const win=this.contentWindow,doc=this.document;const state=this.state={sheet:new win.CSSStyleSheet(),selectors:new Set(),classes:new Set(),ids:new Set(),queue:[],timer:0,paint:0};doc.adoptedStyleSheets=[...doc.adoptedStyleSheets,state.sheet];
  const send=async tokens=>{try{const values=await this.sendQuery('selectors',tokens);let changed=false;for(const s of values)if(typeof s==='string'&&s.length<16384&&!/[{}]/.test(s)&&!state.selectors.has(s)){state.selectors.add(s);changed=true;}if(changed&&!state.paint)state.paint=win.requestAnimationFrame(()=>{state.paint=0;state.sheet.replaceSync([...state.selectors].map(s=>s+'{display:none!important}').join('\n'));});}catch(error){console.warn('Soulu cosmetic filter:',String(error));}};
  const collect=root=>{if(root.nodeType!==1&&root!==doc)return;const nodes=root===doc?[...doc.querySelectorAll('[class],[id]')]:[root,...root.querySelectorAll('[class],[id]')];let classes=[],ids=[];const flush=()=>{if(classes.length||ids.length){send({classes,ids});classes=[];ids=[];}};for(const node of nodes.slice(0,10000)){for(const c of node.classList||[])if(c.length<=256&&!state.classes.has(c)&&state.classes.size<20000){state.classes.add(c);classes.push(c);if(classes.length+ids.length>=256)flush();}if(node.id&&node.id.length<=256&&!state.ids.has(node.id)&&state.ids.size<20000){state.ids.add(node.id);ids.push(node.id);if(classes.length+ids.length>=256)flush();}}flush();};
  state.refresh=()=>{state.classes.clear();state.ids.clear();state.selectors.clear();state.sheet.replaceSync('');send({});collect(doc);};
  this.observer=new win.MutationObserver(records=>{for(const r of records){if(r.type==='attributes')state.queue.push(r.target);else for(const n of r.addedNodes)if(n.nodeType===1)state.queue.push(n);}if(!state.timer)state.timer=win.setTimeout(()=>{state.timer=0;for(const root of new Set(state.queue.splice(0)))collect(root);},200);});
  this.observer.observe(doc,{subtree:true,childList:true,attributes:true,attributeFilter:['class','id']});send({});collect(doc);
 }
 receiveMessage(message){if(message.name==='refresh'){if(!this.state)this.handleEvent();else this.state.refresh();}}
 didDestroy(){this.observer?.disconnect();}
}
