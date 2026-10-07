(() => {
  'use strict';
  const api=window.browserShell;
  if(!api) return;
  let state={}, rows=[], parent=0, query='', drag=0, busy=false, manage=false, pane='list';
  const el=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls||'';if(text)n.textContent=text;return n;};
  const button=(text,fn)=>{const b=el('button','nav-action',text);b.type='button';b.onclick=()=>Promise.resolve(fn()).catch(error=>alert(error.message));return b;};
  const bar=el('nav','bookmarks-bar');bar.setAttribute('aria-label','Панель закладок');document.body.append(bar);
  const menu=el('section','bookmarks-menu');menu.hidden=true;document.body.append(menu);
  const shield=el('div','navigation-shield');shield.hidden=true;document.body.append(shield);
  const overview=el('section','tab-overview');overview.hidden=true;document.body.append(overview);
  const head=el('div','overview-head'), search=el('input','navigation-search');search.placeholder='Поиск вкладок';search.setAttribute('aria-label','Поиск вкладок');
  head.append(el('h1','','Обзор вкладок'),search);overview.append(head);
  const grid=el('div','overview-grid');overview.append(grid);search.oninput=renderOverview;
  const menuSearch=el('input','navigation-search');menuSearch.placeholder='Поиск закладок';menuSearch.setAttribute('aria-label','Поиск закладок');menuSearch.oninput=()=>{pane='list';query=menuSearch.value;renderMenu();};
  const contents=el('div','bookmark-tree'), actions=el('div','bookmark-actions');
  menu.append(menuSearch,contents,actions);
  const nextId=()=>rows.reduce((n,r)=>Math.max(n,Number(r.id)||0),0)+1;
  const children=id=>rows.filter(r=>(r.parentId||0)===id).sort((a,b)=>(a.order||0)-(b.order||0));
  const descendants=id=>{const found=new Set([id]);let changed=true;while(changed){changed=false;for(const r of rows)if(found.has(r.parentId)&&!found.has(r.id)){found.add(r.id);changed=true;}}return found;};
  async function persist(next){if(busy)throw Error('Дождитесь сохранения');busy=true;try{rows=await api.replaceBookmarks(next);render();}finally{busy=false;}}
  const updatePopover=()=>{const open=Boolean(document.querySelector('.bookmark-context'));shield.hidden=!(open||editor);return api.setPopover(open,'bookmarks');};
  const closeMenu=()=>{pane='list';menu.hidden=true;api.setBookmarksSidebar(false);document.querySelector('.bookmark-context')?.remove();updatePopover();api.setSuggestionsHeight(0);};
  async function openMenu(id=0,editor=false){await api.setOverview(false);rows=await api.getBookmarks();parent=id;manage=editor;pane='list';query='';menuSearch.value='';menu.hidden=false;await api.setBookmarksSidebar(true);await updatePopover();renderMenu();menuSearch.focus();}
  function icon(row){const n=el('span','bookmark-icon',row.type==='folder'?'▱':'◉');if(row.favicon&&row.type!=='folder'){const im=el('img');im.src=row.favicon;im.alt='';im.onerror=()=>im.remove();n.replaceChildren(im);}return n;}
  function item(row,compact=false){const b=button('',()=>row.type==='folder'?openMenu(row.id,manage):(closeMenu(),api.openBookmark(row.url)));b.classList.add('bookmark-item');b.title=row.title||row.url;b.setAttribute('aria-label',b.title);b.append(icon(row),el('span','bookmark-label',row.title||row.url));if(compact&&(state.settings?.bookmarksIconsOnly||row.hideTitle))b.classList.add('icons-only');b.dataset.bookmarkId=String(row.id);b.draggable=false;b.onpointerdown=e=>{if(e.button===0){gesture={id:row.id,x:e.clientX,y:e.clientY,pointer:e.pointerId,node:b,active:false};b.setPointerCapture(e.pointerId);}};b.ondragstart=e=>{drag=row.id;e.dataTransfer.setData('text/plain',String(row.id));};b.ondragend=()=>{drag=0;};b.ondragover=e=>{if(drag)e.preventDefault();};b.ondrop=e=>{e.preventDefault();e.stopPropagation();move(drag,row).catch(err=>alert(err.message));};b.oncontextmenu=e=>{e.preventDefault();context(row,e);};return b;}
  // Internal pointer dragging also works in the native OSR shell, which does
  // not implement the operating system's HTML drag/drop protocol.
  let gesture=null, ghost=null, consumeClick=false;
  const finishDrag=()=>{ghost?.remove();ghost=null;gesture=null;drag=0;api.setSuggestionsHeight(0);};
  document.addEventListener('pointermove',e=>{
    if(!gesture||e.pointerId!==gesture.pointer)return;
    if(!gesture.active&&Math.hypot(e.clientX-gesture.x,e.clientY-gesture.y)>6){
      gesture.active=true;drag=gesture.id;ghost=gesture.node.cloneNode(true);ghost.classList.add('bookmark-drag-ghost');ghost.removeAttribute('data-bookmark-id');document.body.append(ghost);api.setSuggestionsHeight(innerHeight);
    }
    if(ghost){ghost.style.left=(e.clientX+12)+'px';ghost.style.top=(e.clientY+12)+'px';e.preventDefault();}
  });
  document.addEventListener('pointerup',e=>{
    if(!gesture||e.pointerId!==gesture.pointer)return;
    if(gesture.active){
      consumeClick=true;const target=document.elementFromPoint(e.clientX,e.clientY)?.closest('[data-bookmark-id]');const id=gesture.id;
      if(target){const row=rows.find(r=>r.id===Number(target.dataset.bookmarkId));if(row)move(id,row).catch(err=>alert(err.message));}
      else if(document.elementFromPoint(e.clientX,e.clientY)?.closest('.bookmarks-bar'))persist(rows.map(r=>r.id===id?{...r,parentId:0,order:rows.length}:r)).catch(err=>alert(err.message));
      setTimeout(()=>{consumeClick=false;},0);
    }
    finishDrag();
  });
  document.addEventListener('pointercancel',finishDrag);
  document.addEventListener('click',e=>{if(consumeClick){e.preventDefault();e.stopImmediatePropagation();}},true);
  async function move(id,target){if(!id||id===target.id)return;const moving=rows.find(r=>r.id===id);if(!moving||descendants(id).has(target.id))return;const next=rows.map(r=>({...r})), copy=next.find(r=>r.id===id);copy.parentId=target.type==='folder'?target.id:(target.parentId||0);const siblings=next.filter(r=>r.id!==id&&(r.parentId||0)===copy.parentId).sort((a,b)=>(a.order||0)-(b.order||0));const index=target.type==='folder'?siblings.length:siblings.findIndex(r=>r.id===target.id);siblings.splice(index,0,copy);siblings.forEach((r,i)=>r.order=i);await persist(next);}
  async function context(row,event){
    const en=state.settings?.language==='en',commands=[],items=[];
    const add=(ru,english,run)=>{commands.push(run);items.push({command:commands.length,label:en?english:ru});};
    add('Открыть','Open',()=>row.type==='folder'?openMenu(row.id):api.openBookmark(row.url));
    if(row.type!=='folder'){
      add('Открыть в новой вкладке','Open in new tab',()=>api.openTab(row.url));
      add('Открыть в фоновой вкладке','Open in background tab',()=>api.openTab(row.url,true));
    }
    add('Редактировать','Edit',()=>edit(row));
    add(row.hideTitle?'Показать подпись':'Скрыть подпись',row.hideTitle?'Show label':'Hide label',()=>persist(rows.map(r=>r.id===row.id?{...r,hideTitle:!r.hideTitle}:r)));
    add('Переместить в корень','Move to root',()=>persist(rows.map(r=>r.id===row.id?{...r,parentId:0,order:rows.length}:r)));
    add('Удалить','Delete',()=>{const ids=descendants(row.id);if(row.type==='folder'&&ids.size>1&&!confirm(en?'Delete folder and its bookmarks?':'Удалить папку со всеми закладками?'))return;return persist(rows.filter(r=>!ids.has(r.id)));});
    const rect=event.currentTarget?.getBoundingClientRect();
    const command=await api.showMenu(items,event.clientX||rect?.left||0,event.clientY||rect?.bottom||document.querySelector(".browser-toolbar:not([hidden])")?.getBoundingClientRect().bottom||0);
    if(command>0&&commands[command-1])await commands[command-1]();
  }

  let editor=null, editorReturn=null, editorGeneration=0;
  const profileKey=()=>String(state.activeProfileId)+':'+String(state.incognito);
  function closeEditor(restore=true){++editorGeneration;if(!editor)return;editor.remove();editor=null;api.setPopover(false,'bookmark-editor');updatePopover();if(restore&&editorReturn?.isConnected)editorReturn.focus();editorReturn=null;}
  async function edit(row=null,newFolder=false){
    closeEditor(false);
    const key=profileKey(),generation=editorGeneration;
    rows=await api.getBookmarks();
    if(profileKey()!==key||generation!==editorGeneration)return;
    const page={...state.page};
    if(!row&&!newFolder){
      if(!/^https?:\/\//i.test(page.url||'')){await openMenu();return;}
      row=rows.find(mark=>mark.type!=='folder'&&mark.url===page.url)||null;
    }
    const isFolder=newFolder||row?.type==='folder';let existing=row;
    const en=state.settings?.language==='en',t=(ru,english)=>en?english:ru;
    editorReturn=document.activeElement;
    const box=el('form','bookmark-editor');editor=box;
    box.setAttribute('role','dialog');box.setAttribute('aria-label',t(existing?'Изменить закладку':isFolder?'Новая папка':'Сохранить закладку',existing?'Edit bookmark':isFolder?'New folder':'Save bookmark'));
    const top=el('div','bookmark-editor-head');top.append(el('strong','',box.getAttribute('aria-label')),button('×',()=>closeEditor()));top.lastChild.setAttribute('aria-label',t('Закрыть','Close'));box.append(top);
    function field(label,id,value){const wrap=el('label','bookmark-editor-field',label),input=el('input');input.id=id;input.value=value||'';input.required=true;wrap.append(input);box.append(wrap);return input;}
    const title=field(t('Название','Name'),'bookmarkTitle',existing?.title||(isFolder?'':page.title));
    const url=isFolder?null:field(t('Адрес','Address'),'bookmarkUrl',existing?.url||page.url);
    const place=el('label','bookmark-editor-field',t('Сохранить в','Save in')),select=el('select');select.id='bookmarkFolder';
    select.append(new Option(t('Панель закладок','Bookmarks bar'),'0'));
    const excluded=existing?descendants(existing.id):new Set();
    const path=mark=>{const names=[mark.title];let id=mark.parentId,depth=0;while(id&&depth++<64){const folder=rows.find(r=>r.id===id);if(!folder)break;names.unshift(folder.title);id=folder.parentId;}return names.join(' / ');};
    for(const mark of rows.filter(r=>r.type==='folder'&&!excluded.has(r.id)))select.append(new Option(path(mark),String(mark.id)));
    select.value=String(existing?.parentId??parent??0);if(select.selectedIndex<0)select.value='0';place.append(select);box.append(place);
    const favorite=el('input');favorite.type='checkbox';favorite.id='bookmarkHomeFavorite';favorite.checked=!!existing&&(state.settings?.homeFavoriteIds||[]).includes(existing.id);
    if(!isFolder){const label=el('label','bookmark-editor-favorite');label.append(favorite,document.createTextNode(t('Избранное на Home','Home favorites')));box.append(label);}
    const error=el('p','bookmark-editor-error');error.setAttribute('role','alert');error.hidden=true;box.append(error);
    const footer=el('div','bookmark-editor-footer'),cancel=button(t('Отмена','Cancel'),()=>closeEditor()),save=button(t('Сохранить','Save'),()=>{});save.type='submit';footer.append(cancel,save);box.append(footer);
    box.onsubmit=async e=>{e.preventDefault();if(save.disabled)return;error.hidden=true;let address=url?.value.trim();
      if(url){try{const parsed=new URL(address);if(!['http:','https:'].includes(parsed.protocol)||!parsed.hostname||parsed.username||parsed.password)throw Error();address=parsed.href;}catch{error.textContent=t('Введите адрес HTTP или HTTPS.','Enter an HTTP or HTTPS address.');error.hidden=false;url.focus();return;}}
      if(!title.value.trim()){title.focus();return;}save.disabled=true;cancel.disabled=true;
      try{
        if(profileKey()!==key)throw Error(t('Профиль изменился. Откройте редактор заново.','The profile changed. Open the editor again.'));
        rows=await api.getBookmarks();
        if(profileKey()!==key)throw Error(t('Профиль изменился. Откройте редактор заново.','The profile changed. Open the editor again.'));
        const mark=existing?rows.find(r=>r.id===existing.id):null;
        if(existing&&!mark)throw Error(t('Закладка уже удалена.','This bookmark was deleted.'));
        const next=mark?{...mark}:{id:nextId(),type:isFolder?'folder':'url',createdAt:Date.now(),order:rows.length};
        Object.assign(next,{title:title.value.trim(),parentId:Number(select.value),updatedAt:Date.now()});if(url){next.url=address;if(!mark&&address===page.url)next.favicon=page.favicon;}
        await persist(mark?rows.map(r=>r.id===mark.id?next:r):[...rows,next]);
        existing=next;
        if(profileKey()!==key)throw Error(t('Профиль изменился.','The profile changed.'));
        if(!isFolder){const ids=state.settings?.homeFavoriteIds||[],selected=favorite.checked;await api.setSettings({homeFavoriteIds:selected?[...new Set([...ids,next.id])]:ids.filter(id=>id!==next.id)});}
        if(editor===box)closeEditor();
      }catch(reason){error.textContent=reason.message;error.hidden=false;save.disabled=false;cancel.disabled=false;}
    };
    document.body.append(box);await api.setPopover(true,'bookmark-editor');updatePopover();
    if(editor!==box)return;
    const anchor=document.querySelector(state.settings?.layout==='classic'?'#favoritesButton':'.compact-toolbar [data-favorites]')?.getBoundingClientRect();
    const toolbar=document.querySelector(state.settings?.layout==='classic'?'.classic-toolbar':'.compact-toolbar');
    const width=box.getBoundingClientRect().width;box.style.left=Math.max(12,Math.min(innerWidth-width-12,(anchor?.right||innerWidth)-width))+'px';box.style.top=(anchor?.bottom||toolbar?.getBoundingClientRect().bottom||0)+10+'px';title.focus();title.select();
    box.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();closeEditor();}else if(e.key==='Tab'){const focusable=[...box.querySelectorAll('button,input,select')].filter(n=>!n.disabled);if(e.shiftKey&&document.activeElement===focusable[0]){e.preventDefault();focusable.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===focusable.at(-1)){e.preventDefault();focusable[0].focus();}}};
  }
  async function folder(){await edit(null,true);}
  async function add(){await edit();}
  actions.append(button('Все закладки',()=>{pane='list';parent=0;query='';menuSearch.value='';manage=false;renderMenu();}),button('Управление закладками',()=>{pane='list';manage=true;renderMenu();}),button('Добавить текущую страницу',add),button('Создать папку',folder),button('Импортировать закладки…',importMenu));
  const options=el('div','bookmark-options');
  const settingsAction=button('Настройки закладок',()=>{closeMenu();api.openSettingsWindow();});
  settingsAction.id='bookmarkSettingsAction';options.append(settingsAction);menu.append(options);
  function renderMenu(){if(pane==='import')return;contents.replaceChildren();if(parent){const current=rows.find(r=>r.id===parent);if(!current){parent=0;return renderMenu();}contents.append(button('‹ '+current.title,()=>{parent=current.parentId||0;renderMenu();}));}const matches=query?rows.filter(r=>(r.title+' '+(r.url||'')).toLocaleLowerCase().includes(query.toLocaleLowerCase())):children(parent);for(const r of matches){const line=el('div','bookmark-line');line.append(item(r));if(manage){line.append(button('Изменить',()=>edit(r)));}contents.append(line);}if(!matches.length)contents.append(el('p','','Закладок пока нет'));}
  function renderBar(){const host=document.querySelector(state.settings?.layout==='classic'?'.classic-toolbar':'.compact-toolbar');if(host&&bar.parentElement!==host)host.append(bar);bar.replaceChildren();bar.hidden=!state.bookmarksBarVisible;document.body.dataset.bookmarksBar=String(!bar.hidden);document.body.dataset.bookmarksPosition=state.settings?.bookmarksBarPosition||'above';if(bar.hidden)return;const list=children(0);for(const row of list)bar.append(item(row,true));const more=button('»',()=>openMenu());more.classList.add('bookmarks-overflow');bar.append(more);requestAnimationFrame(()=>{if(bar.hidden)return;let limit=bar.clientWidth-42,used=12,hidden=false;for(const node of [...bar.children].slice(0,-1)){node.hidden=false;used+=node.getBoundingClientRect().width+4;if(used>limit){node.hidden=true;hidden=true;}}more.hidden=!hidden;});bar.ondragover=e=>{if(drag)e.preventDefault();};bar.ondrop=e=>{e.preventDefault();if(drag)persist(rows.map(r=>r.id===drag?{...r,parentId:0,order:rows.length}:r)).catch(err=>alert(err.message));};}
  function renderOverview(){if(overview.hidden)return;const q=search.value.toLocaleLowerCase();grid.replaceChildren();for(const tab of state.tabs||[]){if(!(tab.title+' '+tab.url).toLocaleLowerCase().includes(q))continue;const card=el('article','overview-card'+(tab.active?' active':''));const preview=button('',async()=>{await api.switchTab(tab.id);await api.setOverview(false);});preview.classList.add('overview-preview');preview.setAttribute('aria-label',tab.title||'Новая вкладка');if(tab.thumbnail){const im=el('img');im.src=tab.thumbnail;im.alt='';preview.append(im);}else{preview.append(el('span','preview-placeholder',tab.url?'Превью появится после просмотра вкладки':'Новая вкладка'));}const caption=el('div','overview-caption');caption.append(icon(tab),el('span','',tab.title||'Новая вкладка'),button('×',()=>api.closeTab(tab.id)));caption.lastChild.setAttribute('aria-label','Закрыть '+tab.title);card.append(preview,caption);grid.append(card);}const addTile=button('+ Новая вкладка',async()=>{await api.newTab();await api.setOverview(false);});addTile.classList.add('overview-new');grid.append(addTile);}
  function render(){renderBar();if(!menu.hidden)renderMenu();overview.hidden=!state.overviewVisible;renderOverview();}
  async function importMenu(){pane='import';contents.replaceChildren(el('p','','Chrome / Edge / Brave / другие Chromium: файл Bookmarks (JSON) или экспорт HTML. Firefox: экспорт закладок HTML. Пароли не импортируются.'));const input=el('input');input.type='file';input.setAttribute('aria-label','Файл закладок Chromium JSON или HTML-экспорт');contents.append(input);input.onchange=async()=>{try{const file=input.files[0];if(!file)return;const profile=String(state.activeProfileId)+':'+String(state.incognito);if(file.size>20*1024*1024)throw Error('Файл превышает 20 МБ');const text=await file.text();if(menu.hidden||pane!=='import')return;if(profile!==String(state.activeProfileId)+':'+String(state.incognito))throw Error('Профиль изменился. Откройте импорт заново.');let nodes=[];if(text.trim().startsWith('{')){const data=JSON.parse(text);if(!data.roots)throw Error('Нужен стандартный Chromium Bookmarks JSON');nodes=Object.values(data.roots);}else{const doc=new DOMParser().parseFromString(text,'text/html');if(!doc.querySelector('dl'))throw Error('Нужен экспорт закладок HTML');const parse=dl=>[...dl.children].filter(n=>n.tagName==='DT').map(dt=>{const a=dt.querySelector(':scope > a'),h=dt.querySelector(':scope > h3');if(a)return {type:'url',name:a.textContent,url:a.getAttribute('href')};const nested=dt.querySelector(':scope > dl');return h?{type:'folder',name:h.textContent,children:nested?parse(nested):[]}:null;}).filter(Boolean);nodes=parse(doc.querySelector('dl'));}const next=rows.map(r=>({...r}));let id=nextId(),added=0;const walk=(ns,p,depth=0)=>{if(depth>64)throw Error('Слишком глубокая вложенность');for(const n of ns){if(next.length>=20000)throw Error('Слишком много закладок');if(n.type==='folder'||n.children){let existing=next.find(r=>r.type==='folder'&&(r.parentId||0)===p&&r.title===(n.name||'Импорт'));if(!existing){existing={id:id++,type:'folder',title:n.name||'Импорт',parentId:p,order:next.length,createdAt:Date.now()};next.push(existing);added++;}walk(n.children||[],existing.id,depth+1);}else if(/^https?:\/\//i.test(n.url||'')&&!next.some(r=>r.url===n.url)){next.push({id:id++,type:'url',title:n.name||n.url,url:n.url,parentId:p,order:next.length,createdAt:Date.now()});added++;}}};walk(nodes,0);if(!added){alert('Новых закладок нет. Дубликаты пропущены.');return;}if(!confirm('Добавить '+added+' элементов из '+file.name+'? Дубликаты URL будут пропущены.'))return;pane='list';await persist(next);alert('Импорт завершён');}catch(error){alert(error.message);}};}
  for(const [selector,before] of [['.window-controls','#windowMinimize'],['.compact-toolbar-surface','#compactWindowMinimize']]){const host=document.querySelector(selector);if(!host)continue;const tabs=button('',async()=>{closeMenu();await api.setOverview(!state.overviewVisible);});tabs.classList.add('navigation-toolbar-button',selector==='.window-controls'?'toolbar-button':'compact-control');tabs.title='Обзор вкладок';tabs.setAttribute('aria-label','Обзор вкладок');tabs.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 7V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2"/><rect x="7" y="7" width="14" height="14" rx="1.8"/></svg>';host.insertBefore(tabs,host.querySelector(before));}
  document.addEventListener('click',e=>{if(e.target.closest('#favoritesButton,[data-favorites]')){e.preventDefault();e.stopImmediatePropagation();edit();}else if(e.target.closest('#sidebarButton,#compactSidebarButton')){e.preventDefault();e.stopImmediatePropagation();closeEditor(false);if(menu.hidden)openMenu();else closeMenu();}},true);
  document.addEventListener('pointerdown',e=>{if(!e.target.closest('.bookmark-context')){document.querySelector('.bookmark-context')?.remove();updatePopover();}});
  shield.addEventListener('pointerdown',()=>closeEditor());
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeEditor();closeMenu();api.setOverview(false);}if(e.ctrlKey&&e.shiftKey&&e.key.toLowerCase()==='b'){e.preventDefault();api.setBookmarksAuto(!state.bookmarksBarVisible);}});
  let autoTimer=0;
  for(const header of document.querySelectorAll('.browser-toolbar')){header.addEventListener('pointerenter',()=>{clearTimeout(autoTimer);if(state.settings?.bookmarksBarMode==='auto'&&!state.bookmarksBarVisible)api.setBookmarksAuto(true);});header.addEventListener('pointerleave',()=>{autoTimer=setTimeout(()=>{if(state.settings?.bookmarksBarMode==='auto'&&menu.hidden&&!bar.matches(':hover'))api.setBookmarksAuto(false);},500);});}
  bar.addEventListener('pointerenter',()=>clearTimeout(autoTimer));bar.addEventListener('pointerleave',()=>{if(state.settings?.bookmarksBarMode==='auto'&&menu.hidden)api.setBookmarksAuto(false);});
  window.addEventListener('resize',()=>{renderBar();if(!menu.hidden)renderMenu();});
  window.souluNavigation={openBookmarks:openMenu};
  const apply=s=>{const changed=profileKey()!==String(s.activeProfileId)+':'+String(s.incognito),entered=s.overviewVisible&&!state.overviewVisible;state=s;if(changed)closeEditor(false);rows=s.bookmarks||rows;menu.hidden=!s.bookmarksSidebarVisible;if(entered){closeEditor(false);closeMenu();}render();document.querySelectorAll('#sidebarButton,#compactSidebarButton').forEach(n=>{n.title=s.settings?.language==='en'?'Bookmarks':'Закладки';n.setAttribute('aria-label',n.title);n.classList.toggle('active',!!s.bookmarksSidebarVisible);});document.querySelectorAll('#favoritesButton,[data-favorites]').forEach(n=>{n.title=s.settings?.language==='en'?'Save bookmark':'Сохранить закладку';const saved=rows.some(r=>r.url===s.page?.url);n.classList.toggle('bookmark-saved',saved);n.setAttribute('aria-pressed',String(saved));});if(entered){search.value='';renderOverview();search.focus();}};api.onState(apply);api.getState().then(apply);
})();
