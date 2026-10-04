(() => {
  'use strict';
  const api = window.browserShell, safe = window.souluReaderSafe;
  if (!api?.getCurrentSite || !safe) return;
  let state = {}, site = null, key = '', revision = 0, anchor = null, articleKey = '', saving = Promise.resolve(), probing = false;
  let menuSignature = '', preferencesSignature = '', reloadMenu = null, level = 'main', picking = '', promptId = 0;
  const el = (tag, cls, text) => { const n = document.createElement(tag); n.className = cls || ''; if (text !== undefined) n.textContent = text; return n; };
  const error = e => { status.textContent = e.message || String(e); status.hidden = false; if (!reader.hidden) { readerNotice.textContent = status.textContent; readerNotice.hidden = false; } };
  const button = (text, fn, cls = '') => { const n = el('button', cls, text); n.type = 'button'; n.onclick = () => Promise.resolve().then(fn).catch(error); return n; };
  const shield = el('div', 'site-shield'), menu = el('section', 'site-popover'), reader = el('section', 'reader-view');
  shield.hidden = menu.hidden = reader.hidden = true;
  menu.setAttribute('role', 'dialog'); menu.setAttribute('aria-label', 'Функции текущего сайта');
  const status = el('p', 'site-status'); status.setAttribute('role', 'status'); status.hidden = true;
  const content = el('div', 'site-menu-content'); menu.append(content, status);
  document.body.append(reader, shield, menu);
  const readerBar = el('div', 'reader-toolbar'), article = el('article', 'reader-article'), settings = el('section', 'reader-settings');
  const readerNotice = el('p', 'reader-notice'); readerNotice.hidden = true; readerNotice.setAttribute('role', 'status');
  settings.hidden = true; settings.setAttribute('aria-label', 'Оформление режима чтения');
  const exit = button('‹ К странице', () => act('reader.exit'));
  const style = button('Оформление · Aa', () => { settings.hidden = !settings.hidden; style.setAttribute('aria-expanded', String(!settings.hidden)); });
  style.setAttribute('aria-expanded', 'false');
  readerBar.append(exit, el('span', '', 'Режим чтения'), style); reader.append(readerBar, readerNotice, settings, article);
  let linkMenu = null;
  async function expandSurface(owner = 'site-reader') {
    await api.setPopover(true, owner);
    const current = await api.getState();
    const height = current.clientHeight || 200;
    // A bridge reply precedes CEF's asynchronous WasResized frame. Focusing
    // before the viewport arrives can scroll the document above the titlebar.
    await new Promise(resolve => {
      const deadline = performance.now() + 2000;
      const ready = () => { if (innerHeight >= height || performance.now() >= deadline) resolve(); else setTimeout(ready, 16); };
      ready();
    });
  }
  const closeLink = () => { linkMenu?.remove(); linkMenu = null; };
  function updateSurface() { return api.setPopover(!menu.hidden || !findBox.hidden || Boolean(linkMenu), 'site-reader'); }
  function close(focus = false) {
    menu.hidden = shield.hidden = true; closeLink(); updateSurface();
    anchor?.setAttribute('aria-expanded', 'false'); if (focus && anchor?.isConnected) anchor.focus();
  }
  function token(snapshot = site) { return {tabId: snapshot.tabId, url: snapshot.url, generation: snapshot.generation}; }
  async function act(action, values = {}, snapshot = site) {
    if (!snapshot) return;
    if (['blocking', 'reset'].includes(action) && !menu.hidden) reloadMenu = token(snapshot);
    let result;
    try { result = await api.siteAction(action, {...token(snapshot), ...values}); }
    catch (e) { if (['blocking', 'reset'].includes(action)) reloadMenu = null; throw e; }
    if (result?.tabId && key === `${result.tabId}|${result.url}|${result.generation}`) {
      site = result; renderReader(); if (!menu.hidden) renderMenu();
    }
    return result;
  }
  function position() {
    const rect = anchor?.isConnected ? anchor.getBoundingClientRect() : {left: 12, bottom: state.settings?.layout === 'classic' ? 82 : 48};
    // The closed OSR viewport is only toolbar-height. Do not use that height
    // to move a newly opened surface above its anchor. CSS tracks the expanded
    // viewport and supplies scrolling for long/nested content.
    const top = Math.max(8, rect.bottom + 8);
    menu.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - menu.offsetWidth - 8))}px`;
    menu.style.top = `${top}px`;
    menu.style.maxHeight = `max(0px, calc(100% - ${top + 8}px))`;
    const toolbar = (state.settings?.layout === 'classic' ? 82 : 48) + (state.bookmarksBarVisible ? 28 : 0);
    prompt.style.top = `${toolbar + 8}px`;
    prompt.style.maxHeight = `max(0px, calc(100% - ${toolbar + 16}px))`;
    findBox.style.top = `${toolbar + 8}px`;
    findBox.style.maxHeight = `max(0px, calc(100% - ${toolbar + 16}px))`;
  }
  async function open() {
    closeLink(); settings.hidden = true; style.setAttribute('aria-expanded', 'false');
    anchor = document.querySelector('body[data-layout=classic] #classicPageMenu') || document.querySelector('[data-page-menu]') || document.querySelector('#classicPageMenu');
    const request = ++revision; const snapshot = await api.getCurrentSite();
    if (request !== revision) return;
    // Request native bounds before exposing or focusing client-area content.
    await expandSurface();
    if (request !== revision) { updateSurface(); return; }
    level = 'main'; picking = ''; menuSignature = ''; site = snapshot; probing = Boolean(site.origin && !site.mainLoading && !site.readerActive); menu.hidden = shield.hidden = false; status.hidden = true;
    anchor?.setAttribute('aria-expanded', 'true'); renderMenu(); position();
    menu.querySelector('button:not(:disabled)')?.focus();
    if (site.origin && !site.mainLoading && !site.readerActive) {
      const result = await act('reader.probe', {}, snapshot).catch(e => { if (request === revision && !menu.hidden) error(e); });
      if (request === revision) { probing = false; if (!menu.hidden) renderMenu(); }
    }
  }
  api.pageMenu = () => open().catch(error);
  shield.onpointerdown = () => close(true);
  function select(label, options, value, change) {
    const row = el('label', 'site-control'), control = el('select'); control.setAttribute('aria-label', label);
    for (const [v, name] of options) control.append(new Option(name, String(v)));
    control.value = String(value); control.onchange = () => Promise.resolve(change(control.value)).catch(error);
    row.append(el('span', '', label), control); return row;
  }
  const names = {geolocation:'Геолокация',camera:'Камера',microphone:'Микрофон',notifications:'Уведомления',sound:'Звук',popups:'Всплывающие окна',downloads:'Загрузки'};
  const paths = {
    geolocation:'M10 18s6-6 6-11a6 6 0 1 0-12 0c0 5 6 11 6 11Z M12 7a2 2 0 1 1-4 0 2 2 0 0 1 4 0',
    camera:'M3 5h10v10H3z M13 8l4-2v8l-4-2',
    microphone:'M7 4a3 3 0 0 1 6 0v6a3 3 0 0 1-6 0z M4 9v1a6 6 0 0 0 12 0V9 M10 16v3 M7 19h6',
    notifications:'M4 14c2-2 1-4 2-7a4 4 0 0 1 8 0c1 3 0 5 2 7H4 M8 17a2 2 0 0 0 4 0 M10 2V1',
    sound:'M3 8h3l4-4v12l-4-4H3z M13 6c3 2 3 6 0 8 M15 3c5 4 5 10 0 14',
    popups:'M11 3h6v6 M17 3l-8 8 M7 4H3v13h13v-4',
    downloads:'M10 2v11 M6 9l4 4 4-4 M3 17h14',
    reader:'M4 2h12v16H4z M7 6h6 M7 9h6 M7 12h4',
    find:'M13 8a5 5 0 1 1-10 0 5 5 0 0 1 10 0 M12 12l5 5',
    zoom:'M13 8a5 5 0 1 1-10 0 5 5 0 0 1 10 0 M12 12l5 5 M5 8h6 M8 5v6',
    settings:'M3 5h14 M3 10h14 M3 15h14 M7 3v4 M13 8v4 M8 13v4',
    shield:'M10 2l7 3v5c0 4-7 8-7 8S3 14 3 10V5z',
    trash:'M3 5h14 M7 5V2h6v3 M5 5l1 13h8l1-13 M8 8v7 M12 8v7',
    reset:'M3 7a7 7 0 1 1 0 6 M3 2v5h5',
    back:'M11 4l-6 6 6 6 M5 10h12',
    chevron:'M8 5l5 5-5 5',
    globe:'M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0 M2 10h16 M10 2c-5 5-5 11 0 16 M10 2c5 5 5 11 0 16',
    close:'M5 5l10 10 M15 5L5 15'
  };
  function glyph(name) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 20 20'); svg.setAttribute('aria-hidden', 'true'); svg.classList.add('site-icon');
    const path = document.createElementNS(svg.namespaceURI, 'path'); path.setAttribute('d', paths[name] || paths.globe); svg.append(path); return svg;
  }
  function row(text, name, fn, value = '', chevron = false) {
    const b = button('', fn, 'site-row'); b.setAttribute('aria-label', text);
    b.append(glyph(name), el('span', 'site-row-label', text));
    if (value) b.append(el('span', 'site-row-value', value));
    if (chevron) b.append(glyph('chevron')); return b;
  }
  function toggle(label, checked, change, name) {
    const wrap = el('div', 'site-row'); if (name) wrap.append(glyph(name)); wrap.append(el('span', 'site-row-label', label));
    const b = button('', () => change(!checked), 'soulu-site-toggle'); b.setAttribute('role', 'switch');
    b.setAttribute('aria-checked', String(checked)); b.setAttribute('aria-label', label); wrap.append(b); return wrap;
  }
  const divider = () => el('hr', 'site-divider');
  function navigateLevel(next, permission = '') {
    const backwards = next === 'main' || (next === 'settings' && level !== 'main');
    level = next; picking = permission; menuSignature = ''; renderMenu(); position();
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) content.animate(
      [{opacity:0,transform:`translateX(${backwards ? -6 : 6}px)`},{opacity:1,transform:'translateX(0)'}],
      {duration:180,easing:'cubic-bezier(.22,1,.36,1)'});
    content.querySelector('button:not(:disabled)')?.focus();
  }
  function permissionValue(name) {
    const override = site.rules.sites?.[site.domain]?.[name];
    return override === undefined ? 'По умолчанию' : name === 'sound' ? ['Разрешено','Приглушено','Запрещено'][override] : ['Разрешено','Спрашивать','Запрещено'][override];
  }
  function renderMenu() {
    if (!site) return;
    const signature = JSON.stringify([level,picking,probing,...['tabId','url','generation','origin','domain','favicon','secureConnection','readerActive','readerAvailable','mainLoading','zoom','rules'].map(name => site[name]),site.adblock?.ready,site.adblock?.active,site.adblock?.blockedRequests]);
    if (content.childElementCount && menuSignature === signature) return;
    menuSignature = signature;
    const focusedLabel = content.contains(document.activeElement) && document.activeElement?.getAttribute('aria-label');
    content.replaceChildren(); menu.dataset.level = level;
    if (level !== 'main') {
      const title = level === 'settings' ? 'Настройки сайта' : level === 'picker' ? names[picking] : level === 'clear' ? 'Очистить данные сайта?' : 'Сбросить настройки сайта?';
      const header = row(title, 'back', () => navigateLevel(level === 'settings' ? 'main' : 'settings')); header.classList.add('site-back'); content.append(header);
      content.append(el('small', 'site-hint site-domain', site.domain), divider());
      if (level === 'settings') {
        for (const [name, label] of Object.entries(names)) if (Object.hasOwn(site.rules.defaults, name)) {
          const b = row(label, name, () => navigateLevel('picker', name), permissionValue(name), true); b.dataset.permission = name; content.append(b);
        }
        content.append(divider(), row('Очистить данные сайта…', 'trash', () => navigateLevel('clear')),
          row('Сбросить настройки сайта', 'reset', () => navigateLevel('reset')));
      } else if (level === 'picker') {
        const current = site.rules.sites?.[site.domain]?.[picking] ?? -1;
        const labels = picking === 'sound' ? ['Разрешить','Приглушить','Запретить'] : ['Разрешить','Спрашивать','Запретить'];
        for (const [value, label] of [[-1,'По умолчанию'], ...labels.map((v, i) => [i, v])]) {
          const b = button(label, async () => { await act('permission', {permission:picking,value}); navigateLevel('settings'); }, 'site-row site-choice');
          b.dataset.value = value; b.setAttribute('aria-pressed', String(current === value));
          if (current === value) b.append(el('span', 'site-check', '✓')); content.append(b);
        }
        const defaults = site.rules.defaults[picking]; content.append(el('small', 'site-hint', `По умолчанию: ${labels[defaults]}`));
      } else {
        content.append(el('p', 'site-confirm-text', level === 'clear'
          ? `Удалить localStorage, sessionStorage, IndexedDB, Cache Storage и service workers для ${site.origin}? Cookies, HTTP-кэш, пароли и другие сайты сохранятся.`
          : 'Удалить исключения разрешений и рекламы для этого домена? Будут применены общие настройки. Данные сайта сохранятся.'));
        const actions = el('div', 'site-confirm-actions');
        actions.append(button('Отмена', () => navigateLevel('settings')));
        const confirm = button(level === 'clear' ? 'Очистить' : 'Сбросить', async () => {
          const action = level; confirm.disabled = true;
          try { const result = await act(action, action === 'clear' ? {confirmed:true} : {});
            navigateLevel('settings'); status.textContent = action === 'clear' && result?.cleared ? 'Данные сайта очищены. Cookies и HTTP-кэш сохранены.' : 'Настройки сайта сброшены.'; status.hidden = false;
          } finally { confirm.disabled = false; }
        }, 'site-primary'); confirm.dataset.confirm = level; actions.append(confirm); content.append(actions);
      }
    } else {
      const head = el('header', 'site-heading'), identity = el('div', 'site-identity'); identity.append(glyph('globe'));
      if (safe.webURL(site.favicon, site.url) || /^data:image\/(png|jpeg|webp|x-icon);base64,/i.test(site.favicon || '')) {
        const icon = el('img'); icon.src = site.favicon; icon.alt = ''; icon.onload = () => identity.firstChild?.classList.add('site-fallback-hidden'); icon.onerror = () => icon.remove(); identity.append(icon);
      }
      const info = el('div'); info.append(el('strong', '', site.domain || 'Внутренняя страница'), el('small', 'site-url', site.url));
      info.append(el('small', '', site.origin?.startsWith('https:') ? (site.secureConnection ? 'HTTPS · защищённое соединение' : 'HTTPS · защита не подтверждена') : site.origin ? 'HTTP · незашифрованное соединение' : 'Настройки сайта недоступны'));
      head.append(identity, info); content.append(head);
      const read = row(site.readerActive ? 'Выйти из режима чтения' : 'Показать режим чтения', 'reader', async () => { await act(site.readerActive ? 'reader.exit' : 'reader.enter'); close(); });
      read.classList.add('site-reader-action'); read.dataset.readerAction = ''; read.disabled = !site.readerActive && !site.readerAvailable; content.append(read);
      if (read.disabled) content.append(el('small', 'site-hint', site.mainLoading ? 'Дождитесь загрузки страницы' : probing ? 'Проверяем статью…' : 'На этой странице статья не определена'));
      const find = row('Найти на странице · Ctrl+F', 'find', async () => { close(); await act('find'); }); find.disabled = !site.origin; content.append(find);
      const zoom = el('div', 'site-row site-zoom'); zoom.append(glyph('zoom'), el('span', 'site-row-label', 'Масштаб'));
      for (const [command, label, text] of [['out','Уменьшить масштаб','−'],['reset','Сбросить масштаб',`${site.zoom || 100}%`],['in','Увеличить масштаб','+']]) {
        const b = button(text, () => act('zoom', {command})); b.disabled = !site.origin; b.setAttribute('aria-label', label); zoom.append(b);
      }
      content.append(zoom);
      if (site.origin && site.rules) {
        content.append(divider(), row('Настройки сайта…', 'settings', () => navigateLevel('settings'), '', true));
        const blocking = site.rules.blocking, override = blocking.sites[site.domain], checked = override ?? blocking.enabled;
        content.append(toggle('Блокировка рекламы на этом сайте', Boolean(checked), checked => act('blocking', {value:checked ? 1 : 0}), 'shield'));
        const protection = site.adblock;
        content.append(el('small', 'site-hint site-blocking-hint', protection && !protection.ready ? 'Фильтры недоступны' : `${override === undefined ? 'Глобально' : 'Для сайта'} ${checked ? 'включена' : 'выключена'}${protection?.active ? ` · Заблокировано: ${protection.blockedRequests || 0}` : ''}`));
      }
    }
    if (focusedLabel) [...content.querySelectorAll('[aria-label]')].find(n => n.getAttribute('aria-label') === focusedLabel)?.focus();
  }
  function preferences(changes) {
    const snapshot = site;
    saving = saving.catch(() => {}).then(() => act('reader.preferences', {preferences:changes}, snapshot));
    return saving;
  }
  function renderReader() {
    const active = Boolean(site?.readerActive && site.article); reader.hidden = !active;
    document.body.dataset.reader = String(active);
    if (!active) { article.replaceChildren(); articleKey = ''; settings.hidden = true; style.setAttribute('aria-expanded', 'false'); return; }
    const prefs = site.preferences;
    reader.dataset.theme = prefs.theme; reader.dataset.font = prefs.font; reader.dataset.size = String(prefs.size);
    reader.dataset.width = String(prefs.width); reader.dataset.spacing = String(prefs.spacing); reader.dataset.images = String(prefs.images);
    const currentKey = `${site.tabId}|${site.url}|${site.generation}`;
    if (articleKey !== currentKey) {
      articleKey = currentKey; article.replaceChildren(); reader.scrollTop = 0;
      const data = site.article; article.append(el('h1', '', data.title));
      if (data.deck && !data.content.includes(data.deck)) article.append(el('p', 'reader-deck', data.deck));
      const metadata = [data.author, data.date].filter(Boolean).join(' · ');
      if (metadata) article.append(el('p', 'reader-meta', metadata));
      const body = el('div', 'reader-body'); body.append(safe.content(data.content, site.url)); article.append(body);
      const snapshot = site, images = [...body.querySelectorAll('img[data-reader-src]')].slice(0, 64);
      // Keep network activity in the source profile; deliver inert raster data
      // to the shell. Four concurrent requests, bounded by the native loader.
      let index = 0;
      async function loadImages() {
        while (index < images.length && articleKey === currentKey) {
          const image = images[index++];
          try { const result = await api.siteAction('reader.image', {...token(snapshot), target:image.dataset.readerSrc});
            if (image.isConnected && articleKey === currentKey && /^data:image\/(png|jpeg|webp|gif|avif);base64,/.test(result)) image.src = result;
          } catch { if (image.isConnected) image.alt = image.alt || 'Изображение недоступно'; }
        }
      }
      for (let i = 0; i < 4; i++) loadImages();
    }
    const signature = JSON.stringify(prefs);
    if (settings.childElementCount && preferencesSignature === signature) return;
    preferencesSignature = signature;
    const wasFocused = settings.contains(document.activeElement), label = document.activeElement?.getAttribute('aria-label');
    settings.replaceChildren(el('h2', 'reader-palette-title', 'Оформление · Aa'));
    const themes = el('div', 'reader-swatches'); themes.setAttribute('role', 'group'); themes.setAttribute('aria-label', 'Тема статьи');
    for (const [theme, label] of [['light','Светлая'],['sepia','Тёплая'],['gray','Серая'],['dark','Тёмная']]) {
      const b = button('', () => preferences({theme}), 'reader-swatch'); b.dataset.theme = theme;
      b.title = label; b.setAttribute('aria-label', label); b.setAttribute('aria-pressed', String(prefs.theme === theme)); themes.append(b);
    }
    settings.append(el('span', 'reader-palette-label', 'Тема'), themes, divider());
    settings.append(select('Шрифт', site.readerFonts?.map(f => [f.id, f.label]) || [['serif','Georgia'],['sans','Arial'],['system','Системный (Segoe UI)']], prefs.font, font => preferences({font})));
    const size = el('div', 'site-control reader-size'); size.append(el('span', '', 'Размер текста'));
    const controls = el('div', 'reader-segments');
    const minus = button('A−', () => preferences({size:Math.max(14, site.preferences.size - 2)})), plus = button('A+', () => preferences({size:Math.min(32, site.preferences.size + 2)}));
    minus.setAttribute('aria-label', 'Уменьшить размер текста'); plus.setAttribute('aria-label', 'Увеличить размер текста');
    minus.disabled = prefs.size <= 14; plus.disabled = prefs.size >= 32;
    controls.append(minus, el('output', '', String(prefs.size)), plus); size.append(controls); settings.append(size, divider());
    for (const [name, title, labels] of [['width','Ширина',['Узкая','Средняя','Широкая']],['spacing','Интервал',['Плотный','Обычный','Свободный']]]) {
      const group = el('div', 'reader-segments reader-layout'); group.setAttribute('role', 'group'); group.setAttribute('aria-label', title);
      for (let i = 0; i < 3; i++) {
        const b = button('', () => preferences({[name]:i}), 'reader-layout-option'); b.dataset[name] = i;
        b.setAttribute('aria-label', `${title}: ${labels[i]}`); b.title = labels[i]; b.setAttribute('aria-pressed', String(prefs[name] === i));
        const lines = el('span', 'reader-lines'); for (let j = 0; j < 3; j++) lines.append(el('i')); b.append(lines); group.append(b);
      }
      settings.append(el('span', 'reader-palette-label', title), group);
    }
    settings.append(divider(), toggle('Изображения', prefs.images, images => preferences({images})));
    if (wasFocused && label) [...settings.querySelectorAll('[aria-label]')].find(n => n.getAttribute('aria-label') === label)?.focus();
  }
  const prompt = el('section', 'soulu-permission-prompt'); prompt.hidden = true;
  prompt.setAttribute('role', 'dialog'); prompt.setAttribute('aria-label', 'Разрешение сайта'); document.body.append(prompt);
  async function respond(decision) {
    const id = promptId; if (!id) return;
    for (const b of prompt.querySelectorAll('button')) b.disabled = true;
    try { await api.respondPermission({id, decision}); }
    catch (e) { if (promptId === id) error(e); }
    finally { await renderPrompt(await api.getState()); }
  }
  async function renderPrompt(next) {
    const request = next.permissionPrompt;
    if (!request) { promptId = 0; prompt.hidden = true; await api.setPopover(false, 'permissions'); return; }
    const fresh = promptId !== request.id; promptId = request.id;
    if (fresh) {
      close(); settings.hidden = true; style.setAttribute('aria-expanded', 'false');
      const header = el('header', 'site-heading'); const identity = el('div');
      identity.append(el('strong', '', request.domain), el('small', '', request.origin));
      const dismiss = button('', () => respond('dismiss'), 'site-prompt-dismiss'); dismiss.setAttribute('aria-label', 'Закрыть запрос'); dismiss.append(glyph('close'));
      header.append(glyph(request.permissions[0]), identity, dismiss);
      const message = el('p', 'site-prompt-message', request.permissions.includes('popups')
        ? 'Разрешить всплывающие окна? После выбора повторите действие на сайте.'
        : `Запрашивает доступ: ${request.permissions.map(n => names[n]?.toLowerCase() || n).join(', ')}`);
      const actions = el('div', 'site-confirm-actions'); actions.append(button('Запретить', () => respond('block')), button('Разрешить', () => respond('allow'), 'site-primary'));
      prompt.replaceChildren(header, message, actions);
      await expandSurface('permissions'); if (promptId !== request.id) return;
      prompt.hidden = false; position(); prompt.querySelector('button')?.focus();
    }
    for (const b of prompt.querySelectorAll('button')) b.disabled = false;
  }
  function link(event, mode) {
    const a = event.target.closest('.reader-body a[href]'); if (!a) return;
    event.preventDefault(); const target = safe.webURL(a.getAttribute('href'), site.url); if (target) act('reader.link', {target, mode}).catch(error);
  }
  article.onclick = e => link(e, e.ctrlKey || e.metaKey ? (e.shiftKey ? 'new' : 'background') : 'current');
  article.onauxclick = e => { if (e.button === 1) link(e, 'background'); };
  article.oncontextmenu = e => {
    const a = e.target.closest('.reader-body a[href]'); if (!a) return;
    e.preventDefault(); closeLink(); const snapshot = site, target = safe.webURL(a.getAttribute('href'), snapshot.url);
    linkMenu = el('section', 'reader-link-menu');
    for (const [mode, text] of [['new','Открыть в новой вкладке'],['background','Открыть в фоновой вкладке'],['incognito','Открыть в инкогнито']]) linkMenu.append(button(text, () => { closeLink(); updateSurface(); return act('reader.link', {target, mode}, snapshot); }));
    linkMenu.style.left = `${Math.max(8, Math.min(e.clientX, innerWidth - 280))}px`; linkMenu.style.top = `${Math.min(e.clientY, innerHeight - 140)}px`;
    document.body.append(linkMenu); updateSurface(); linkMenu.querySelector('button')?.focus();
  };
  const findBox = el('section', 'site-find'), findInput = el('input'); findBox.hidden = true;
  findInput.setAttribute('aria-label', 'Найти на странице'); findInput.placeholder = 'Найти на странице';
  const closeFind = () => { findBox.hidden = true; api.find(''); updateSurface(); };
  const previous = button('↑', () => api.find(findInput.value, false)), next = button('↓', () => api.find(findInput.value));
  previous.setAttribute('aria-label', 'Предыдущее совпадение'); next.setAttribute('aria-label', 'Следующее совпадение');
  const dismiss = button('×', closeFind); dismiss.setAttribute('aria-label', 'Закрыть поиск');
  findBox.append(findInput, previous, next, dismiss); document.body.append(findBox);
  findInput.oninput = () => api.find(findInput.value); findInput.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); api.find(findInput.value, !e.shiftKey); } };
  api.onRequestFind(async () => { await expandSurface(); findBox.hidden = false; close(); position(); findInput.focus(); findInput.select(); });
  document.addEventListener('pointerdown', e => {
    if (!prompt.hidden && !prompt.contains(e.target)) respond('dismiss');
    if (linkMenu && !linkMenu.contains(e.target)) { closeLink(); updateSurface(); }
    if (!settings.hidden && !settings.contains(e.target) && e.target !== style) { settings.hidden = true; style.setAttribute('aria-expanded', 'false'); }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !prompt.hidden) { e.preventDefault(); respond('dismiss'); return; }
    if (e.key === 'Escape') { if (!menu.hidden) { e.preventDefault(); if (level === 'main') close(true); else navigateLevel(level === 'settings' ? 'main' : 'settings'); } else if (!findBox.hidden) closeFind(); else if (!settings.hidden) { settings.hidden = true; style.setAttribute('aria-expanded', 'false'); } else closeLink(); }
    if (e.key === 'Tab' && (!menu.hidden || !prompt.hidden || !settings.hidden)) {
      const surface = !prompt.hidden ? prompt : !menu.hidden ? menu : settings;
      const items = [...surface.querySelectorAll('button:not(:disabled),select,input')].filter(n => n.getClientRects().length);
      if (e.shiftKey && document.activeElement === items[0]) { e.preventDefault(); items.at(-1)?.focus(); }
      else if (!e.shiftKey && document.activeElement === items.at(-1)) { e.preventDefault(); items[0]?.focus(); }
    }
  });
  async function sync(next) {
    state = next; await renderPrompt(next); const readerTop = (state.settings?.layout === 'classic' ? 82 : 48) + (state.bookmarksBarVisible ? 28 : 0);
    reader.style.top = `${readerTop}px`; reader.style.setProperty('--reader-top', `${readerTop}px`);
    reader.style.left = state.bookmarksSidebarVisible ? '276px' : '0';
    const nextKey = `${state.activeTabId}|${state.page?.url || 'about:blank'}|${state.page?.generation}`;
    if (key !== nextKey) {
      // Applying this site's blocker reloads its resources. Keep the anchored
      // controls visible through that one reload; other navigation still closes.
      const keepMenu = !menu.hidden && reloadMenu?.tabId === state.activeTabId && reloadMenu.url === state.page?.url;
      reloadMenu = null; key = nextKey; ++revision; site = null; articleKey = ''; reader.hidden = true; closeFind();
      if (!keepMenu) close();
    }
    const request = revision; const result = await api.getCurrentSite();
    if (request !== revision) return; site = result; renderReader();
    if (!menu.hidden) { renderMenu(); position(); }
  }
  api.onState(next => sync(next).catch(error)); api.getState().then(sync).catch(error);
  window.addEventListener('resize', position);
})();
