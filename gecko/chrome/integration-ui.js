/* Additional commands on the existing Soulu UI, without replacing its components. */
(()=>{
const api=window.browserShell;if(!api)return;
const invoke=(action,payload)=>new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action,payload}),onSuccess:s=>resolve(JSON.parse(s)),onFailure:(_,e)=>reject(Error(e))}));
const error=e=>{const n=document.getElementById('actionMessage');if(n)n.textContent=e.message;else console.error(e);};
const button=(text,fn)=>{const n=document.createElement('button');n.textContent=text;n.onclick=()=>Promise.resolve().then(fn).catch(error);return n;};
if(location.pathname.endsWith('/settings.html')){
 const ui=window.souluSettings;
 if(window.souluBrowserImport)window.souluBrowserImport.open=()=>ui.dialog('Импорт и экспорт',box=>{
  const note=document.createElement('p');note.className='note';note.textContent='Мастер Firefox показывает доступные браузеры и типы данных. Защищённые пароли поддерживаются только там, где это разрешает исходный браузер. CSV содержит пароли открытым текстом: удалите экспорт после импорта.';
  const result=document.createElement('p');result.className='note';const act=async(action,payload)=>{const r=await invoke(action,payload);result.textContent=r.canceled?'Отменено':JSON.stringify(r);};
  box.append(note,button('Из установленного браузера…',()=>act('browser.import.native')),button('Закладки из HTML…',()=>act('browser.import.filePicker','bookmarks')),button('Пароли из CSV…',()=>act('browser.import.filePicker','passwords')),button('Экспорт закладок в HTML…',()=>act('browser.import.exportBookmarks')),result);
 });
 new MutationObserver(()=>{for(const row of document.querySelectorAll('.profile-row[data-profile-id]')){if(row.querySelector('[data-rename]'))continue;const b=button('Переименовать',async()=>{const name=prompt('Название профиля',row.querySelector('b')?.textContent||'');if(name===null)return;await ui.flush();await invoke('browser.profile.rename',{id:row.dataset.profileId,name});row.querySelector('b').textContent=name;});b.dataset.rename='true';row.append(b);}}).observe(document.getElementById('actionDialog'),{childList:true,subtree:true});
 return;
}
if(!location.pathname.endsWith('/index.html'))return;
let snapshot={},drag=null,suppress=0;
api.onState(value=>{snapshot=value;const back=document.getElementById('backButton');if(back&&!document.getElementById('geckoForward')){const b=back.cloneNode(true);b.id='geckoForward';b.title='Вперёд';b.setAttribute('aria-label','Вперёд');b.style.transform='rotate(180deg)';b.onclick=()=>invoke('browser.forward').catch(error);back.after(b);}const forward=document.getElementById('geckoForward');if(forward)forward.hidden=!value.page?.canGoForward;});
document.addEventListener('contextmenu',async e=>{const n=e.target.closest('[data-tab-id]');if(!n)return;e.preventDefault();e.stopImmediatePropagation();const id=Number(n.dataset.tabId),tab=snapshot.tabs?.find(t=>t.id===id);if(!tab)return;const actions=['browser.pinTab','browser.reloadTab','browser.duplicateTab','browser.restoreTab','browser.closeOtherTabs','browser.closeTab'];const labels=[tab.pinned?'Открепить вкладку':'Закрепить вкладку','Обновить','Дублировать','Восстановить закрытую вкладку','Закрыть другие вкладки','Закрыть вкладку'];try{const choice=await api.showMenu(labels.map((label,i)=>({command:i+1,label})),e.clientX,e.clientY);if(choice)await invoke(actions[choice-1],id);}catch(e){error(e);}},true);
document.addEventListener('pointerdown',e=>{const n=e.target.closest('[data-tab-id]');if(e.button!==0||!n||e.target.closest('[data-close-tab],[data-mute-tab],button,input'))return;drag={n,id:Number(n.dataset.tabId),x:e.clientX,pointer:e.pointerId,moved:false};});
document.addEventListener('pointermove',e=>{if(!drag||drag.pointer!==e.pointerId)return;if(Math.abs(e.clientX-drag.x)>6){drag.moved=true;drag.n.classList.add('gecko-tab-dragging');}});
document.addEventListener('pointerup',e=>{if(!drag)return;const d=drag;drag=null;d.n.classList.remove('gecko-tab-dragging');if(!d.moved)return;suppress=performance.now()+250;const target=document.elementFromPoint(e.clientX,e.clientY)?.closest('[data-tab-id]');if(target&&Number(target.dataset.tabId)!==d.id)invoke(e.clientX>target.getBoundingClientRect().x+target.getBoundingClientRect().width/2?'browser.moveTabAfter':'browser.moveTabBefore',{id:d.id,targetId:Number(target.dataset.tabId)}).catch(error);});
document.addEventListener('pointercancel',()=>{drag?.n.classList.remove('gecko-tab-dragging');drag=null;});
document.addEventListener('click',e=>{if(performance.now()<suppress&&e.target.closest('[data-tab-id]')){e.preventDefault();e.stopImmediatePropagation();}},true);
let downloads=[];
function renderActions(){const rows=[...document.querySelectorAll('#downloadsList .download-row')];rows.forEach((row,i)=>{const d=downloads[i];if(!d||row.querySelector('.gecko-download-actions'))return;const box=document.createElement('div');box.className='gecko-download-actions';const add=(label,operation)=>box.append(button(label,async()=>{downloads=await invoke('browser.downloads.action',{id:d.id,operation});}));if(d.state==='progressing')add('Отмена','cancel');else{if(d.state==='completed'){add('Открыть','open');add('Папка','reveal');}else add('Повторить','retry');add('Убрать','remove');}row.append(box);});}
api.onDownloads(value=>{downloads=value;queueMicrotask(renderActions);});const get=api.getDownloads;api.getDownloads=async()=>{downloads=await get();setTimeout(renderActions,0);return downloads;};
})();
