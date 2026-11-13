(() => {
  'use strict';
  if(new URLSearchParams(location.search).get('host')==='overlay')document.body.dataset.host='overlay';
  const $=id=>document.getElementById(id), el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const clone=v=>structuredClone(v);
  const invoke=(action,payload=null)=>new Promise((resolve,reject)=>window.cefQuery({request:JSON.stringify({action:'settings.'+action,payload}),persistent:false,onSuccess:v=>resolve(v?JSON.parse(v):null),onFailure:(_,message)=>reject(Error(message))}));
  let loaded=null,persisted=null,current=null,state={},section='',busy=false,reloading=false,queue=Promise.resolve(),index=[];
  const t=(ru,en)=>current?.settings.language==='en'?en:ru;
  const icons=window.sonaSettingsIcons;
  const icon=id=>icons.create(id);
  const opt=(value,ru,en=ru)=>({value,ru,en});
  const row=(key,ru,en,type='toggle',options=[],hint='',enHint='',store='settings',tags='')=>({key,ru,en,type,options,hint,enHint,store,tags});
  const action=(key,ru,en)=>row(key,ru,en,'action');
  const group=(ru,en,rows)=>({ru,en,rows});
  const pageOptions=[opt('sona','Страница Sona','Sona page'),opt('blank','Пустая страница','Blank page'),opt('custom','Указанный адрес','Custom address')];
  const permissionNames=[['geolocation','Геолокация','Location'],['camera','Камера','Camera'],['microphone','Микрофон','Microphone'],['notifications','Уведомления','Notifications'],['sound','Звук','Sound'],['popups','Всплывающие окна','Pop-ups'],['downloads','Автоматические загрузки','Automatic downloads']];
  const sections=[
    {id:'general',ru:'Общие',en:'General',hint:'Язык и основные настройки Sona.',enHint:'Language and basic Sona settings.',groups:[group('Язык и система','Language and system',[row('language','Язык интерфейса','Interface language','select',[opt('ru','Русский'),opt('en','English')],'Язык меню, настроек и элементов интерфейса Sona.','Language of Sona menus, settings and interface.'),action('defaultBrowser','Браузер по умолчанию','Default browser')])]},
    {id:'interface',ru:'Интерфейс',en:'Interface',hint:'Внешний вид и элементы браузера.',enHint:'Appearance and browser controls.',groups:[group('Внешний вид','Appearance',[row('theme','Тема','Theme','segments',[opt('system','Системная','System'),opt('light','Светлая','Light'),opt('dark','Тёмная','Dark')],'','', 'settings','тёмная темная светлая dark light'),row('mattePanel','Матовая прозрачность','Matte transparency','toggle',[],'Размытие и прозрачность в верхней панели Sona.','Blur and transparency in the Sona toolbar.'),row('layout','Режим панели','Toolbar mode','segments',[opt('adaptive','Основная','Main'),opt('compact','Компактная','Compact')])]),group('Элементы панели','Toolbar items',[...[
      ['showExtensions','Кнопка расширений','Extensions button'],['showSidebar','Боковая панель','Sidebar'],['showBack','Назад','Back'],['showHome','Домашняя страница','Home button'],['showFavorites','Закладки','Bookmarks'],['showNewTab','Новая вкладка','New tab'],['showDownloads','Загрузки','Downloads'],['vpnToolbarVisible','Кнопка VPN','VPN button']].map(a=>row(...a)),row('addressPosition','Расположение адресной строки','Address position','select',[opt('left','Слева','Left'),opt('center','По центру','Centered')]),row('downloadsMode','Кнопка загрузок','Downloads button','select',[opt('always','Всегда показывать','Always show'),opt('dynamic','Во время загрузки','During downloads')])])]},
    {id:'tabs',ru:'Вкладки и страницы',en:'Tabs and pages',hint:'Вкладки, запуск и страницы браузера.',enHint:'Tabs, startup and browser pages.',groups:[group('Вкладки','Tabs',[row('openStartPageAfterLastTab','После закрытия последней вкладки открывать страницу запуска','Open the startup page after closing the last tab','toggle',[],'Вместо закрытия последней вкладки откроется выбранная страница запуска.','The selected startup page replaces the last tab.')]),...[
      ['startup','При запуске Sona','When Sona starts'],['newTab','Новая вкладка','New tab'],['home','Домашняя страница','Home page']].map(([key,ru,en])=>group(ru,en,[row(key+'Mode',ru,en,'select',key==='startup'?[opt('continue','Продолжить с предыдущего места','Continue where you left off'),...pageOptions]:pageOptions),row(key+'Url','Адрес страницы','Page address','url')])),group('Погода','Weather',[row('homeWeatherMode','Местоположение','Location','select',[opt('automatic','Автоматически','Automatic'),opt('configured','Указанный город','Selected city')],'Автоматическое определение использует разрешённую геолокацию Windows.','Automatic location uses permitted Windows geolocation.'),row('homeWeatherCity','Город','City','text'),row('homeWeatherUnits','Единицы температуры','Temperature units','select',[opt('celsius','Цельсий','Celsius'),opt('fahrenheit','Фаренгейт','Fahrenheit')]),action('weatherPermission','Доступ к геолокации для погоды','Weather location permission'),action('weatherCredits','Источники погоды','Weather sources')]),group('Избранное Home','Home favorites',[row('homeShowFavorites','Кнопка избранного рядом с погодой','Favorites button beside weather','toggle'),action('homeFavorites','Выбрать закладки для Home','Choose bookmarks for Home')])]},
    {id:'search',ru:'Поиск',en:'Search',hint:'Поисковая система и адресная строка.',enHint:'Search engine and address bar.',groups:[group('Адресная строка','Address bar',[row('searchEngine','Поисковая система','Search engine','select',[opt('google','Google'),opt('yandex','Яндекс','Yandex'),opt('bing','Bing'),opt('duckduckgo','DuckDuckGo')]),row('addressOpenMode','Открывать введённый адрес','Open entered address','select',[opt('current','В текущей вкладке','In current tab'),opt('newIfOccupied','В новой, если текущая занята','In new tab when occupied')])])]},
    {id:'bookmarks',ru:'Закладки',en:'Bookmarks',hint:'Панель и отображение закладок.',enHint:'Bookmarks bar and display.',groups:[group('Панель закладок','Bookmarks bar',[row('bookmarksBarMode','Панель закладок','Bookmarks bar','select',[opt('always','Всегда показывать','Always show'),opt('newTab','На странице новой вкладки','On the new tab page'),opt('home','На домашней странице','On the home page'),opt('auto','При наведении','On hover'),opt('never','Не показывать','Hidden')]),row('bookmarksIconsOnly','Показывать только иконки','Show icons only')])]},
    {id:'sites',ru:'Веб-сайты',en:'Websites',hint:'Разрешения, данные и содержимое сайтов.',enHint:'Permissions, data and site content.',groups:[group('Разрешения','Permissions',permissionNames.map(([key,ru,en])=>row(key,ru,en,'select',key==='sound'?[opt(0,'Разрешать','Allow'),opt(1,'Приглушать','Mute'),opt(2,'Блокировать','Block')]:[opt(0,'Разрешать','Allow'),opt(1,'Спрашивать','Ask'),opt(2,'Блокировать','Block')],'','', 'permissions'))),group('Исключения сайтов','Site exceptions',[action('exceptions','Исключения разрешений','Permission exceptions')]),group('Блокировка рекламы','Ad blocking',[row('contentBlocking','Блокировать рекламу','Block ads','toggle',[],'Блокировка рекламных запросов и трекеров, скрытие рекламных контейнеров.','Blocks advertising and tracking requests and hides advertising containers.','blocking'),action('adblockExceptions','Разрешить рекламу на выбранных сайтах','Allow ads on selected sites')]),group('Режим чтения','Reader mode',[
      row('theme','Тема чтения','Reader theme','select',[opt('light','Светлая','Light'),opt('sepia','Сепия','Sepia'),opt('gray','Серая','Gray'),opt('dark','Тёмная','Dark')],'','','reader','reader режим чтения'),row('font','Шрифт','Font','select',[opt('system','Системный','System'),opt('sans','Без засечек','Sans-serif'),opt('serif','С засечками','Serif')],'','','reader'),row('size','Размер текста','Text size','select',[14,16,18,20,22,24,26,28,30,32].map(v=>opt(v,String(v))),'','','reader'),row('width','Ширина текста','Text width','select',[opt(0,'Узкая','Narrow'),opt(1,'Средняя','Medium'),opt(2,'Широкая','Wide')],'','','reader'),row('spacing','Межстрочный интервал','Line spacing','select',[opt(0,'Обычный','Normal'),opt(1,'Свободный','Relaxed'),opt(2,'Широкий','Wide')],'','','reader'),row('images','Показывать изображения','Show images','toggle',[],'','','reader')]),group('Sona Translate','Sona Translate',[row('translationTarget','Язык локального перевода','Local translation language','select',[opt('ru','Русский','Russian'),opt('en','Английский','English')],'Текст остаётся на устройстве. Правила языков и сайтов доступны в панели перевода.','Text stays on your device. Language and site rules are available in the translation panel.')]),group('Данные сайтов','Site data',[action('siteData','Очистить данные сайта…','Clear site data…')])]},
    {id:'profiles',ru:'Профили и данные',en:'Profiles and data',hint:'Профили, пароли и импорт данных.',enHint:'Profiles, passwords and data import.',groups:[group('История и очистка','History and clearing',[row('saveHistory','Сохранять историю браузера','Save browsing history'),row('historyGroupDays','Группировать историю по дням','Group history by day'),row('historyDefaultFilter','Начальный период истории','Default history period','select',[opt('all','Все записи','All visits'),opt('today','Сегодня','Today'),opt('yesterday','Вчера','Yesterday'),opt('week','Последние 7 дней','Last 7 days'),opt('older','Более старые','Older visits')]),action('history','Открыть историю','Open history'),action('clearData','Очистить данные браузера…','Clear browsing data…')]),group('Профили','Profiles',[action('profileList','Текущий профиль и другие профили','Current and other profiles'),action('createProfile','Создать профиль','Create profile')]),group('Пароли','Passwords',[{...action('passwords','Открыть менеджер паролей','Open password manager'),tags:'пароль логин password'}]),group('Импорт данных','Import data',[action('import','Импортировать из другого браузера','Import from another browser')]),group('Инкогнито','Incognito',[action('incognito','Открыть вкладку инкогнито','Open incognito tab')])]},
    {id:'downloads',ru:'Загрузки',en:'Downloads',hint:'Папка загрузок и сохранение файлов.',enHint:'Download folder and saving files.',groups:[group('Сохранение файлов','Saving files',[row('downloadPath','Папка загрузок','Downloads folder','text'),action('chooseFolder','Изменить папку','Change folder'),row('askDownloadLocation','Всегда спрашивать, куда сохранять файлы','Always ask where to save files'),action('openFolder','Открыть папку загрузок','Open downloads folder')])]},
    {id:'vpn',ru:'VPN',en:'VPN',hint:'Подключения VLESS и Sudoku.',enHint:'VLESS and Sudoku connections.',groups:[group('Подключения','Connections',[row('profiles','Сохранённые ключи','Saved connections','vpnProfiles',[],'','','vpn')]),group('Маршрутизация','Routing',[row('directDomains','Сайты без VPN','Sites without VPN','textarea',[],'По одному домену или адресу на строку. Поддомены также подключаются напрямую. Изменения применяются сразу.','One domain or URL per line. Subdomains also connect directly. Changes apply immediately.','vpn')])]},
    {id:'updates',ru:'Обновления',en:'Updates',hint:'Версия Sona и компоненты браузера.',enHint:'Sona version and browser components.',groups:[group('Компоненты','Components',[{...action('versions','Версии компонентов','Component versions'),tags:'cef chromium версия version'}])]}
  ];
  // Reuse the canonical controls and bindings in the fixed Settings 2.0 map.
  const old=Object.fromEntries(sections.map(s=>[s.id,s]));
  old.general.groups.push({...old.downloads.groups[0],ru:'Загрузки',en:'Downloads'});
  old.interface.groups.push(...old.bookmarks.groups);
  old.interface.groups[1].rows.find(r=>r.key==='showDownloads').ru='Показывать загрузки на панели';
  old.interface.groups[1].rows.find(r=>r.key==='showDownloads').en='Show downloads on toolbar';
  old.interface.groups[1].rows.find(r=>r.key==='downloadsMode').ru='Когда показывать кнопку загрузок';
  old.interface.groups[1].rows.find(r=>r.key==='downloadsMode').en='When to show downloads button';
  old.tabs.id='startup';old.tabs.ru='Запуск и главная';old.tabs.en='Startup and home';
  old.sites.id='privacy';old.sites.ru='Конфиденциальность и защита';old.sites.en='Privacy and security';
  old.sites.hint='Разрешения, реклама и сохранённые данные.';old.sites.enHint='Permissions, ads and stored data.';
  const reading={id:'reading',ru:'Режим чтения',en:'Reader mode',hint:'Оформление текста в режиме чтения.',enHint:'Text appearance in Reader mode.',groups:old.sites.groups.filter(g=>g.en==='Reader mode')};
  const translation={id:'translation',ru:'Перевод',en:'Translation',hint:'Перевод страниц и озвучка видео YouTube.',enHint:'Page translation and YouTube video voice-over.',groups:[...old.sites.groups.filter(g=>g.en==='Sona Translate'),group('YouTube Translate','YouTube Translate',[row('videoTranslationEnabled','Перевод видео YouTube','YouTube video translation','toggle',[],'Русская озвучка VOT запускается кнопкой на самом видео.','Start VOT Russian voice-over using the button on the video.'),action('videoOptions','Настройки перевода YouTube','YouTube translation settings')])]};
  const extensions={id:'extensions',ru:'Расширения',en:'Extensions',hint:'Каталог и установленные расширения браузера.',enHint:'Extension catalog and installed browser extensions.',groups:[group('Каталог расширений','Extension catalog',[row('extensionCatalog','Расширения для Sona','Extensions for Sona','extensionCatalog')])]};
  const performance={id:'performance',ru:'Производительность',en:'Performance',hint:'Ресурсы, память и фоновые вкладки.',enHint:'Resources, memory and background tabs.',groups:[group('Режим работы','Operating mode',[row('performanceMode','Режим работы браузера','Browser operating mode','select',[opt('balanced','Сбалансированный','Balanced'),opt('eco','Экономия ресурсов','Resource saver'),opt('performance','Максимальная производительность','Maximum performance')],'Экономия приостанавливает неактивные вкладки через минуту. Максимальная производительность оставляет их работающими.','Resource saver pauses idle tabs after one minute. Maximum performance keeps them running.')]),group('Фоновые вкладки','Background tabs',[row('freezeBackgroundTabs','Приостанавливать неактивные вкладки','Pause inactive tabs','toggle',[],'Страница и введённый текст сохраняются. Вкладка продолжает работу при открытии. Звук, камера, микрофон, закреплённые вкладки и загрузки защищены.','The page and entered text are preserved. Opening a tab resumes it. Audio, camera, microphone, pinned tabs and downloads are protected.'),row('backgroundTabTimeout','Приостанавливать через','Pause after','select',[opt('60','1 минуту','1 minute'),opt('300','5 минут','5 minutes'),opt('900','15 минут','15 minutes'),opt('1800','30 минут','30 minutes')]),row('memorySaver','Освобождать неиспользуемую память','Release unused memory','toggle',[],'Сборка неиспользуемых объектов после приостановки. Страницы не выгружаются и не перезагружаются.','Collect unused objects after pausing. Pages are not discarded or reloaded.'),row('performanceExclusions','Всегда активные сайты','Always-active sites','textarea',[],'Один домен в строке, включая его поддомены.','One domain per line, including its subdomains.'),action('optimizeNow','Приостановить подходящие фоновые вкладки сейчас','Pause eligible background tabs now')])]};
  old.sites.groups=old.sites.groups.filter(g=>!['Reader mode','Sona Translate'].includes(g.en));
  old.sites.groups.splice(3,0,old.profiles.groups[0]);
  old.sites.groups.push(old.profiles.groups[2]);
  old.profiles.groups=old.profiles.groups.filter(g=>!['History and clearing','Passwords'].includes(g.en));
  old.profiles.ru='Профили и импорт';old.profiles.en='Profiles and import';
  old.profiles.hint='Профили, импорт и инкогнито.';old.profiles.enHint='Profiles, import and incognito.';
  old.updates.groups.push(group('Компоненты VPN','VPN components',[row('vpnComponents','Xray и Sudoku','Xray and Sudoku','components')]));
  old.updates.id='about';old.updates.ru='О Sona';old.updates.en='About Sona';
  sections.splice(0,sections.length,old.general,old.interface,old.tabs,old.search,old.sites,old.vpn,reading,translation,extensions,performance,old.profiles,old.updates);
  document.querySelector('.search-box').prepend(icon('search'));
  for(const id of ['closeSettings','clearSearch','closeAction'])$(id).replaceChildren(icon('close'));
  function get(r){if(r.key==='bookmarksBarMode'&&current.settings.bookmarksBarPosition==='hidden')return 'never';if(r.store==='permissions')return current.rules.defaults[r.key];if(r.store==='blocking')return current.rules.blocking.enabled;return current[r.store][r.key];}
  function set(r,value){if(r.store==='vpn'&&r.key==='link'&&value.trim()){try{const parsed=window.sonaParseVpnKey(value);Object.assign(current.vpn,parsed);value=parsed.link;const field=document.getElementById('vpn-link');if(field)field.value=value;for(const radio of document.querySelectorAll('input[name=vpn-protocol]'))radio.checked=radio.value===parsed.protocol;}catch(error){report(error);return;}}if(r.key==='bookmarksBarMode'){if(value==='never')current.settings.bookmarksBarPosition='hidden';else{current.settings.bookmarksBarPosition='above';current.settings.bookmarksBarMode=value;}}else if(r.store==='permissions')current.rules.defaults[r.key]=Number(value);else if(r.store==='blocking')current.rules.blocking.enabled=value;else current[r.store][r.key]=r.store==='reader'&&['size','width','spacing'].includes(r.key)?Number(value):value;changed();}
  function report(error){if(section){let n=document.getElementById('sectionError');if(!n){n=el('p',undefined,'note error');n.id='sectionError';n.setAttribute('role','alert');$('sectionContent').prepend(n);}n.textContent=error.message||error;}$('dataMessage').textContent=error.message||error;$('dataMessage').classList.add('error');}
  function status(){document.querySelector('main').setAttribute('aria-busy',String(busy));}
  let saveGeneration=0;
  function changed(){
    window.sonaMotion.cancel();$('dataMessage').classList.remove('error');$('sectionError')?.remove();
    document.body.dataset.theme=current.settings.theme;updateConditional();
    if(document.documentElement.lang!==current.settings.language)render();
    const snapshot=clone(current),generation=++saveGeneration;
    queue=queue.then(async()=>{
      const result=await invoke('save',snapshot);
      persisted=result.persisted;loaded=clone(persisted);
      if(generation===saveGeneration){
        current=clone(persisted);
        if(!result.ok){render();throw Error(result.error);}
        document.body.dataset.theme=current.settings.theme;
      }
      if(!result.ok)throw Error(result.error);
    }).catch(report);
    return queue;
  }
  function updateConditional(){
    const managed=current.settings.performanceMode!=='balanced';
    const freeze=$('freezeBackgroundTabs');if(freeze)freeze.disabled=managed;
    const timeout=$('backgroundTabTimeout');if(timeout)timeout.disabled=managed||!current.settings.freezeBackgroundTabs;
for(const kind of ['startup','newTab','home']){const n=$('control-settings-'+kind+'Url');if(n){const inactive=current.settings[kind+'Mode']!=='custom';n.hidden=inactive;n.querySelector('input').disabled=inactive;n.querySelector('.search-mode-note')?.remove();}}const n=$('control-settings-bookmarksIconsOnly');if(n){const hidden=current.settings.bookmarksBarPosition==='hidden';n.querySelector('input').disabled=hidden;let note=n.querySelector('small');if(!note){note=el('small');n.querySelector('span').append(note);}note.textContent=hidden?t('Недоступно, пока панель закладок отключена.','Unavailable while the bookmarks bar is hidden.'):'';}}
  function button(text,fn,cls){const b=el('button',text,cls);b.type='button';b.onclick=()=>Promise.resolve().then(fn).catch(report);return b;}
  function render(){window.sonaMotion.cancel();if(!current)return;const english=current.settings.language==='en';document.documentElement.lang=english?'en':'ru';document.title=t('Настройки','Settings');document.body.dataset.theme=current.settings.theme;$('closeSettings').setAttribute('aria-label',t('Закрыть настройки','Close settings'));const activeSection=sections.find(s=>s.id===section);$('settingsTitle').textContent=activeSection?t(activeSection.ru,activeSection.en):t('Настройки','Settings');$('settingsSearch').placeholder=t('Поиск в настройках','Search settings');$('settingsSearch').setAttribute('aria-label',$('settingsSearch').placeholder);$('clearSearch').title=t('Очистить поиск','Clear search');$('clearSearch').setAttribute('aria-label',$('clearSearch').title);$('closeAction').setAttribute('aria-label',t('Закрыть','Close'));$('sectionNav').setAttribute('aria-label',t('Разделы настроек','Settings sections'));$('settingsContent').setAttribute('aria-label',t('Настройки','Settings'));
    $('homeCards').replaceChildren();$('sectionNav').replaceChildren();const all=button('',()=>openSection(''),'nav-item');all.append(icon('all'),el('span',t('Все настройки','All settings')));all.title=t('Все настройки','All settings');all.setAttribute('aria-label',all.title);$('sectionNav').append(all);
    index=[];
    for(const s of sections){const b=button('',()=>openSection(s.id,undefined,true),'category-card icon-'+s.id);const tile=el('span',undefined,'icon-tile');tile.append(icon(s.id));const text=el('span',undefined,'category-copy');text.append(el('strong',t(s.ru,s.en)),el('small',t(s.hint,s.enHint)));b.dataset.section=s.id;b.append(tile,text,icon('chevron'));$('homeCards').append(b);
      const nav=button('',()=>openSection(s.id),'nav-item');nav.dataset.section=s.id;nav.append(icon(s.id),el('span',t(s.ru,s.en)));nav.dataset.tooltip=t(s.ru,s.en);nav.setAttribute('aria-label',nav.dataset.tooltip);nav.classList.toggle('active',section===s.id);if(section===s.id)nav.setAttribute('aria-current','page');$('sectionNav').append(nav);
      for(const g of s.groups)for(const r of g.rows)index.push({section:s.id,key:r.store+'-'+r.key,title:t(r.ru,r.en),path:t(s.ru,s.en)+' → '+t(g.ru,g.en),hay:[s.ru,s.en,g.ru,g.en,r.ru,r.en,r.hint,r.enHint,r.key,r.tags,...r.options.flatMap(o=>[o.ru,o.en])].join(' ').toLowerCase().replaceAll('ё','е')});
    }
    renderSection();showSearch();status();resizePanel();
  }
  function renderSection(){const content=$('sectionContent');content.replaceChildren();const s=sections.find(x=>x.id===section);if(!s)return;const h=el('header',undefined,'section-heading');const words=el('div');words.append(el('p',t(s.hint,s.enHint)));h.append(icon(s.id),words);content.append(h);
    for(const g of s.groups){const card=el('article',undefined,'card');card.append(el('h3',t(g.ru,g.en)));
      for(const r of g.rows){const n=el('div',undefined,'row'+(r.type==='textarea'?' long':''));n.id='control-'+r.store+'-'+r.key;n.tabIndex=-1;const text=el('span');text.append(el('b',t(r.ru,r.en)));if(r.hint)text.append(el('small',t(r.hint,r.enHint)));n.append(text);
        if(r.type==='extensionCatalog'){
          n.classList.add('long');n.replaceChildren();card.querySelector('h3')?.remove();
          const controls=el('div',undefined,'extension-controls');
          controls.append(button(t('Установленные','Installed'),()=>placeExtensions('installed')),
            button(t('Chrome Web Store','Chrome Web Store'),()=>placeExtensions('store')));
          const help=el('details',undefined,'extension-help');help.append(el('summary',t('Локальная установка и совместимость','Local installation and compatibility')));
          help.append(el('p',t('Для локальной установки включите «Режим разработчика» ниже и нажмите «Загрузить распакованное расширение». Выберите папку с manifest.json. Разрешения и удаление доступны в карточке расширения.','For local installation, enable Developer mode below and choose Load unpacked. Select the folder containing manifest.json. Permissions and removal are available on each extension card.'),'note'));
          help.append(el('p',t('Совместимость зависит от расширения. Функции, требующие панели Chrome, могут быть недоступны в оболочке Sona.','Compatibility depends on the extension. Features requiring the Chrome toolbar may be unavailable in the Sona shell.'),'note'));
          help.addEventListener('toggle',scheduleExtensions);n.append(controls,help);
          const host=el('div',undefined,'extensions-surface');host.id='extensionsSurface';n.append(host);
          const pins=el('div',undefined,'extension-pin-list');pins.id='extensionPins';n.insertBefore(pins,host);
          renderExtensionPins(pins);
          card.append(n);requestAnimationFrame(()=>placeExtensions());continue;
        }
        if(r.key==='defaultBrowser')text.append(el('small',t(state.capabilities?.defaultBrowser?'Sona используется как браузер по умолчанию':'Sona не является браузером по умолчанию',state.capabilities?.defaultBrowser?'Sona is the default browser':'Sona is not the default browser')));if(r.type==='vpnProfiles'){n.classList.add('long');const host=el('div',undefined,'vpn-profile-manager');n.append(host);window.sonaVpnSettings.render(host);}else if(r.type==='components'){n.classList.add('long');const host=el('div',undefined,'component-manager');n.append(host);window.sonaComponents.render(host);}else if(r.type==='action'){if(r.key==='versions'){const grid=el('div',undefined,'version-grid');for(const [name,value] of [['Sona',state.update?.sona],['CEF',state.update?.cef],['Chromium',state.update?.chromium]]){const cell=el('div');cell.append(el('span',name),el('strong',value||'—'));grid.append(cell);}n.classList.add('long');n.append(grid,el('p',t('Автоматическая проверка и установка обновлений пока недоступны.','Automatic update checks and installation are not available.'),'note'));}else n.append(button(r.key==='defaultBrowser'?t(state.capabilities?.defaultBrowser?'Настройки Windows':'Сделать основным',state.capabilities?.defaultBrowser?'Windows settings':'Make default'):t('Открыть','Open'),()=>runAction(r.key)));}
        else if(r.type==='segments'){const box=el('div',undefined,'segments');box.setAttribute('role','radiogroup');box.setAttribute('aria-label',t(r.ru,r.en));for(const o of r.options){const label=el('label'),input=el('input');input.type='radio';input.name=r.store+'-'+r.key;input.value=o.value;input.checked=get(r)===o.value;input.onchange=()=>set(r,o.value);label.append(input,el('span',t(o.ru,o.en)));box.append(label);}n.append(box);}
        else{const input=el(r.type==='select'?'select':r.type==='textarea'?'textarea':'input');input.id=r.store==='settings'?r.key:r.store+'-'+r.key;input.setAttribute('aria-label',t(r.ru,r.en));if(r.type==='select'){for(const o of (r.store==='reader'&&r.key==='font'&&current.readerFonts?current.readerFonts.map(f=>opt(f.id,f.label)):r.options))input.append(new Option(t(o.ru,o.en),o.value));if(r.store==='reader'&&r.key==='size'&&!r.options.some(o=>o.value===get(r)))input.append(new Option(String(get(r)),get(r)));input.value=get(r);}else{if(r.type!=='textarea')input.type=r.type==='toggle'?'checkbox':r.type==='url'?'url':'text';if(r.type==='toggle')input.checked=get(r)!==false;else input.value=get(r)||'';if(r.type==='url')input.placeholder='https://example.com';if(r.key==='downloadPath'){input.placeholder=t('Папка загрузок Windows','Windows downloads folder');input.title=input.value;}}
          input.onchange=()=>{if(r.key.endsWith('Mode')&&['startupMode','newTabMode','homeMode'].includes(r.key)&&input.value==='custom'&&!current.settings[r.key.replace('Mode','Url')]){const target=$('control-settings-'+r.key.replace('Mode','Url'));target.hidden=false;const field=target.querySelector('input');field.disabled=false;field.dataset.customMode=r.key;field.focus();return;}if(input.dataset.customMode){current.settings[input.dataset.customMode]='custom';delete input.dataset.customMode;}set(r,r.type==='toggle'?input.checked:input.value);};if(['text','url','textarea'].includes(r.type))input.onkeydown=e=>{if(e.key==='Enter'&&r.type!=='textarea'){e.preventDefault();input.blur();}};if(r.store==='settings'&&r.type==='toggle')input.dataset.setting=r.key;n.append(input);}
        card.append(n);
      }content.append(card);
    }if(state.capabilities?.matteAvailable===false){const row=$('control-settings-mattePanel');if(row){row.querySelector('input').disabled=!current.settings.mattePanel;row.querySelector('span').append(el('small',t('Эффект недоступен при текущих настройках прозрачности или контрастности Windows.','The effect is unavailable with the current Windows transparency or contrast settings.')));}}updateConditional();
  }

  async function renderExtensionPins(host){
    const profile=current.profile;
    try{
      const data=await window.browserShell.extensions('list',{profile});
      if(!host.isConnected||current?.profile!==profile)return;
      const signature=JSON.stringify((data.items||[]).map(e=>[e.id,e.enabled,e.pinned,e.version]));if(host.dataset.signature===signature)return;host.dataset.signature=signature;
      host.replaceChildren();host.append(el('b',t('Расширения в меню','Extensions in menu')));
      for(const item of (data.items||[])){
        const row=el('label',undefined,'extension-pin-row');
        if(/^data:image\//.test(item.icon||'')){const image=el('img');image.src=item.icon;image.alt='';row.append(image);}
        row.append(el('span',item.name));const toggle=el('input');toggle.type='checkbox';toggle.checked=item.enabled;toggle.disabled=false;toggle.dataset.extensionId=item.id;toggle.setAttribute('aria-label',t('Включить расширение: ','Enable extension: ')+item.name);
        toggle.onchange=async()=>{const wanted=toggle.checked;toggle.disabled=true;try{await window.browserShell.extensions('setEnabled',{profile,id:item.id,enabled:wanted});}catch(error){toggle.checked=!wanted;report(error);}finally{toggle.disabled=false;scheduleExtensions();}};
        row.append(toggle);host.append(row);
      }
      if(!(data.items||[]).length)host.append(el('small',t('Установленные пользовательские расширения появятся здесь.','Installed user extensions appear here.')));
      scheduleExtensions();
    }catch(error){if(host.isConnected){host.textContent=error.message;report(error);}}
  }
  setInterval(()=>{const host=$('extensionPins');if(current&&section==='extensions'&&host)renderExtensionPins(host);},3000);
  let extensionFrame=0;
  function placeExtensions(page){
    const host=$('extensionsSurface'),viewport=$('settingsContent');
    const visible=section==='extensions'&&host&&host.getClientRects().length&&!$('actionDialog').open&&!$('settingsSearch').value.trim();
    if(!visible)return invoke('extensions',{visible:false}).catch(report);
    const rect=host.getBoundingClientRect(),clip=viewport.getBoundingClientRect();
    const x=Math.max(0,rect.left,clip.left),y=Math.max(0,rect.top,clip.top);
    const right=Math.min(innerWidth,rect.right,clip.right),bottom=Math.min(innerHeight,rect.bottom,clip.bottom);
    if(right<=x||bottom<=y)return invoke('extensions',{visible:false}).catch(report);
    return invoke('extensions',{visible:true,x,y,width:right-x,height:bottom-y,...(page?{page}:{})}).catch(report);
  }
  function scheduleExtensions(){cancelAnimationFrame(extensionFrame);extensionFrame=requestAnimationFrame(()=>placeExtensions());}
  window.addEventListener('resize',scheduleExtensions);
  $('settingsContent').addEventListener('scroll',scheduleExtensions);
  $('actionDialog').addEventListener('close',scheduleExtensions);
  new MutationObserver(scheduleExtensions).observe($('actionDialog'),{attributes:true,attributeFilter:['open']});

  // Own the Settings transition separately from viewport-resize cancellation.
  // Native height animation resizes the renderer; that must not interrupt fades.
  const sectionAnimations=new Set();
  function prepareSectionMotion(id,target){
    for(const animation of sectionAnimations)animation.cancel();sectionAnimations.clear();
    return id!==section||!!target;
  }
  function finishSectionMotion(changed,id){
    if(!changed)return;
    const reduced=window.sonaMotion.reduced;
    for(const node of [$('settingsContent'),...(id?[document.querySelector('aside')]:[])]){
      const animation=node.animate([{opacity:0,transform:reduced?'none':'translateY(5px)'},{opacity:1,transform:'none'}],
        {duration:reduced?90:320,delay:reduced?0:45,easing:'cubic-bezier(.25,.1,.25,1)',fill:'backwards'});
      sectionAnimations.add(animation);
      animation.finished.then(scheduleExtensions,()=>{}).finally(()=>sectionAnimations.delete(animation));
    }
  }

  function openSection(id,target,fromCard=false){$('dataMessage').textContent='';$('dataMessage').classList.remove('error');$('sectionError')?.remove();if(section==='extensions')invoke('extensions',{visible:false}).catch(report);const previous=section;const transition=prepareSectionMotion(id,target,fromCard);section=id;$('settingsSearch').value='';document.querySelector('main').dataset.view=id?'section':'home';document.querySelector('aside').hidden=!id;$('homeCards').hidden=!!id;$('sectionContent').hidden=!id;$('searchResults').hidden=true;render();$('settingsContent').scrollTop=0;if(target){const n=$('control-'+target);if(n){if(n.hidden){n.hidden=false;n.querySelector('span').append(el('small',t('Выберите «Указанный адрес», чтобы изменить эту страницу.','Choose Custom address to edit this page.'),'search-mode-note'));}n.scrollIntoView({block:'center',behavior:'smooth'});n.classList.add('setting-highlight');n.focus({preventScroll:true});setTimeout(()=>n.classList.remove('setting-highlight'),2200);}}else if(!id&&previous)document.querySelector('#homeCards [data-section="'+previous+'"]')?.focus({preventScroll:true});else $('settingsContent').focus({preventScroll:true});finishSectionMotion(transition,id);}
  function showSearch(){scheduleExtensions();resizePanel();window.sonaMotion.cancel();const query=$('settingsSearch').value.trim().toLowerCase().replaceAll('ё','е');$('clearSearch').hidden=!query;$('searchResults').hidden=!query;$('homeCards').hidden=!!query||!!section;$('sectionContent').hidden=!!query||!section;if(!query)return;const box=$('searchResults');box.replaceChildren();const results=index.filter(x=>query.split(/\s+/).every(word=>x.hay.includes(word)));for(const r of results){const b=button('',()=>openSection(r.section,r.key),'result');const text=el('span');text.append(el('strong',r.title),el('small',r.path));b.append(icon(r.section),text);box.append(b);}if(!results.length)box.append(el('p',t('Ничего не найдено','No settings found'),'note'));}
  async function requestClose(){window.sonaMotion.cancel();document.activeElement?.blur();await queue;await invoke('close').catch(report);}
  function dialog(title,build){$('actionTitle').textContent=title;$('actionMessage').textContent='';$('actionContent').replaceChildren();build($('actionContent'));if(!$('actionDialog').open)$('actionDialog').showModal();}
  async function runAction(key){if(key==='optimizeNow'){await window.browserShell.optimizeBackgroundTabs();$('dataMessage').textContent=t('Оптимизация фоновых вкладок запущена.','Background tab optimization has started.');return;}if(key==='history'||key==='clearData')return window.browserShell.openHistory(key==='clearData');if(key==='defaultBrowser')return invoke('defaultBrowser');if(key==='chooseFolder'){const path=await invoke('chooseFolder');if(path){current.settings.downloadPath=path;changed();renderSection();}return;}if(key==='openFolder')return invoke('openFolder');if(key==='incognito')return window.browserShell.newIncognito();if(key==='parseVpn'){const parsed=window.sonaParseVpnKey(current.vpn.link);Object.assign(current.vpn,parsed);changed();dialog(t('Ключ распознан','Key parsed'),box=>{for(const [ru,en,value] of [['Протокол','Protocol',parsed.protocol],['Сервер','Server',parsed.address],['Название из ключа','Label from key',parsed.region]])box.append(el('p',t(ru,en)+': '+value));box.append(el('p',t('Конфигурация сохраняется автоматически.','Configuration is saved automatically.'),'note'));});return;}
    if(key==='vpnStatus'){const result=await window.vpn.send('status');dialog(t('Состояние VPN','VPN status'),box=>{box.append(el('p',result?.error||t(result?.connected?'Подключён':'Отключён',result?.connected?'Connected':'Disconnected')));});return;}
    if(key==='siteData')return window.sonaSettingsData.siteData();
    if(key==='homeFavorites')return editHomeFavorites();
    if(key==='videoOptions')return window.sonaVideoSettings.open();
    if(key==='weatherPermission')return editWeatherPermission();
    if(key==='weatherCredits')return dialog(t('Источники погоды','Weather sources'),box=>{const link=el('a','Weather data by Open-Meteo.com');link.href='https://open-meteo.com/';link.onclick=e=>{e.preventDefault();window.browserShell.openTab(link.href);};const license=el('a','CC BY 4.0');license.href='https://creativecommons.org/licenses/by/4.0/';license.onclick=e=>{e.preventDefault();window.browserShell.openTab(license.href);};box.append(link,el('p',t('Температура округляется, условия представлены значками.','Temperatures are rounded and conditions are represented by icons.'),'note'),license);});
    if(key==='exceptions'||key==='adblockExceptions')return editExceptions(key==='adblockExceptions');
    if(window.sonaSettingsData)return window.sonaSettingsData.action(key);
  }
  function editWeatherPermission(){dialog(t('Геолокация погоды','Weather location'),box=>{const select=el('select');select.setAttribute('aria-label',t('Доступ к местоположению','Location access'));select.append(new Option(t('Разрешить','Allow'),'0'),new Option(t('Не разрешать','Do not allow'),'2'));select.value=String(current.rules.sites['sona://home']?.geolocation??2);select.onchange=()=>{current.rules.sites['sona://home']={...(current.rules.sites['sona://home']||{}),geolocation:Number(select.value)};changed();};box.append(select,el('p',t('Windows также должен разрешать доступ к местоположению. Координаты округляются до района и передаются только погодному сервису Open-Meteo.','Windows must also allow location access. Coordinates are rounded to the area and sent only to the Open-Meteo weather service.'),'note'));});}
  async function editHomeFavorites(){const rows=await window.browserShell.getBookmarks();dialog(t('Избранное Home','Home favorites'),box=>{
    const valid=rows.filter(item=>{try{return item.type!=='folder'&&['http:','https:'].includes(new URL(item.url).protocol);}catch{return false;}});
    const selected=()=>current.settings.homeFavoriteIds||[];
    function draw(){box.replaceChildren();const ids=selected();for(const id of ids){const item=valid.find(row=>row.id===id);if(!item)continue;const n=el('div',undefined,'profile-row');n.append(el('span',item.title||item.url),button(t('Убрать из избранного','Remove from favorites'),()=>{current.settings.homeFavoriteIds=selected().filter(value=>value!==id);changed();draw();}),button(t('Выше','Move up'),()=>{const order=[...selected()],i=order.indexOf(id);if(i>0){[order[i-1],order[i]]=[order[i],order[i-1]];current.settings.homeFavoriteIds=order;changed();draw();}}));box.append(n);}for(const item of valid.filter(row=>!ids.includes(row.id))){const n=el('div',undefined,'profile-row');n.append(el('span',item.title||item.url),button(t('Добавить в избранное','Add to favorites'),()=>{current.settings.homeFavoriteIds=[...selected(),item.id];changed();draw();}));box.append(n);}if(!valid.length)box.append(el('p',t('Сначала сохраните нужные сайты в закладки.','Save your preferred sites as bookmarks first.'),'note'));}draw();
  });}
  function editExceptions(blocking){dialog(t(blocking?'Исключения блокировки рекламы':'Исключения разрешений',blocking?'Ad blocking exceptions':'Permission exceptions'),box=>{const search=el('input');search.type='search';search.placeholder=t('Поиск по домену','Search domains');search.setAttribute('aria-label',search.placeholder);const list=el('div');box.append(search,list);const data=()=>blocking?current.rules.blocking.sites:current.rules.sites;
      function draw(){list.replaceChildren();for(const domain of Object.keys(data()).sort().filter(d=>d.includes(search.value.toLowerCase()))){const n=el('div',undefined,'profile-row');n.append(el('span',domain+(blocking?' · '+t(data()[domain]?'Блокировать':'Разрешать',data()[domain]?'Block':'Allow'):'')),button(t('Изменить','Edit'),()=>editDomain(domain,blocking)),button(t('Удалить исключение','Remove exception'),()=>{delete data()[domain];changed();draw();}));list.append(n);}if(!list.children.length)list.append(el('p',t('Исключений нет','No exceptions'),'note'));}
      search.oninput=draw;draw();const input=el('input');input.type='text';input.placeholder='example.com';input.setAttribute('aria-label',t('Домен','Domain'));box.append(input,button(t('Добавить сайт','Add site'),()=>{const u=new URL(input.value.includes('://')?input.value:'https://'+input.value);if(!['http:','https:'].includes(u.protocol)||!u.hostname||u.username||u.password)throw Error(t('Укажите HTTP/HTTPS-сайт','Enter an HTTP/HTTPS site'));editDomain(u.hostname.toLowerCase().replace(/\.$/,''),blocking);}),button(t('Сбросить все исключения','Reset all exceptions'),()=>{if(confirm(t('Сбросить все исключения этой группы?','Reset all exceptions in this group?'))){for(const k of Object.keys(data()))delete data()[k];changed();draw();}}));});}
  function editDomain(domain,blocking){dialog(domain,box=>{if(blocking){const select=el('select');select.append(new Option(t('По умолчанию','Default'),'default'),new Option(t('Разрешать рекламу','Allow ads'),'false'),new Option(t('Блокировать рекламу','Block ads'),'true'));select.value=current.rules.blocking.sites[domain]===undefined?'default':String(current.rules.blocking.sites[domain]);select.setAttribute('aria-label',t('Блокировка рекламы','Ad blocking'));select.onchange=()=>{if(select.value==='default')delete current.rules.blocking.sites[domain];else current.rules.blocking.sites[domain]=select.value==='true';changed();};box.append(select);}else for(const [key,ru,en] of permissionNames){const n=el('label',undefined,'row'),select=el('select');select.append(new Option(t('По умолчанию','Default'),'-1'));(key==='sound'?[t('Разрешать','Allow'),t('Приглушать','Mute'),t('Блокировать','Block')]:[t('Разрешать','Allow'),t('Спрашивать','Ask'),t('Блокировать','Block')]).forEach((text,i)=>select.append(new Option(text,i)));select.value=current.rules.sites[domain]?.[key]??-1;select.onchange=()=>{const rules=current.rules.sites[domain]||{};if(select.value==='-1')delete rules[key];else rules[key]=Number(select.value);if(Object.keys(rules).length)current.rules.sites[domain]=rules;else delete current.rules.sites[domain];changed();};n.append(el('span',t(ru,en)),select);box.append(n);}box.append(button(t('Все исключения','All exceptions'),()=>editExceptions(blocking)));});}
  $('settingsSearch').oninput=showSearch;$('clearSearch').onclick=()=>{$('settingsSearch').value='';showSearch();$('settingsSearch').focus();};$('closeSettings').onclick=requestClose;
  $('closeAction').onclick=()=>{$('actionDialog').close();$('actionContent').replaceChildren();};$('actionDialog').addEventListener('close',()=>{$('actionContent').replaceChildren();});
  document.addEventListener('keydown',e=>{if(e.altKey&&e.key==='ArrowLeft'&&section&&!document.querySelector('dialog[open]')){e.preventDefault();openSection('');}if(e.key==='Escape'&&!document.querySelector('dialog[open]')){e.preventDefault();requestClose();}if(e.target.closest('#sectionNav')&&['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();const buttons=[...$('sectionNav').children],i=buttons.indexOf(e.target);buttons[e.key==='Home'?0:e.key==='End'?buttons.length-1:(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length].focus();}});
  window.addEventListener('focus',()=>{if(section==='extensions'&&$('extensionPins'))renderExtensionPins($('extensionPins'));if(current)invoke('capabilities').then(capabilities=>{state.capabilities=capabilities;if(section==='general')renderSection();}).catch(()=>{});});
  document.addEventListener('keydown',e=>{
    if(e.ctrlKey&&e.key.toLowerCase()==='f'){e.preventDefault();$('settingsSearch').focus();}
    if(e.ctrlKey&&e.key.toLowerCase()==='w'){e.preventDefault();requestClose();}
    if(e.key!=='Tab')return;
    const root=document.querySelector('dialog[open]')||document.querySelector('main');
    const items=[...root.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex="0"]')].filter(n=>n.getClientRects().length);
    const first=items[0],last=items.at(-1);if(!first)return;
    if(e.shiftKey&&(document.activeElement===first||!items.includes(document.activeElement))){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&(document.activeElement===last||!items.includes(document.activeElement))){e.preventDefault();first.focus();}
  });
  // Home hugs its entries; sections retain the full desktop workspace.
  // Observe intrinsic content rather than shell height to avoid resize loops.
  let resizeFrame=0,lastPanelHeight=0;
  function measurePanelHeight(){
      const content=$('settingsContent'),style=getComputedStyle(content);
      if(!section&&!$('settingsSearch').value.trim()){
        const cards=[...$('homeCards').children],first=cards[0]?.getBoundingClientRect();
        const firstRow=cards.filter(card=>Math.abs(card.getBoundingClientRect().top-first?.top)<1);
        const rightColumn=firstRow.length>1?firstRow.at(-1):null;
        if(rightColumn){const search=document.querySelector('.search-box').getBoundingClientRect();
          document.querySelector('main').style.setProperty('--settings-search-width',Math.max(160,Math.floor(search.right-rightColumn.getBoundingClientRect().left))+'px');}
      }

      const searching=!!$('settingsSearch').value.trim();
      const entries=searching?$('searchResults'):$('homeCards');
      const height=section&&!searching?800:Math.min(800,Math.max(160,Math.ceil(
        document.querySelector('.settings-header').getBoundingClientRect().height+
        entries.getBoundingClientRect().height+parseFloat(style.paddingTop)+parseFloat(style.paddingBottom)+2)));
      const action=$('actionDialog');
      return action.open&&action.classList.contains('browser-import-dialog')?Math.max(height,640,Math.min(800,action.scrollHeight+40)):height;
  }
  function resizePanel(){cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{if(!current)return;const height=measurePanelHeight();if(height===lastPanelHeight)return;lastPanelHeight=height;invoke('resize',{height}).catch(report);});}
  const contentSize=new ResizeObserver(resizePanel);
  for(const node of [$('homeCards'),$('searchResults'),document.querySelector('.settings-header'),$('actionDialog')])contentSize.observe(node);
  window.addEventListener('resize',resizePanel);
  window.sonaSettingsProfileChanged=async()=>{window.sonaMotion.cancel();
    if($('actionDialog').open)$('actionDialog').close();
    const pending=queue;current=null;persisted=null;loaded=null;document.body.classList.remove('ready');
    await pending.catch(()=>{});queue=Promise.resolve();await window.sonaSettings.reload();
  };
  window.sonaSettingsRequestClose=requestClose;
  window.sonaSettings={t,el,button,dialog,report,invoke,changed,flush:()=>queue,get state(){return state;},get current(){return current;},get persisted(){return persisted;},get loaded(){return loaded;},reload:async()=>{if(reloading)return;reloading=true;try{persisted=await invoke('begin');loaded=clone(persisted);current=clone(persisted);state={...await window.browserShell.getState(),capabilities:await invoke('capabilities')};render();document.body.classList.add('ready');}finally{reloading=false;}},openSection};
  window.browserShell.onState(next=>{state={...next,capabilities:state.capabilities};if(!current&&loaded?.profile===next.activeProfileId){window.sonaSettings.reload().catch(report);return;}if(persisted&&next.activeProfileId!==persisted.profile){current=null;persisted=null;if($('actionDialog').open)$('actionDialog').close();document.body.classList.remove('ready');$('sectionContent').replaceChildren();$('homeCards').replaceChildren();report(t('Активный профиль изменился. Откройте настройки из него.','The active profile changed. Open settings from that profile.'));} });
  Promise.all([invoke('begin'),window.browserShell.getState(),invoke('capabilities'),window.sonaTypographyReady]).then(async ([snapshot,next,capabilities])=>{loaded=clone(snapshot);persisted=clone(snapshot);current=clone(snapshot);state={...next,capabilities};render();if(snapshot.requestedSection==='vpn')openSection('vpn');document.body.classList.add('ready');document.querySelector('main').setAttribute('aria-busy','false');$('settingsSearch').focus();await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));cancelAnimationFrame(resizeFrame);const height=measurePanelHeight();await invoke('resize',{height});lastPanelHeight=height;await invoke('ready',{height});}).catch(report);
})();
