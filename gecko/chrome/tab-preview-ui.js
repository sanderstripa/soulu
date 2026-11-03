/* One hover card shares the host's per-window, memory-only native image cache. */
(()=>{
if(!location.pathname.endsWith('/index.html'))return;
const api=window.browserShell,invoke=(action,payload)=>new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action,payload}),onSuccess:s=>resolve(JSON.parse(s)),onFailure:(_,e)=>reject(Error(e))}));
let state={},owner=null,timer=0,token=0;const card=document.createElement('aside');card.className='soulu-tab-preview';card.hidden=true;document.body.append(card);
function hide(){clearTimeout(timer);token++;owner=null;if(card.hidden)return;card.hidden=true;api.setPopover(false,'tab-preview');}
api.onState(s=>{if(state.activeTabId!==s.activeTabId||s.overviewVisible||s.settingsOverlayOpen)hide();state=s;});api.getState().then(s=>state=s);
document.addEventListener('pointerover',event=>{const node=event.target.closest('[data-tab-id]');if(!node||node===owner)return;const tab=state.tabs?.find(t=>t.id===Number(node.dataset.tabId));if(!tab||tab.active)return;hide();owner=node;const serial=token;
 timer=setTimeout(async()=>{try{const result=await invoke('browser.tab.thumbnail',{id:tab.id});if(serial!==token||!node.isConnected||!result.thumbnail)return;card.replaceChildren();const image=document.createElement('img');image.src=result.thumbnail;image.alt='';const title=document.createElement('strong');title.textContent=tab.title||tab.url;card.append(image,title);card.hidden=false;const r=node.getBoundingClientRect();card.style.left=Math.max(8,Math.min(innerWidth-264,r.left))+'px';card.style.top=(r.bottom+8)+'px';api.setPopover(true,'tab-preview');}catch(error){console.debug(error);}},420);
},true);
document.addEventListener('pointerout',e=>{if(owner&&!owner.contains(e.relatedTarget))hide();},true);for(const event of ['pointerdown','keydown','dragstart'])document.addEventListener(event,hide,true);window.addEventListener('blur',hide);window.addEventListener('resize',()=>{if(!card.hidden){const r=owner?.getBoundingClientRect();if(r)card.style.left=Math.max(8,Math.min(innerWidth-264,r.left))+'px';}});
})();
