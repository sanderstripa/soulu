(() => {
  'use strict';
  const names={bookmarks:['Закладки и папки','Bookmarks and folders'],history:['История посещений','Browsing history'],passwords:['Сохранённые пароли','Saved passwords'],autofill:['Автозаполнение','Autofill'],tabs:['Открытые вкладки','Open tabs'],favicons:['Значки сайтов','Favicons'],preferences:['Настройки браузера','Browser preferences'],other:['Другие данные','Other data']};
  const statuses={available:['Доступно','Available'],not_found:['Не найдено','Not found'],action_required:['Требует действия','Action required'],unsupported:['Не поддерживается','Unsupported'],blocked:['Недоступно','Unavailable']};
  const reasons={
    passwords:['Экспортируйте пароли штатными средствами браузера и выберите CSV-файл.','Export passwords using the source browser, then choose its CSV file.'],
    autofill:['В Soulu нет поддерживаемого хранилища адресов и полей форм.','Soulu has no supported address and form autofill store.'],
    tabs:['Чтение сессий пока не проверено. Приватные вкладки и авторизация не переносятся.','Session reading is not verified. Private tabs and authentication are excluded.'],
    favicons:['Отдельная база значков пока не переносится. Поддерживаются безопасные значки в HTML-экспорте.','Separate favicon databases are not imported. Safe icons in HTML exports are supported.'],
    preferences:['Совместимость настроек с Soulu пока не проверена.','Preferences have no verified mapping to Soulu.'],
    other:['Для загрузок и расширений нет проверенного механизма переноса.','Downloads and extensions have no verified import binding.']
  };
  function parseHtml(text) {
    if(typeof text!=='string'||text.length>20*1024*1024||!/NETSCAPE-Bookmark-file-1/i.test(text)||!/<DL[\s>]/i.test(text))throw Error('Нужен стандартный HTML-экспорт закладок.');
    // Retain only structural bookmark tags. Never adopt exported DOM, execute
    // scripts or request remote images/resources from an untrusted export.
    const safe=text.replace(/<!--[\s\S]*?-->/g,'').replace(/<\/?([a-z][\w:-]*)\b[^>]*>/gi,(tag,name)=>['dl','dt','h3','a','p'].includes(name.toLowerCase())?tag:'');
    const doc=new DOMParser().parseFromString(safe,'text/html');let count=0;
    const parse=(dl,depth=0)=>{
      if(depth>64)throw Error('Слишком глубокая вложенность папок.');const nodes=[];
      for(const dt of [...dl.children].filter(n=>n.tagName==='DT')){
        if(++count>20000)throw Error('Слишком много закладок.');
        const a=dt.querySelector(':scope > a'),h=dt.querySelector(':scope > h3');
        if(a){const raw=a.getAttribute('href');let url;try{url=new URL(raw);}catch{continue;}if(!['https:','http:'].includes(url.protocol)||url.username||url.password)continue;
          const n={type:'url',name:a.textContent,url:url.href};const icon=a.getAttribute('icon');if(icon?.length<=65536&&/^data:image\/(png|x-icon);base64,/i.test(icon))n.favicon=icon;nodes.push(n);
        }else if(h){const nested=dt.querySelector(':scope > dl')||(dt.nextElementSibling?.tagName==='DL'?dt.nextElementSibling:null);nodes.push({type:'folder',name:h.textContent,children:nested?parse(nested,depth+1):[]});}
      }return nodes;
    };
    const root=doc.querySelector('dl');if(!root)throw Error('Неверная структура HTML-экспорта.');const nodes=parse(root);if(!count)throw Error('В файле нет закладок.');return nodes;
  }
  async function open() {
    const ui=window.souluSettings,api=window.browserShell,{t,el,button,dialog}=ui;
    const call=(action,payload)=>api.browserImport(action,payload);
    const state=await api.getState();
    const targets=(state.profiles||[]).filter(p=>p.id!=='__incognito__');
    const activeTarget=ui.persisted?.profile||state.activeProfileId;
    let phase='form',closed=false,source=null,caps=null,pending=true,serial=0,timer=null,cancelRequested=false;
    let sourceOptions=[],extraSources=[],checks=new Map();
    const modal=document.getElementById('actionDialog'),closeButton=document.getElementById('closeAction');
    const previousClose=closeButton.onclick;
    const label=(ru,en)=>t(ru,en);
    const categoryNames={...names,bookmarks:['Закладки и избранное','Bookmarks and favorites'],history:['История','History'],extensions:['Расширения','Extensions']};
    const basicKeys=['bookmarks','history','passwords','autofill','tabs'];
    let box,form,categoryList,notice,execution,summary,footer,consentBox,consent,newName,createField,run,cancel,done,from,to;
    const error=message=>{if(!closed){notice.textContent=message?.message||message;notice.hidden=!notice.textContent;}};
    const wrap=fn=>async()=>{try{await fn();}catch(e){error(e);} };
    function dropdown(id,title,onChoose) {
      const row=el('div',undefined,'import-select-row'),name=el('span',title),anchor=el('div',undefined,'import-select-anchor');
      name.id=id+'-label';
      const toggle=el('button',undefined,'import-select'),value=el('span',label('Выберите источник','Choose a source'));
      toggle.type='button';toggle.id=id;toggle.setAttribute('role','combobox');toggle.setAttribute('aria-labelledby',name.id);
      toggle.setAttribute('aria-haspopup','listbox');toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-controls',id+'-list');
      const chevron=window.souluSettingsIcons.create('chevron');chevron.setAttribute('aria-hidden','true');toggle.append(value,chevron);
      const list=el('div',undefined,'import-options');list.id=id+'-list';list.setAttribute('role','listbox');list.setAttribute('aria-labelledby',name.id);list.hidden=true;
      anchor.append(toggle,list);row.append(name,anchor);
      let entries=[],selected='',buttons=[];
      const hide=()=>{list.hidden=true;toggle.setAttribute('aria-expanded','false');};
      const available=()=>buttons.filter(b=>!b.disabled);
      function show(last=false){if(toggle.disabled)return;hideMenus();list.hidden=false;toggle.setAttribute('aria-expanded','true');const valid=available();const chosen=buttons.find(b=>b.dataset.value===selected&&!b.disabled);(chosen||valid[last?valid.length-1:0])?.focus();}
      toggle.onclick=()=>list.hidden?show():hide();
      toggle.onkeydown=e=>{if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();show(e.key==='ArrowUp');}};
      list.onkeydown=e=>{const valid=available(),index=valid.indexOf(document.activeElement);if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();valid[e.key==='Home'?0:e.key==='End'?valid.length-1:(index+(e.key==='ArrowDown'?1:-1)+valid.length)%valid.length]?.focus();}
        if(e.key==='Escape'){e.preventDefault();e.stopPropagation();hide();toggle.focus();}if(e.key==='Tab')hide();};
      return {row,toggle,list,hide,get value(){return selected;},
        setValue(id,text){selected=id;value.textContent=text||entries.find(e=>e.id===id)?.text||label('Выберите источник','Choose a source');for(const b of buttons)b.setAttribute('aria-selected',String(b.dataset.value===id));},
        setOptions(items){entries=items;list.replaceChildren();buttons=items.map((entry,index)=>{const b=el('button',entry.text,'import-option'+(entry.separator?' import-option-divider':''));b.type='button';b.id=id+'-option-'+index;b.setAttribute('role','option');b.dataset.value=entry.id;b.setAttribute('aria-selected',String(entry.id===selected));b.disabled=!!entry.disabled;
          b.onclick=wrap(async()=>{hide();toggle.focus();await onChoose(entry);});list.append(b);return b;});},
        disable(disabled){toggle.disabled=disabled;if(disabled)hide();}
      };
    }
    function hideMenus(){from?.hide();to?.hide();}
    function targetChoices(){to.setOptions([...targets.map(p=>({id:p.id,text:p.name+(p.id===activeTarget?label(' · текущий',' · current'):'' )})),{id:'__new__',text:label('+ Новый профиль Soulu','+ New Soulu profile'),separator:true}]);}
    function sourceChoices(){from.setOptions([...sourceOptions,...extraSources,{id:'__html__',text:label('HTML-файл с закладками…','Bookmarks HTML file…'),separator:true},{id:'__tabs_html__',text:label('HTML-файл с вкладками…','Open tabs HTML file…')},{id:'__csv__',text:label('CSV-файл с паролями…','Passwords CSV file…')},{id:'__portable__',text:label('Другая папка профиля…','Other profile folder…')},{id:'__refresh__',text:label('Обновить список браузеров','Refresh browser list')}]);}
    function lock() {
      const busy=phase!=='form';
      from.disable(busy||pending==='picker'||pending==='discovery');to.disable(busy);
      newName.disabled=busy;consent.disabled=busy;
      for(const [key,check] of checks)check.disabled=busy||caps?.[key]?.status!=='available';
      const chosen=[...checks.values()].some(c=>c.checked&&!c.disabled);
      const destination=to.value==='__new__'?!!newName.value.trim():targets.some(p=>p.id===to.value);
      run.disabled=phase!=='form'||!!pending||!source||!chosen||!destination||(checks.get('passwords')?.checked&&!consent.checked);
      run.textContent=label(phase==='running'?'Импортируем…':phase==='creating'?'Создаём профиль…':'Импорт',phase==='running'?'Importing…':phase==='creating'?'Creating profile…':'Import');
      cancel.disabled=phase==='creating'||cancelRequested;
    }
    function shortReason(key,status) {
      if(status==='not_found')return label('В профиле не найдено','Not found in this profile');
      if(status==='blocked'&&key==='tabs'&&caps?.[key]?.reason?.includes('Encrypted'))return label('Защищённая сессия — выберите HTML-файл с вкладками','Protected session — choose Open tabs HTML');
      if(status==='blocked')return caps?.[key]?.reason?.startsWith('Close')?label('Закройте браузер и выберите профиль заново','Close the browser and select the profile again'):label('Источник недоступен','Source unavailable');
      if(key==='passwords')return label('Через CSV-экспорт из браузера','Use a browser CSV export');
      if(key==='autofill')return label('Сохранённые значения форм не найдены','Saved form values not found');
      if(key==='tabs')return label('Формат сессии недоступен — используйте HTML-экспорт','Session unavailable — use an HTML export');
      return label('Перенос не поддерживается','Import is not supported');
    }
    function drawCategories() {
      categoryList.replaceChildren();checks=new Map();
      const keys=source?.kind?[source.kind]:[...basicKeys,...Object.keys(caps||{}).filter(k=>!basicKeys.includes(k)&&categoryNames[k]&&caps[k].status==='available')];
      for(const key of keys){const value=caps?.[key],available=value?.status==='available';
        const row=el('label',undefined,'import-category'),check=el('input'),text=el('span',undefined,'import-category-copy');
        check.type='checkbox';check.dataset.category=key;check.disabled=!available;check.checked=available&&key!=='passwords';check.setAttribute('aria-label',label(...categoryNames[key]));
        text.append(el('span',label(...categoryNames[key]),'import-category-name'));
        if(value&&!available)text.append(el('small',shortReason(key,value.status)));
        if(available&&key==='autofill')text.append(el('small',label('Адреса и значения форм · без карт','Addresses and form values · excludes cards')));
        if(available&&key==='tabs')text.append(el('small',label('Откроются в выбранном профиле','Will open in the selected profile')));
        if(available&&Number.isInteger(value.count))text.append(el('small',value.count.toLocaleString(),'import-count'));
        row.append(check,text);categoryList.append(row);checks.set(key,check);check.onchange=()=>{consentBox.hidden=!checks.get('passwords')?.checked;lock();};
      }
      consentBox.hidden=!checks.get('passwords')?.checked;consent.checked=false;
      createField.hidden=to.value!=='__new__';lock();
    }
    async function inspect(chosen) {
      const token=++serial;source=chosen;caps=null;pending='capabilities';notice.hidden=true;
      from.setValue(chosen.id,chosen.text);drawCategories();execution.hidden=false;execution.textContent=label('Проверяем доступные данные…','Checking available data…');
      try{const result=await call('capabilities',{source:chosen.id});if(closed||token!==serial)return;if(result.status==='error')throw Error(result.message);caps=result;}
      catch(e){if(closed||token!==serial)return;error(e);caps=Object.fromEntries(basicKeys.map(key=>[key,{status:'blocked'}]));}
      if(closed||token!==serial)return;pending=false;execution.hidden=true;drawCategories();
    }
    async function chooseSource(entry) {
      if(entry.id==='__refresh__')return discover();
      if(!['__html__','__tabs_html__','__csv__','__portable__'].includes(entry.id))return entry.kind?selectFile(entry):inspect(entry);
      const token=++serial;pending='picker';notice.hidden=true;execution.hidden=true;lock();
      try{
        const portable=entry.id==='__portable__',kind=entry.id==='__html__'?'bookmarks':entry.id==='__tabs_html__'?'tabs':'passwords';
        const selected=await call(portable?'portable':'file',portable?undefined:{kind});
        if(closed||token!==serial)return;
        pending=false;if(!selected?.id){lock();if(source&&!caps)await inspect(source);return;}
        if(portable){const chosen={...selected,text:label('Папка профиля · ','Profile folder · ')+selected.name};extraSources.push(chosen);sourceChoices();return inspect(chosen);}
        if(selected.kind!==kind)throw Error(label('Формат файла не соответствует выбранному источнику.','The file does not match the selected source format.'));
        const chosen={id:selected.id,kind,name:selected.name,text:label(kind!=='passwords'?'HTML · ':'CSV · ',kind!=='passwords'?'HTML · ':'CSV · ')+selected.name};
        if(kind!=='passwords')chosen.nodes=parseHtml(selected.text);
        extraSources.push(chosen);sourceChoices();selectFile(chosen);
      }catch(e){if(closed||token!==serial)return;pending=false;error(e);lock();}
    }
    function selectFile(chosen){++serial;source=chosen;pending=false;from.setValue(chosen.id,chosen.text);caps={[chosen.kind]:{status:'available'}};
      if(chosen.nodes){let count=0;const walk=nodes=>{for(const n of nodes)n.type==='folder'?walk(n.children):++count;};walk(chosen.nodes);caps[chosen.kind].count=count;}
      notice.hidden=true;execution.hidden=true;drawCategories();
    }
    async function discover() {
      const token=++serial;pending='discovery';source=null;caps=null;from.setValue('',label('Ищем браузеры…','Finding browsers…'));notice.hidden=true;execution.hidden=true;drawCategories();
      try{const catalog=await call('catalog');if(closed||token!==serial)return;
        sourceOptions=catalog.flatMap(b=>b.profiles.length?b.profiles.map(p=>({...p,text:b.browser+' · '+p.name})): [{id:'unavailable:'+b.browser,text:b.browser+label(' · профили недоступны',' · no accessible profiles'),disabled:true}]);
        sourceChoices();from.setValue('',label('Выберите браузер или файл','Choose a browser or file'));
        if(!catalog.some(b=>b.profiles.length))error(label('Браузеры с доступными профилями не найдены. Выберите файл или папку профиля.','No accessible browser profiles found. Choose a file or profile folder.'));
      }catch(e){if(closed||token!==serial)return;sourceOptions=[];sourceChoices();from.setValue('',label('Выберите файл или папку профиля','Choose a file or profile folder'));error(e);}
      if(closed||token!==serial)return;pending=false;lock();
    }
    async function requestCancel(){if(phase==='running'){cancelRequested=true;lock();execution.textContent=label('Отменяем… Уже перенесённые записи сохранятся.','Cancelling… Entries already imported will remain.');try{await call('cancel');}catch(e){cancelRequested=false;lock();error(e);}}else if(phase!=='creating')modal.close();}
    async function execute() {
      if(run.disabled)return;hideMenus();notice.hidden=true;
      const selected=source,chosen=Object.fromEntries([...checks].map(([key,c])=>[key,c.checked&&!c.disabled]));
      const approved=consent.checked;let destination=to.value;
      if(destination==='__new__'){
        phase='creating';box.dataset.importState=phase;execution.hidden=false;execution.textContent=label('Создаём профиль Soulu…','Creating a Soulu profile…');lock();
        try{await ui.flush();const profile=await call('createProfile',{name:newName.value.trim()});if(!profile?.id)throw Error(label('Не удалось создать профиль.','Could not create a profile.'));
          if(closed)return;targets.push(profile);targetChoices();to.setValue(profile.id);destination=profile.id;createField.hidden=true;
        }catch(e){if(closed)return;phase='form';box.dataset.importState=phase;execution.hidden=true;error(e);lock();return;}
      }
      phase='running';box.dataset.importState=phase;box.setAttribute('aria-busy','true');execution.hidden=false;execution.textContent=label('Импортируем выбранные данные…','Importing selected data…');lock();
      const payload={source:selected.id,target:destination,...chosen,consent:approved};if(selected.nodes)payload.nodes=selected.nodes;
      let pollPending=false;
      timer=setInterval(async()=>{if(pollPending)return;pollPending=true;try{const p=await call('progress');if(!closed&&phase==='running'&&!cancelRequested)execution.textContent=label(`Обработано записей: ${p.processed.toLocaleString()}`,`Entries processed: ${p.processed.toLocaleString()}`);}catch{}finally{pollPending=false;}},500);
      let result;try{result=await call('run',payload);}catch(e){result={status:'error',message:e.message};}finally{clearInterval(timer);box.removeAttribute('aria-busy');}
      if(!closed)finish(result);
    }
    function finish(result) {
      phase='result';box.dataset.importState=phase;cancelRequested=false;lock();
      form.querySelector('.import-categories-section').hidden=true;consentBox.hidden=true;createField.hidden=true;execution.hidden=true;
      const title=result.status==='ok'?label('Импорт завершён','Import complete'):result.status==='cancelled'?label('Импорт отменён','Import cancelled'):label('Импорт завершён с ошибками','Import completed with errors');
      summary.replaceChildren(el('p',title,'import-result-title'));summary.hidden=false;
      const totals={imported:0,skipped:0,failed:0},reports=Object.entries(result.categories||{});
      for(const [,r] of reports){totals.imported+=r.imported||0;totals.skipped+=r.skipped||0;totals.failed+=r.failed||0;if(r.status==='error'&&!r.failed)++totals.failed;}
      if(result.status==='error'&&!reports.length)++totals.failed;
      const counts=el('dl',undefined,'import-totals');for(const [key,ru,en] of [['imported','Импортировано','Imported'],['skipped','Пропущено','Skipped'],['failed','Ошибки','Errors']]){const item=el('div');item.append(el('dt',label(ru,en)),el('dd',totals[key].toLocaleString()));counts.append(item);}summary.append(counts);
      for(const [key,r] of reports){const text=el('p',label(...(categoryNames[key]||[key,key]))+' · '+label(`${r.imported||0} добавлено, ${r.skipped||0} пропущено`,`${r.imported||0} added, ${r.skipped||0} skipped`),'import-result-line');summary.append(text);if(r.message&&r.status!=='ok')summary.append(el('p',r.message,'note'));}
      if(result.message)error(result.message);
      if(result.status==='cancelled')summary.append(el('p',label('Уже перенесённые данные сохранены.','Entries already imported remain saved.'),'note'));
      cancel.hidden=true;run.hidden=true;done.hidden=false;done.focus();
    }
    dialog(label('Импорт из другого браузера','Import from another browser'),host=>{
      box=host;box.classList.add('browser-import');modal.classList.add('browser-import-dialog');box.dataset.importState='form';
      form=el('div',undefined,'import-form');from=dropdown('importFrom',label('Из','From'),chooseSource);to=dropdown('importTo',label('В','To'),async entry=>{to.setValue(entry.id);createField.hidden=entry.id!=='__new__';lock();if(entry.id==='__new__')newName.focus();});
      form.append(from.row,to.row);
      createField=el('label',undefined,'import-new-profile');createField.hidden=true;newName=el('input');newName.type='text';newName.maxLength=80;newName.placeholder=label('Название нового профиля','New profile name');newName.setAttribute('aria-label',label('Название нового профиля','New profile name'));newName.oninput=lock;createField.append(newName,el('small',label('Будет создан при запуске импорта','Created when you start the import')));form.append(createField);
      const section=el('section',undefined,'import-categories-section');section.append(el('p',label('Что импортировать','What to import'),'import-section-label'));categoryList=el('div');section.append(categoryList);form.append(section);
      consentBox=el('div',undefined,'import-csv-consent');consentBox.hidden=true;consentBox.append(el('p',label('Пароли сохраняются с защитой Windows. Для защищённых записей потребуется CSV-экспорт из браузера; CSV содержит открытый текст.','CSV contains unencrypted passwords. Existing credentials are preserved; the file is not deleted.'),'note'));
      const consentLabel=el('label',undefined,'import-consent');consent=el('input');consent.type='checkbox';consent.onchange=lock;consentLabel.append(consent,el('span',label('Разрешаю перенос паролей','Allow importing passwords')));consentBox.append(consentLabel);form.append(consentBox);
      notice=el('p',undefined,'import-notice');notice.hidden=true;notice.setAttribute('role','alert');execution=el('p',undefined,'import-execution');execution.hidden=true;execution.setAttribute('role','status');execution.setAttribute('aria-live','polite');summary=el('div',undefined,'import-summary');summary.hidden=true;summary.setAttribute('role','status');
      footer=el('div',undefined,'dialog-actions');cancel=button(label('Отмена','Cancel'),wrap(requestCancel),'import-cancel');run=button(label('Импорт','Import'),wrap(execute),'primary');done=button(label('Закрыть','Close'),()=>modal.close(),'primary');done.hidden=true;footer.append(cancel,run,done);box.append(form,notice,execution,summary,footer);
      targetChoices();to.setValue(targets.some(p=>p.id===activeTarget)?activeTarget:targets[0]?.id||'');
      drawCategories();
    });
    const outside=e=>{if(!e.target.closest('.import-select-anchor'))hideMenus();};
    const escape=e=>{if(phase==='running'||phase==='creating'){e.preventDefault();if(phase==='running')requestCancel().catch(error);}};
    closeButton.onclick=wrap(requestCancel);modal.addEventListener('pointerdown',outside);modal.addEventListener('cancel',escape);
    const cleanup=()=>{closed=true;++serial;clearInterval(timer);if(phase==='running')call('cancel').catch(()=>{});box.classList.remove('browser-import');modal.classList.remove('browser-import-dialog');closeButton.onclick=previousClose;modal.removeEventListener('pointerdown',outside);modal.removeEventListener('cancel',escape);modal.removeEventListener('close',cleanup);};modal.addEventListener('close',cleanup);
    await discover();if(!closed)from.toggle.focus();
  }
  window.souluBrowserImport={open,parseHtml};
})();
