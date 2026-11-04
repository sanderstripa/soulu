/* Soulu consent/settings; VOT itself owns the compact controls on videos. */
(()=>{
if(!location.pathname.endsWith('/settings.html'))return;
const invoke=(action,payload)=>new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action,payload}),onSuccess:s=>resolve(JSON.parse(s)),onFailure:(_,e)=>reject(Error(e))}));
const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
window.souluVideoSettings={open(){souluSettings.dialog('Перевод YouTube · VOT',box=>{
 const status=el('p','Проверка встроенного компонента…');status.setAttribute('role','status');
 const note=el('p','VOT передаёт адрес видео и данные запроса внешним серверам Яндекса/VOT. Это отдельная функция от локального перевода страниц Gecko. Перевод запускается кнопкой VOT на видео; громкость, язык и возврат оригинального звука регулируются там же.');note.className='note';
 const details=el('details'),summary=el('summary','Разрешения компонента');details.append(summary);const permissions=el('pre');permissions.style.cssText='white-space:pre-wrap;max-height:160px;overflow:auto;font:inherit';details.append(permissions);
 const consent=el('input');consent.type='checkbox';consent.id='gecko-vot-consent';const label=el('label');label.append(consent,document.createTextNode('Разрешаю включить встроенный VOT и обращаться к внешнему сервису перевода.'));
 const install=el('button','Включить встроенный VOT 1.12.6');install.type='button';install.id='gecko-vot-install';install.disabled=true;
 consent.onchange=()=>install.disabled=!consent.checked;install.onclick=async()=>{install.disabled=true;status.textContent='Проверка подписи встроенного компонента…';try{const r=await invoke('browser.vot.install',{consent:consent.checked});status.textContent='VOT '+r.version+' установлен. Откройте или обновите страницу видео.';await souluSettings.reload();}catch(e){status.textContent=e.message;install.disabled=false;}};
 box.append(note,status,details,label,install);
 invoke('browser.vot.status').then(r=>{permissions.textContent=JSON.stringify(r.permissions,null,2);status.textContent=r.installed?'VOT '+r.version+(r.enabled?' включён.':' отключён.'):'Подписанный VOT готов к установке после согласия.';if(r.installed){label.hidden=install.hidden=true;const toggle=el('button',r.enabled?'Отключить VOT':'Включить VOT');toggle.type='button';toggle.onclick=async()=>{await invoke('browser.vot.setEnabled',{enabled:!r.enabled});await souluSettings.reload();document.getElementById('actionDialog').close();};box.append(toggle);}}).catch(e=>{status.textContent=e.message;install.disabled=true;});
 });}};
const watch=()=>{const n=document.getElementById('videoTranslationEnabled');if(n)invoke('browser.vot.status').then(r=>{n.disabled=!r.installed;n.title=r.installed?'Озвучка через подписанное расширение VOT':'Сначала установите VOT в настройках перевода YouTube.';}).catch(()=>n.disabled=true);};
new MutationObserver(watch).observe(document.getElementById('sectionContent'),{childList:true});
})();
