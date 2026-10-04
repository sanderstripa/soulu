(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const invoke = (action, payload = null) => new Promise((resolve, reject) => window.cefQuery({
    request: JSON.stringify({action, payload}), persistent: false,
    onSuccess: value => resolve(value ? JSON.parse(value) : null),
    onFailure: (_, message) => reject(new Error(message))
  }));

  let state = {}, editIndex = -1, revision = 0, selectedEngine = 'google';
  let recognition = null, weatherRequest = 0;
  const weatherCache = new Map();
  const el = (tag, text) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; return node; };
  const report = error => { $('error').textContent = error?.message || String(error || ''); };
  const set = async patch => { const next = await invoke('home.set', patch); apply(next); };
  const english = () => state.language === 'en';

  const labels = {
    homeShowLogo: 'Soulu', homeShowSearch: 'Поиск / Search', homeShowShortcuts: 'Избранное / Favorites',
    homeShowWeather: 'Погода / Weather', homeShowBackground: 'Мягкий фон / Soft background'
  };
  for (const [key, label] of Object.entries(labels)) {
    const row = el('label', label); row.className = 'toggle';
    const input = el('input'); input.type = 'checkbox'; input.dataset.key = key;
    input.onchange = () => set({[key]: input.checked}).catch(report);
    row.append(input); $('toggles').append(row);
  }

  function closePopovers(except = '') {
    for (const [panel, toggle] of [['engineMenu','engineToggle'],['weatherDetail','weatherToggle'],['launcherPanel','launcherToggle']]) {
      if (panel === except) continue;
      $(panel).hidden = true; $(toggle).setAttribute('aria-expanded', 'false');
    }
  }

  function setEngine(engine) {
    selectedEngine = engine === 'perplexity' ? 'perplexity' : 'google';
    const isPerplexity = selectedEngine === 'perplexity';
    $('engineLabel').textContent = isPerplexity ? 'Perplexity' : 'Google';
    $('engineIcon').className = 'engine-icon ' + (isPerplexity ? 'perplexity-mark' : 'google-mark');
    if (isPerplexity) {
      $('engineIcon').textContent = '';
      const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
      svg.setAttribute('viewBox','0 0 24 24');
      svg.innerHTML = '<path d="M7 3v18M17 3v18M3 8h18M3 16h18M7 3l10 5-10 8 10 5M17 3 7 8l10 8-10 5"/>';
      $('engineIcon').append(svg);
    } else {
      $('engineIcon').textContent = 'G';
    }
    for (const option of document.querySelectorAll('.engine-option')) {
      const active = option.dataset.engine === selectedEngine;
      option.classList.toggle('selected', active);
      option.setAttribute('aria-selected', String(active));
      option.querySelector('.engine-check').textContent = active ? '✓' : '';
    }
  }

  function toggleEngineMenu() {
    const opening = $('engineMenu').hidden;
    closePopovers(opening ? 'engineMenu' : '');
    $('engineMenu').hidden = !opening;
    $('engineToggle').setAttribute('aria-expanded', String(opening));
    if (opening) document.querySelector('.engine-option.selected')?.focus();
  }
  $('engineToggle').onclick = toggleEngineMenu;
  $('engineToggle').onkeydown = event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); toggleEngineMenu(); }
  };
  for (const option of document.querySelectorAll('.engine-option')) option.onclick = () => {
    setEngine(option.dataset.engine); closePopovers(); $('query').focus();
  };

  function likelyAddress(value) {
    return /^https?:\/\//i.test(value) || /^localhost(?::\d+)?(?:\/|$)/i.test(value) ||
      (!/\s/.test(value) && /^[^./\s]+(?:\.[^./\s]+)+(?:[/:?#].*)?$/.test(value));
  }
  $('search').onsubmit = event => {
    event.preventDefault();
    const value = $('query').value.trim(); if (!value) return;
    let target = value;
    if (!likelyAddress(value)) {
      const query = encodeURIComponent(value);
      target = selectedEngine === 'perplexity'
        ? 'https://www.perplexity.ai/?q=' + query
        : 'https://www.google.com/search?q=' + query;
    }
    invoke('home.navigate', target).catch(report);
  };

  function startVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { report(new Error(english() ? 'Voice input is unavailable in this build.' : 'Голосовой ввод недоступен в этой сборке.')); return; }
    if (recognition) { try { recognition.stop(); } catch {} return; }
    recognition = new SpeechRecognition(); recognition.lang = english() ? 'en-US' : 'ru-RU'; recognition.interimResults = false; recognition.maxAlternatives = 1;
    $('voice').classList.add('listening'); $('voice').setAttribute('aria-pressed','true');
    recognition.onresult = event => { const text = event.results?.[0]?.[0]?.transcript?.trim(); if (text) { $('query').value = text; $('query').focus(); } };
    recognition.onerror = event => report(new Error(english() ? 'Voice input failed.' : 'Не удалось распознать голос.'));
    recognition.onend = () => { recognition = null; $('voice').classList.remove('listening'); $('voice').removeAttribute('aria-pressed'); };
    try { recognition.start(); } catch (error) { recognition = null; $('voice').classList.remove('listening'); report(error); }
  }
  $('voice').onclick = startVoice;

  function openEditor(index) {
    editIndex = index; const row = (state.homeShortcuts || [])[index];
    $('shortcutName').value = row?.name || ''; $('shortcutUrl').value = row?.url || '';
    $('editorError').textContent = ''; $('editor').showModal(); $('shortcutName').focus();
  }
  function tool(text, label, fn) {
    const button = el('button', text); button.type = 'button'; button.setAttribute('aria-label', label);
    button.onclick = () => Promise.resolve(fn()).catch(report); return button;
  }
  function drawShortcuts() {
    $('links').replaceChildren();
    const rows = Array.isArray(state.homeShortcuts) ? state.homeShortcuts : [];
    rows.slice(0,12).forEach((row,index) => {
      let url; try { url = new URL(row.url); if (!['http:','https:'].includes(url.protocol)) return; } catch { return; }
      const tile = el('div'); tile.className = 'shortcut';
      const a = el('a'); a.href = url.href; a.title = row.name + ' · ' + url.href;
      const icon = el('img'); icon.className = 'favicon'; icon.alt = ''; icon.referrerPolicy = 'no-referrer';
      const initial = el('span', (url.hostname[0] || 'S').toUpperCase()); initial.className = 'shortcut-initial';
      icon.onerror = () => { icon.onerror = null; if (icon.isConnected) icon.replaceWith(initial); };
      icon.src = url.origin + '/favicon.ico';
      const label = el('span', row.name); label.className = 'shortcut-label';
      a.append(icon, label);
      a.onclick = event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.button !== 0) return;
        event.preventDefault(); invoke('home.navigate', url.href).catch(report);
      };
      const tools = el('div'); tools.className = 'shortcut-tools';
      tools.append(
        tool('✎','Изменить / Edit',()=>openEditor(index)),
        tool('×','Удалить / Delete',()=>set({homeShortcuts:rows.filter((_,i)=>i!==index)}))
      );
      const move = tool('←','Переместить влево / Move left',()=>{
        if (index === 0) return; const next = rows.map(x=>({...x}));
        [next[index-1],next[index]] = [next[index],next[index-1]]; return set({homeShortcuts:next});
      }); move.disabled = index === 0; tools.append(move);
      tile.append(a, tools); $('links').append(tile);
    });
    $('shortcutsEmpty').hidden = rows.length > 0;
    $('add').disabled = rows.length >= 12;
  }

  const weatherText = (code, en = false) => {
    const table = [
      [[0],['Ясно','Clear']],[[1,2],['Переменная облачность','Partly cloudy']],[[3],['Облачно','Cloudy']],
      [[45,48],['Туман','Fog']],[[51,53,55,56,57],['Морось','Drizzle']],[[61,63,65,66,67,80,81,82],['Дождь','Rain']],
      [[71,73,75,77,85,86],['Снег','Snow']],[[95,96,99],['Гроза','Thunderstorm']]
    ];
    for (const [codes,names] of table) if (codes.includes(Number(code))) return names[en ? 1 : 0];
    return en ? 'Weather' : 'Погода';
  };
  const weatherIcon = code => {
    code = Number(code); if (code === 0) return '☀'; if ([1,2].includes(code)) return '⛅'; if ([3,45,48].includes(code)) return '☁';
    if ([71,73,75,77,85,86].includes(code)) return '❄'; if ([95,96,99].includes(code)) return '⛈'; return '🌧';
  };
  const degree = value => Number.isFinite(Number(value)) ? Math.round(Number(value)) + '°' : '—';
  const weekday = iso => new Intl.DateTimeFormat(english() ? 'en-US' : 'ru-RU',{weekday:'short'}).format(new Date(iso));
  const hour = iso => new Intl.DateTimeFormat(english() ? 'en-US' : 'ru-RU',{hour:'2-digit',minute:'2-digit'}).format(new Date(iso));

  function weatherCell(title, icon, value) {
    const cell = el('div'); cell.className = 'weather-cell';
    cell.append(el('b', title), el('span', icon), el('span', value)); return cell;
  }
  function renderWeather(city, geo, data) {
    const current = data.current || {}, code = current.weather_code, icon = weatherIcon(code), name = geo.name || city;
    $('weatherIcon').textContent = icon; $('weatherTemp').textContent = degree(current.temperature_2m); $('weatherCity').textContent = name;
    $('weatherDetailIcon').textContent = icon; $('weatherDetailTemp').textContent = degree(current.temperature_2m);
    $('weatherCondition').textContent = weatherText(code, english()); $('weatherDetailCity').textContent = name;
    $('weatherMeta').textContent = (english() ? 'Feels like ' : 'Ощущается как ') + degree(current.apparent_temperature) +
      ' · ' + (english() ? 'Wind ' : 'Ветер ') + Math.round(Number(current.wind_speed_10m || 0)) + ' ' + (data.current_units?.wind_speed_10m || 'km/h') +
      ' · ' + (english() ? 'Humidity ' : 'Влажность ') + Math.round(Number(current.relative_humidity_2m || 0)) + '%';
    $('weatherMessage').textContent = '';
    $('weatherHourly').replaceChildren();
    const times = data.hourly?.time || [], temps = data.hourly?.temperature_2m || [], codes = data.hourly?.weather_code || [];
    const now = Date.now(); let start = times.findIndex(value => new Date(value).getTime() >= now - 30*60*1000); if (start < 0) start = 0;
    for (let i=start;i<Math.min(start+6,times.length);i++) $('weatherHourly').append(weatherCell(hour(times[i]),weatherIcon(codes[i]),degree(temps[i])));
    $('weatherDaily').replaceChildren();
    const days = data.daily?.time || [], max = data.daily?.temperature_2m_max || [], min = data.daily?.temperature_2m_min || [], dailyCodes = data.daily?.weather_code || [];
    for (let i=0;i<Math.min(7,days.length);i++) $('weatherDaily').append(weatherCell(weekday(days[i]),weatherIcon(dailyCodes[i]),degree(max[i])+' / '+degree(min[i])));
  }
  async function loadWeather(city, token) {
    const normalized = city.trim();
    if (!normalized) {
      $('weatherIcon').textContent = '☁'; $('weatherTemp').textContent = ''; $('weatherCity').textContent = english() ? 'Weather' : 'Погода';
      $('weatherDetailCity').textContent = english() ? 'Choose a city' : 'Выберите город'; $('weatherDetailTemp').textContent = '—';
      $('weatherCondition').textContent = english() ? 'Weather' : 'Погода'; $('weatherMeta').textContent = '';
      $('weatherMessage').textContent = english() ? 'Enter a city to show the live forecast.' : 'Укажите город, чтобы показать актуальный прогноз.';
      $('weatherHourly').replaceChildren(); $('weatherDaily').replaceChildren(); return;
    }
    const cached = weatherCache.get(normalized.toLowerCase());
    if (cached && Date.now() - cached.at < 10*60*1000) { if (token === weatherRequest) renderWeather(normalized,cached.geo,cached.data); return; }
    $('weatherCity').textContent = normalized; $('weatherDetailCity').textContent = normalized;
    $('weatherMessage').textContent = english() ? 'Updating…' : 'Обновляем…';
    try {
      const lang = english() ? 'en' : 'ru';
      const geoResponse = await fetch('https://geocoding-api.open-meteo.com/v1/search?count=1&format=json&language='+lang+'&name='+encodeURIComponent(normalized),{cache:'no-store'});
      if (!geoResponse.ok) throw new Error('geocoding');
      const geoJson = await geoResponse.json(), geo = geoJson.results?.[0]; if (!geo) throw new Error('city-not-found');
      const params = new URLSearchParams({
        latitude:String(geo.latitude),longitude:String(geo.longitude),timezone:'auto',forecast_days:'7',
        current:'temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m',
        hourly:'temperature_2m,weather_code',daily:'weather_code,temperature_2m_max,temperature_2m_min'
      });
      const forecastResponse = await fetch('https://api.open-meteo.com/v1/forecast?'+params.toString(),{cache:'no-store'});
      if (!forecastResponse.ok) throw new Error('forecast');
      const data = await forecastResponse.json(); weatherCache.set(normalized.toLowerCase(),{at:Date.now(),geo,data});
      if (token === weatherRequest) renderWeather(normalized,geo,data);
    } catch (error) {
      if (token !== weatherRequest) return;
      $('weatherTemp').textContent = ''; $('weatherIcon').textContent = '☁';
      $('weatherMessage').textContent = error.message === 'city-not-found'
        ? (english() ? 'City not found.' : 'Город не найден.')
        : (english() ? 'Weather is temporarily unavailable.' : 'Погода временно недоступна.');
    }
  }
  function refreshWeather(force = false) {
    if (!state.homeShowWeather) return; const city = state.homeWeatherCity || '';
    if (force) weatherCache.delete(city.toLowerCase());
    const token = ++weatherRequest; loadWeather(city,token);
  }

  function apply(next) {
    state = next; revision++;
    document.documentElement.lang = english() ? 'en' : 'ru';
    document.body.dataset.theme = state.resolvedTheme || state.theme || 'system';
    document.body.dataset.background = String(state.homeShowBackground !== false);
    $('logo').hidden = state.homeShowLogo === false; $('search').hidden = state.homeShowSearch === false;
    $('shortcuts').hidden = state.homeShowShortcuts === false; $('weather').hidden = state.homeShowWeather === false;
    $('query').placeholder = english() ? 'Enter a search query or URL' : 'Введите поисковый запрос или URL';
    $('shortcutsEmpty').textContent = english() ? 'Add favorite sites in Soulu settings.' : 'Добавьте избранные сайты в настройках Soulu.';
    $('city').placeholder = english() ? 'City' : 'Город'; $('saveCity').textContent = english() ? 'Save' : 'Сохранить';
    $('weatherToggle').setAttribute('aria-label', english() ? 'Weather' : 'Погода');
    $('launcherToggle').setAttribute('aria-label', english() ? 'Favorite sites' : 'Избранные сайты');
    for (const input of document.querySelectorAll('[data-key]')) input.checked = state[input.dataset.key] !== false;
    if (document.activeElement !== $('city')) $('city').value = state.homeWeatherCity || '';
    drawShortcuts(); refreshWeather();
  }
  window.souluHomeApply = apply;

  $('launcherToggle').onclick = () => {
    const opening = $('launcherPanel').hidden; closePopovers(opening ? 'launcherPanel' : '');
    $('launcherPanel').hidden = !opening; $('launcherToggle').setAttribute('aria-expanded',String(opening));
  };
  $('weatherToggle').onclick = () => {
    const opening = $('weatherDetail').hidden; closePopovers(opening ? 'weatherDetail' : '');
    $('weatherDetail').hidden = !opening; $('weatherToggle').setAttribute('aria-expanded',String(opening));
    if (opening) refreshWeather();
  };
  $('saveCity').onclick = () => set({homeWeatherCity:$('city').value.trim()}).catch(report);
  $('city').onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); $('saveCity').click(); } };
  document.addEventListener('pointerdown', event => {
    if (!event.target.closest('#searchWrap') && !event.target.closest('#utilities')) closePopovers();
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closePopovers(); });

  $('add').onclick = () => openEditor(-1); $('cancel').onclick = () => $('editor').close();
  $('shortcutForm').onsubmit = async event => {
    event.preventDefault(); const rows = (state.homeShortcuts || []).map(x=>({...x}));
    const row = {name:$('shortcutName').value.trim(),url:$('shortcutUrl').value.trim()};
    if (editIndex < 0) rows.push(row); else rows[editIndex] = row;
    try { await set({homeShortcuts:rows}); $('editor').close(); } catch (error) { $('editorError').textContent = error.message; }
  };
  $('customize').onclick = () => $('preferences').showModal();

  setEngine('google');
  invoke('home.get').then(apply).catch(report);
  setInterval(() => { if (!document.hidden) refreshWeather(true); }, 15*60*1000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshWeather(); });
})();
