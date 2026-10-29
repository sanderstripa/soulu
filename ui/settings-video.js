(()=>{
 'use strict';
 const call=payload=>new Promise((resolve,reject)=>window.cefQuery({request:JSON.stringify({action:'browser.video.settings',payload}),persistent:false,onSuccess:s=>resolve(JSON.parse(s)),onFailure:(_,s)=>reject(Error(s))}));
 const options=[
 ['responseLanguage','Язык озвучки','Voice-over language','select','ru',['ru','en','kk','uk','uz']],
 ['useLivelyVoice','Живые голоса','Lively voices','bool',false],
 ['autoTranslate','Переводить автоматически','Translate automatically','bool',false],
 ['autoPauseOnTranslate','Приостановить видео на время перевода','Pause while translating','bool',false],
 ['dontTranslateLanguages','Не переводить языки (через запятую)','Do not translate languages (comma separated)','list',['ru']],
 ['dontTranslateByYTMusic','Не переводить YouTube Music','Skip YouTube Music','bool',false],
 ['defaultVolume','Громкость перевода','Translation volume','number',100,[0,100]],
 ['enabledAutoVolume','Автогромкость оригинала','Automatic original volume','bool',true],
 ['autoVolume','Громкость оригинала','Original volume','number',15,[0,100]],
 ['enabledSmartDucking','Приглушать оригинал во время озвучки','Smart ducking','bool',true],
 ['smartDuckingStrength','Сила приглушения','Ducking strength','number',80,[0,100]],
 ['showVideoSlider','Ползунок оригинальной дорожки','Original audio slider','bool',true],
 ['audioBooster','Усиление звука','Audio booster','bool',false],
 ['syncVolume','Синхронизация громкости','Sync volume','bool',false],
 ['newAudioPlayer','Новый аудиоплеер','New audio player','bool',true],
 ['onlyBypassMediaCSP','Обход ограничений медиадорожки','Bypass media CSP','bool',true],
 ['downloadWithName','Имя видео при скачивании','Use video name for downloads','bool',true],
 ['useAudioDownload','Скачивать аудиодорожку','Download audio track','bool',true],
 ['sendNotifyOnComplete','Уведомление о готовом переводе','Notify when translation is ready','bool',false],
 ['translationService','Сервис перевода','Translation service','select','yandexbrowser',['yandexbrowser','msedge']],
 ['detectService','Определение языка','Language detection','select','yandexbrowser',['yandexbrowser','msedge','rust-server']],
 ['translateAPIErrors','Переводить сообщения об ошибках','Translate API errors','bool',true],
 ['sendErrorReports','Отправлять отчёты разработчикам VOT','Send error reports to VOT developers','bool',false],
 ['autoSubtitles','Автоматические субтитры','Automatic subtitles','bool',false],
 ['responseLanguageSubtitles','Язык субтитров','Subtitle language','select','auto',['auto','original','ru','en','kk','uk','uz']],
 ['subtitlesTranslationLanguage','Язык перевода субтитров','Subtitle translation language','select','auto',['auto','ru','en','kk','uk','uz']],
 ['highlightWords','Подсвечивать слова','Highlight words','bool',false],
 ['subtitlesSmartLayout','Умная компоновка субтитров','Smart subtitle layout','bool',true],
 ['subtitlesDownloadFormat','Формат субтитров','Subtitle download format','select','srt',['srt','vtt','json']],
 ['subtitlesFontFamily','Шрифт субтитров','Subtitle font family','text','default-sans'],
 ['subtitlesMaxLength','Длина субтитров','Subtitle maximum length','number',300,[30,2000]],
 ['subtitlesFontSize','Размер субтитров','Subtitle font size','number',20,[10,60]],
 ['subtitlesOpacity','Непрозрачность фона субтитров','Subtitle background opacity','number',20,[0,100]],
 ['showPiPButton','Кнопка «картинка в картинке» на видео','Picture-in-picture button on video','bool',false],
 ['autoHideButtonDelay','Задержка скрытия кнопки, мс','Button hide delay, ms','number',1000,[100,3000]],
 ['buttonPos','Положение кнопки на видео','Video button position','select','default',['default','left','right','leftCenter','rightCenter']],
 ['translationHotkey','Горячая клавиша перевода','Translation hotkey','hotkey',null],
 ['subtitlesHotkey','Горячая клавиша субтитров','Subtitle hotkey','hotkey',null],
 ['pipHotkey','Горячая клавиша PiP','PiP hotkey','hotkey',null],
 ['translateProxyEnabled','Прокси перевода (0 — авто, 1 — вкл., 2 — выкл.)','Translation proxy (0 auto, 1 on, 2 off)','select',0,[0,1,2]],
 ['translateProxyEnabledDefault','Прокси включён по умолчанию','Proxy enabled by default','bool',false],
 ['proxyWorkerHost','Сервер прокси VOT','VOT proxy host','text','vot-worker.eu.cc'],
 ['mediaProxyHost','Сервер медиапрокси','Media proxy host','text','media-proxy.toil.cc'],
 ['m3u8ProxyHost','Прокси M3U8','M3U8 proxy','text','media-proxy.toil.cc/v1/proxy/m3u8'],
 ['localeLangOverride','Язык интерфейса VOT','VOT interface language','select','ru',['ru','en']]
 ];
 window.souluVideoSettings={open:async()=>{
  const {t,el,button,dialog}=window.souluSettings;let values=await call(null),queue=Promise.resolve();
  dialog('Video Translate · VOT 1.12.3',box=>{
   box.append(el('p',t('Перевод выполняет сервис VOT/Яндекс: ему передаются адрес видео и необходимые данные для перевода. Дорожка появляется поверх видео; отдельной кнопки на панели браузера нет. Изменения сохраняются в текущем профиле.','VOT/Yandex receives the video URL and data required for translation. Controls appear on the video. Changes are saved in the current profile.'),'note'));
   const message=el('p','','note');message.setAttribute('role','status');box.append(message);
   const save=(key,value)=>{queue=queue.then(()=>call({values:{[key]:value}})).then(next=>{values=next;message.textContent=t('Сохранено','Saved')}).catch(e=>{message.textContent=e.message});return queue;};
   for(const [key,ru,en,type,fallback,choices] of options){
    const row=el('label',undefined,'row'),label=el('span',t(ru,en));let control;
    const value=values[key]??fallback;
    if(type==='select'){control=el('select');for(const v of choices)control.append(new Option(String(v),String(v)));control.value=String(value);control.onchange=()=>save(key,typeof fallback==='number'?Number(control.value):control.value);}
    else if(type==='hotkey'){control=button(value||t('Не задана — нажмите','Unset — click'),()=>{control.textContent=t('Нажмите сочетание; Esc — очистить','Press a shortcut; Esc to clear');control.onkeydown=e=>{e.preventDefault();e.stopPropagation();const v=e.key==='Escape'?null:[e.ctrlKey?'Control':null,e.altKey?'Alt':null,e.shiftKey?'Shift':null,e.metaKey?'Meta':null,e.code.replace('Key','').replace('Digit','')].filter(Boolean).join('+');if(['Control','Alt','Shift','Meta'].includes(e.key))return;save(key,v);control.textContent=v||t('Не задана','Unset');control.onkeydown=null;};});}
    else{control=el('input');control.type=type==='bool'?'checkbox':type==='number'?'number':'text';if(type==='bool'){control.checked=value;control.setAttribute('role','switch');}else control.value=type==='list'?value.join(', '):value;if(type==='number'){control.min=choices[0];control.max=choices[1];}control.onchange=()=>{if(!control.reportValidity())return;save(key,type==='bool'?control.checked:type==='number'?Number(control.value):type==='list'?control.value.split(',').map(v=>v.trim()).filter(Boolean):control.value.trim());};}
    control.setAttribute('aria-label',t(ru,en));row.append(label,control);box.append(row);
   }
   const account=el('p',values.account?.username?t('Аккаунт Яндекс: ','Yandex account: ')+values.account.username:t('Аккаунт Яндекс не подключён. Обычный перевод работает без входа; вход доступен ниже.','Yandex account is not connected. Regular translation works without signing in; sign-in is available below.'),'note');
   box.append(account,button(t('Войти в Яндекс для VOT','Sign in to Yandex for VOT'),async()=>{await window.souluSettings.flush();const response=await call({operation:'authStart'});await window.browserShell.openTab(response.url);window.souluSettingsRequestClose();}),button(t('Выйти из аккаунта VOT','Sign out of VOT'),async()=>{await save('account',null);account.textContent=t('Аккаунт отключён','Account disconnected')}));
   const upstream=el('a','VOT · MIT · ilyhalight/voice-over-translation');upstream.href='https://github.com/ilyhalight/voice-over-translation';upstream.onclick=e=>{e.preventDefault();window.browserShell.openTab(upstream.href)};box.append(upstream);
  });
 }};
})();
