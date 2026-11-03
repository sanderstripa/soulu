/* Existing Soulu action slots, driven by native events rather than polling. */
(()=>{
'use strict';const api=window.browserShell;if(!api)return;let state={},items=[],request=0,last='',lastError='';
function draw(){const signature=JSON.stringify([state.activeProfileId,state.incognito,items]);if(signature===last)return;last=signature;for(const host of document.querySelectorAll('[data-extension-toolbar]')){host.replaceChildren();for(const item of items.filter(e=>e.enabled&&e.pinned&&e.action)){
 const b=document.createElement('button');b.type='button';b.className=host.dataset.extensionToolbar==='compact'?'compact-control extension-action':'toolbar-button extension-action';b.dataset.extensionId=item.id;b.title=item.title||item.name;b.setAttribute('aria-label',b.title);b.disabled=!item.actionEnabled;
 if(/^data:image\//.test(item.icon||'')){const image=document.createElement('img');image.src=item.icon;image.alt='';b.append(image);}else b.textContent=item.name.slice(0,1);
 if(item.badge){const badge=document.createElement('span');badge.className='gecko-extension-badge';badge.textContent=item.badge;const rgba=a=>Array.isArray(a)&&a.length===4&&a.every(Number.isFinite)?`rgba(${a[0]},${a[1]},${a[2]},${a[3]/255})`:'';badge.style.backgroundColor=rgba(item.badgeColor);badge.style.color=rgba(item.badgeTextColor);b.append(badge);}
 b.onclick=async()=>{lastError='';const rect=b.getBoundingClientRect();try{await api.extensions('open',{profile:state.activeProfileId,id:item.id,tabId:state.activeTabId,generation:state.page?.generation,anchor:{x:rect.x,y:rect.y,width:rect.width,height:rect.height}});}catch(error){lastError=error.message;b.title=lastError;console.error('Soulu extension:',error);}};host.append(b);
 }if(host.dataset.extensionToolbar!=='compact')document.body.style.setProperty('--extension-toolbar-width',host.children.length*32+'px');}}
async function refresh(){const ticket=++request;try{const current=await api.getState();state=current;const value=await api.extensions('list',{profile:current.activeProfileId});if(ticket!==request)return;items=value.items||[];draw();}catch(error){console.error(error);}}
api.onState(value=>{const changed=state.activeProfileId!==value.activeProfileId||state.incognito!==value.incognito;state=value;if(changed)refresh();});
window.addEventListener('SouluExtensionsChanged',event=>{const value=event.detail;if(value.profile!==state.activeProfileId||value.incognito!==state.incognito)return;request++;items=value.items||[];draw();});
window.souluExtensionToolbar={refresh,get items(){return items;},get lastError(){return lastError;}};refresh();
})();
