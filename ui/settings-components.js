(()=>{
 'use strict';
 const manage=payload=>new Promise((resolve,reject)=>window.cefQuery({request:JSON.stringify({action:'browser.components.manage',payload}),persistent:false,onSuccess:raw=>{try{const result=JSON.parse(raw);result.ok===false?reject(Error(result.error||'Component operation failed')):resolve(result)}catch(e){reject(e)}},onFailure:(_,message)=>reject(Error(message))}));
 function render(host){
  if(host.dataset.ready)return;host.dataset.ready='true';
  const ui=window.souluSettings,{el,t,button}=ui;
  for(const id of ['xray','sudoku']){
   const card=el('section',undefined,'component-card'),heading=el('h4',id==='xray'?'Xray':'Sudoku'),installed=el('p',t('Определение версии…','Reading installed version…'),'note'),latest=el('p','','note'),note=el('p','','note'),error=el('p','','note error'),actions=el('div',undefined,'component-actions'),select=el('select'),custom=el('input');
   select.setAttribute('aria-label',t('Версия компонента','Component release'));select.disabled=true;custom.type='text';custom.placeholder='v…';custom.hidden=true;custom.setAttribute('aria-label',t('Тег версии','Release tag'));
   let snapshot={},releases=[],busy=false;
   function state(value){snapshot=value;installed.textContent=t('Установлена: ','Installed: ')+(value.installed||t('Не определена','Unknown'));latest.textContent=[t('Стабильная: ','Stable: ')+(value.latestStable||'—'),t('Предварительная: ','Preview: ')+(value.latestPreview||'—')].join(' · ');rollback.disabled=busy||!value.previous;rollback.title=value.previous?t('Вернуть ','Restore ')+value.previous:'';if(value.error)error.textContent=value.error;}
   async function run(fn){if(busy)return;busy=true;error.textContent='';for(const control of [check,install,rollback,select,custom])control.disabled=true;try{await fn()}catch(e){error.textContent=e.message||String(e)}finally{busy=false;check.disabled=false;select.disabled=!releases.length;custom.disabled=false;install.disabled=!releases.length&&custom.hidden;rollback.disabled=!snapshot.previous;}}
   const check=button(t('Проверить версии','Check releases'),()=>run(async()=>{note.textContent=t('Проверка официального источника…','Checking the official source…');const result=await manage({component:id,operation:'list'});state(result);releases=result.releases||[];select.replaceChildren();for(const row of releases)select.append(new Option(row.version+(row.prerelease?t(' · предварительная',' · preview'):''),row.version));select.append(new Option(t('Указать другой тег…','Enter another tag…'),'custom'));select.value=result.latestStable||releases[0]?.version||'custom';custom.hidden=select.value!=='custom';note.textContent=t('Выберите стабильный или предварительный выпуск. Для более старой версии можно указать точный тег.','Choose a stable or preview release. Enter an exact tag for an older release.');}));
   const install=button(t('Установить','Install'),()=>run(async()=>{const version=select.value==='custom'?custom.value.trim():select.value;if(!version)throw Error(t('Укажите версию.','Enter a release tag.'));note.textContent=t('Загрузка и проверка компонента…','Downloading and verifying the component…');await manage({component:id,operation:'install',version});state(await manage({component:id,operation:'status'}));note.textContent=t('Версия установлена. Для действующего соединения переподключите VPN.','Version installed. Reconnect an active VPN to use it.');}));install.disabled=true;
   const rollback=button(t('Откатить','Roll back'),()=>run(async()=>{await manage({component:id,operation:'rollback'});state(await manage({component:id,operation:'status'}));note.textContent=t('Предыдущая версия восстановлена. Переподключите действующий VPN.','Previous version restored. Reconnect an active VPN.');}));rollback.disabled=true;
   select.onchange=()=>{custom.hidden=select.value!=='custom';if(!custom.hidden)custom.focus();};
   actions.append(check,select,custom,install,rollback);card.append(heading,installed,latest,actions,note,error);host.append(card);
   manage({component:id,operation:'status'}).then(state).catch(e=>error.textContent=e.message);
  }
 }
 window.souluComponents={render};
})();
