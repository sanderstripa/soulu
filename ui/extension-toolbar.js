(() => {
  'use strict';
  let profile='',items=[],request=0;
  const getProfile=state=>state.incognito?'__incognito__':state.activeProfileId;
  function draw(){
    for(const host of document.querySelectorAll('[data-extension-toolbar]')){
      host.replaceChildren();
      for(const item of items.filter(e=>e.enabled&&e.pinned&&e.action)){
        const button=document.createElement('button');button.type='button';
        button.className=host.dataset.extensionToolbar==='compact'?'compact-control extension-action':'toolbar-button extension-action';
        button.dataset.extensionId=item.id;button.title=item.name;button.setAttribute('aria-label',item.name);
        if(/^data:image\/(png|webp|jpeg|gif);base64,/i.test(item.icon||'')){const icon=document.createElement('img');icon.src=item.icon;icon.alt='';button.append(icon);}
        else button.textContent=item.name.slice(0,1);
        button.onclick=async()=>{button.disabled=true;try{await window.browserShell.extensions('open',{profile,id:item.id});}catch(error){button.title=error.message;console.error('Extension action:',error);}finally{button.disabled=false;}};
        host.append(button);
      }
      document.body.style.setProperty('--extension-toolbar-width',`${host.children.length*32}px`);
    }
  }
  async function refresh(){
    const state=await window.browserShell.getState(),next=getProfile(state);if(!next)return;
    const serial=++request;if(next!==profile){profile=next;items=[];draw();}
    if(next==='__incognito__')return;
    try{const data=await window.browserShell.extensions('list',{profile:next});if(serial!==request||data.profile!==profile)return;items=data.items||[];draw();}
    catch(error){console.error('Extensions:',error);}
  }
  window.browserShell.onState(state=>{const next=getProfile(state);if(next&&next!==profile){profile=next;items=[];draw();refresh();}});
  window.souluExtensionToolbar={refresh,get items(){return items;}};
  refresh();setInterval(refresh,2000);
})();
