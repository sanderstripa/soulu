/* The import flow belongs to Soulu, on both welcome and Settings pages. */
(()=>{
const invoke=(action,payload)=>new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action,payload}),onSuccess:s=>resolve(JSON.parse(s)),onFailure:(_,e)=>reject(Error(e))}));
window.souluOpenImport=async()=>{
 let previous=document.getElementById('soulu-import');if(previous){previous.showModal();return;}
 const modal=document.createElement('dialog');modal.id='soulu-import';modal.className='soulu-import';
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const title=el('h2','Импорт данных'),description=el('p','Выберите браузер, профиль и данные для переноса в Soulu.'),select=el('select'),fields=el('fieldset'),status=el('p','Поиск установленных браузеров…'),actions=el('div');
 select.id='soulu-import-source';select.setAttribute('aria-label','Браузер и профиль');fields.id='soulu-import-types';status.id='soulu-import-status';status.setAttribute('role','status');actions.className='soulu-import-actions';
 const button=(text,fn)=>{const n=el('button',text);n.type='button';n.onclick=fn;return n;};
 const close=button('Закрыть',()=>modal.close()),start=button('Импортировать',async()=>{
  const types=[...fields.querySelectorAll('input:checked')].map(n=>n.value);if(!types.length){status.textContent='Выберите данные для импорта.';return;}
  start.disabled=select.disabled=true;fields.disabled=true;close.disabled=true;status.textContent='Перенос данных…';
  try{const result=await invoke('browser.import.run',{id:select.value,types});if(result.ok){completed.add(select.value);select.selectedOptions[0].textContent+=' — OK';start.textContent='OK';}status.textContent=result.ok?'Импорт завершён. Данные сохранены в Soulu.':'Импорт завершён частично. Не удалось перенести: '+result.results.filter(r=>!r.success).map(r=>available.find(s=>s.id===select.value)?.types.find(t=>t.key===r.type)?.label||r.type).join(', ');}
  catch(e){status.textContent=e.message;}
  finally{start.disabled=completed.has(select.value);select.disabled=false;fields.disabled=false;close.disabled=false;}
 });start.id='soulu-import-start';start.className='primary';start.disabled=true;
 const file=button('Закладки из HTML…',async()=>{try{const r=await invoke('browser.import.filePicker','bookmarks');status.textContent=r.canceled?'Отменено':'Закладки импортированы.';}catch(e){status.textContent=e.message;}});
 const passwords=button('Пароли из CSV…',async()=>{try{const r=await invoke('browser.import.filePicker','passwords');status.textContent=r.canceled?'Отменено':`Добавлено паролей: ${r.added||0}. Обновлено: ${r.modified||0}. Ошибок: ${r.failed||0}.`;}catch(e){status.textContent=e.message;}});
 actions.append(file,passwords,close,start);modal.append(title,description,select,fields,el('p','Если исходный браузер защищает пароли от прямого переноса, экспортируйте их в CSV и выберите «Пароли из CSV…».'),status,actions);document.body.append(modal);
 modal.addEventListener('close',()=>modal.remove(),{once:true});modal.addEventListener('cancel',e=>{if(close.disabled)e.preventDefault();});modal.showModal();let available=[];const completed=new Set();
 try{available=(await invoke('browser.import.sources')).sources;for(const row of available){if(row.completed)completed.add(row.id);select.append(new Option(row.name+' — '+row.profile+(row.completed?' — OK':''),row.id));}
  const render=()=>{fields.replaceChildren();for(const type of available.find(s=>s.id===select.value)?.types||[]){const row=el('label'),n=el('input');n.type='checkbox';n.value=type.key;n.checked=true;row.append(n,document.createTextNode(type.label));fields.append(row);}start.disabled=!available.length||completed.has(select.value);start.textContent=completed.has(select.value)?'OK':'Импортировать';};select.onchange=render;render();status.textContent=available.length?'Выберите данные и нажмите «Импортировать».':'Браузеры с доступными данными не найдены. Можно импортировать закладки из HTML и пароли из CSV.';
 }catch(e){status.textContent=e.message;}
};
window.addEventListener('SouluEmit',e=>{try{if(JSON.parse(e.detail).name==='openImport')window.souluOpenImport();}catch{}});
})();
