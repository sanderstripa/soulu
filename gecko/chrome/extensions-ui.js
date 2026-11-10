/* Original Soulu action slots; native events, stable buttons and no polling. */
(()=>{
'use strict';const api=window.browserShell;if(!api)return;let state={},items=[],request=0,last='',lastError='';
function slots(){const r=document.querySelector('.classic-address-wrap')?.getBoundingClientRect();if(!r)return 1;const reserve=Math.max(...['sidebarButton','backButton','geckoForward'].map(id=>document.getElementById(id)?.getBoundingClientRect().right||0))+8;const available=state.settings?.addressPosition==='left'?innerWidth-r.x-380:r.x-reserve-(state.settings?.vpnToolbarVisible===false?0:38);return Math.max(1,Math.floor(available/32));}
function invokeAction(button,operation,id){const r=button.getBoundingClientRect();lastError='';return api.extensions(operation,{profile:state.activeProfileId,...(id?{id}:{}),tabId:state.activeTabId,generation:state.page?.generation,anchor:{x:r.x,y:r.y,width:r.width,height:r.height}}).catch(error=>{lastError=error.message;button.title=lastError;console.error('Soulu extension:',error);});}
function makeButton(id){const b=document.createElement('button');b.type='button';b.className='toolbar-button extension-action';b.dataset.extensionId=id;b.onclick=()=>invokeAction(b,'open',id);return b;}
function updateButton(b,item){
 const title=item.title||item.name;if(b.title!==title)b.title=title;if(b.getAttribute('aria-label')!==title)b.setAttribute('aria-label',title);b.disabled=!item.actionEnabled;
 let icon=b.querySelector('[data-action-icon]');const image=/^data:image\//.test(item.icon||'');if(!icon||(icon.tagName==='IMG')!==image){icon?.remove();icon=document.createElement(image?'img':'span');icon.dataset.actionIcon='true';if(image)icon.alt='';b.prepend(icon);}if(image){if(icon.getAttribute('src')!==item.icon)icon.src=item.icon;}else if(icon.textContent!==item.name.slice(0,1))icon.textContent=item.name.slice(0,1);
 let badge=b.querySelector('.gecko-extension-badge');if(!item.badge){badge?.remove();return;}if(!badge){badge=document.createElement('span');badge.className='gecko-extension-badge';b.append(badge);}if(badge.textContent!==item.badge)badge.textContent=item.badge;const rgba=a=>Array.isArray(a)&&a.length===4&&a.every(Number.isFinite)?`rgba(${a[0]},${a[1]},${a[2]},${a[3]/255})`:'';const background=rgba(item.badgeColor),color=rgba(item.badgeTextColor);if(badge.style.backgroundColor!==background)badge.style.backgroundColor=background;if(badge.style.color!==color)badge.style.color=color;
}
function draw(){
 const controls=document.querySelector('.classic-navigation-right');if(!controls)return;
 const host=document.querySelector('[data-extension-toolbar="classic"]');if(host)host.replaceChildren();document.body.style.setProperty('--extension-toolbar-width','0px');
 let button=document.getElementById('soulu-extensions-menu');if(!button){button=document.createElement('button');button.id='soulu-extensions-menu';button.className='toolbar-button extension-action';button.dataset.extensionOverflow='true';button.title='Расширения';button.setAttribute('aria-label','Расширения');button.innerHTML='<svg viewBox="0 0 24 24"><path d="M4 4h6V2a2 2 0 0 1 4 0v2h6v6h2a2 2 0 0 1 0 4h-2v6h-6v-2a2 2 0 0 0-4 0v2H4Z"/></svg>';button.onclick=()=>invokeAction(button,'overflow');const caption=controls.querySelector('.window-controls');caption.insertBefore(button,caption.querySelector('#windowMinimize'));}
 button.hidden=state.settings?.showExtensions===false;
}
async function refresh(){const ticket=++request;try{const current=await api.getState();state=current;const value=await api.extensions('list',{profile:current.activeProfileId});if(ticket!==request)return;items=value.items||[];draw();}catch(error){console.error(error);}}
api.onState(value=>{const changed=state.activeProfileId!==value.activeProfileId||state.incognito!==value.incognito||state.settings?.theme!==value.settings?.theme;state=value;if(changed)refresh();else draw();});
window.addEventListener('SouluExtensionsChanged',event=>{const value=event.detail;if(value.profile!==state.activeProfileId||value.incognito!==state.incognito)return;request++;items=value.items||[];draw();});
window.addEventListener('resize',draw);window.souluExtensionToolbar={refresh,get items(){return items;},get lastError(){return lastError;}};refresh();
})();
