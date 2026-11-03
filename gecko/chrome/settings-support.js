// Preserve every original section; never present unported optional controls as working.
(()=>{
 const unavailable={reading:'Параметры режима чтения сохраняются; сам режим чтения будет подключён позднее.',extensions:'Используйте расширения Firefox. Установка Chrome CRX не поддерживается.'};
 const observer=new MutationObserver(()=>{const title=document.getElementById('settingsTitle')?.textContent||'';const id=/Режим чтения|Reader mode/.test(title)?'reading':/Расширения|Extensions/.test(title)?'extensions':'';if(!id)return;const box=document.getElementById('sectionContent');if(!box||box.querySelector('[data-gecko-note]'))return;const note=document.createElement('p');note.dataset.geckoNote='true';note.className='note';note.textContent=unavailable[id];box.prepend(note);if(id!=='extensions')for(const input of box.querySelectorAll('input,select,button,textarea'))input.disabled=true;if(id==='extensions'){const button=document.createElement('button');button.textContent='Управление расширениями Firefox';button.onclick=()=>browserShell.openTab('about:addons');note.append(document.createElement('br'),button);}});
 observer.observe(document.getElementById('sectionContent'),{childList:true});
})();
(()=>{
 const annotate=()=>{
  const box=document.getElementById('sectionContent');if(!box)return;
  const unsupported=['freezeBackgroundTabs','backgroundTabTimeout','memorySaver','performanceExclusions'];
  for(const id of unsupported){const input=document.getElementById(id);if(input)input.disabled=true;}
  const mode=document.getElementById('performanceMode');if(mode){const eco=mode.querySelector('option[value=eco]');if(eco)eco.disabled=true;if(!box.querySelector('[data-gecko-performance]')){const note=document.createElement('p');note.className='note';note.dataset.geckoPerformance='true';note.textContent='В этой сборке работают штатные механизмы Gecko. CEF-приостановка вкладок и отдельный режим экономии пока недоступны.';box.append(note);}}
  const video=document.getElementById('videoTranslationEnabled');if(video){video.disabled=true;video.checked=false;video.title='Озвучка YouTube пока не перенесена. Перевод страниц работает через локальный движок Gecko.';}
  const downloads=document.getElementById('permissions-downloads');if(downloads){downloads.disabled=true;downloads.title='Автоматические загрузки пока контролируются штатной защитой Firefox.';}
 };
 new MutationObserver(annotate).observe(document.getElementById('sectionContent'),{childList:true});document.addEventListener('change',()=>setTimeout(annotate,0),true);
 const open=()=>{if(window.souluBrowserImport)window.souluBrowserImport.open=()=>browserShell.browserImport('native');};open();
})();
