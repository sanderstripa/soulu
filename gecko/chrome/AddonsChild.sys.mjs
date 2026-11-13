/* Styling only for the native internal add-ons document; never runs on websites. */
export class SonaAddonsChild extends JSWindowActorChild {
 handleEvent(){
  if(this.document.documentURI!=='about:addons'||this.observer)return;
  const doc=this.document,win=this.contentWindow;
  const update=()=>{if(doc.title!=='Расширения — Sona')doc.title='Расширения — Sona';const walker=doc.createTreeWalker(doc.body,win.NodeFilter.SHOW_TEXT);while(walker.nextNode()){const n=walker.currentNode;if(/Firefox/.test(n.data))n.data=n.data.replace(/Firefox/g,'Sona');}

   for(const card of doc.querySelectorAll('addon-card[addon-id="vot-ext@firefox"]'))card.hidden=true;
   const search=doc.querySelector('search-addons moz-input-search');
   const input=search?.shadowRoot?.querySelector('input');
   if(input&&!input.hasAttribute('data-sona-centered')){
    input.setAttribute('data-sona-centered','true');
    input.style.setProperty('box-sizing','border-box','important');
    input.style.setProperty('min-height','36px','important');
    input.style.setProperty('height','36px','important');
    input.style.setProperty('padding-block','0px','important');
    input.style.setProperty('line-height','normal','important');
    input.style.setProperty('margin-block','0px','important');
   }
  };
  this.observer=new win.MutationObserver(update);this.observer.observe(doc,{subtree:true,childList:true});
  win.customElements.whenDefined('moz-input-search').then(()=>{update();const search=doc.querySelector('moz-input-search');return search?.updateComplete;}).then(update);
  update();
 }
 didDestroy(){try{this.observer?.disconnect();}catch{}}
}
