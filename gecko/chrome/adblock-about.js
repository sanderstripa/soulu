(()=>{
if(!location.pathname.endsWith('/settings.html'))return;
const invoke=(action)=>new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action}),onSuccess:s=>resolve(JSON.parse(s)),onFailure:(_,e)=>reject(Error(e))}));
function render(){
 const host=document.querySelector('[data-adblock-manager]');
 if(!host||host.dataset.ready)return;
 host.dataset.ready='true';
 const en=document.documentElement.lang==='en';
 const note=document.createElement('p'),status=document.createElement('p'),update=document.createElement('button');
 note.className=status.className='note';status.setAttribute('role','status');
 note.textContent=en?'adblock-rust 0.13.3 · The core is updated with Sona. Filter lists can be updated separately.':'adblock-rust 0.13.3 · Ядро обновляется вместе с Sona. Списки фильтров обновляются отдельно.';
 update.textContent=en?'Update filter lists':'Обновить списки фильтров';
 const show=r=>{
  if(!host.isConnected)return;
  status.textContent=r.lastUpdateError||(r.ready?
   (en?'Active rules: ':'Активные правила: ')+(r.networkRules||0)+' / '+(r.cosmeticRules||0)+
   (r.lastSuccessfulUpdate?' · '+new Date(r.lastSuccessfulUpdate*1000).toLocaleString(): '')
   :(en?'Blocker is initializing…':'Блокировщик загружается…'));
  update.disabled=!r.ready||r.updating;
  if(r.updating||!r.ready)setTimeout(()=>invoke('browser.adblock.status').then(show).catch(e=>status.textContent=e.message),1000);
 };
 update.onclick=async()=>{
  update.disabled=true;status.textContent=en?'Downloading and compiling filters…':'Загрузка и компиляция фильтров…';
  try{show(await invoke('browser.adblock.update'));}
  catch(e){status.textContent=e.message;update.disabled=false;}
 };
 host.append(note,update,status);
 invoke('browser.adblock.status').then(show).catch(e=>status.textContent=e.message);
}
new MutationObserver(render).observe(document.getElementById('sectionContent'),{childList:true,subtree:true});render();
})();
