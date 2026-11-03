/* Existing Soulu translation styling; Gecko owns model download and isolated DOM translation. */
(()=>{
 const api=window.browserShell;if(!api)return;
 const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 let state={},snapshot=null,serial=0,timer=0;
 const panel=el('section');panel.className='soulu-translation';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Soulu Translate');document.body.append(panel);
 const close=()=>{panel.hidden=true;clearTimeout(timer);api.setPopover(false,'translation');api.setSuggestionsHeight(0);};
 const button=(label,handler)=>{const b=el('button',label);b.type='button';b.onclick=handler;return b;};
 async function open(){
  snapshot=await api.getCurrentSite();const ticket=++serial;panel.replaceChildren(el('h2','Soulu Translate'));
  const from=el('select'),to=el('select');from.id='gecko-translation-from';to.id='gecko-translation-to';
  for(const [id,title] of [['en','Английский'],['ru','Русский'],['de','Немецкий'],['fr','Французский'],['es','Испанский'],['it','Итальянский'],['zh','Китайский']])from.append(new Option(title,id));
  to.append(new Option('Русский','ru'),new Option('English','en'));to.value=state.settings.translationTarget||'ru';
  const status=el('p','Определение языка страницы…');status.setAttribute('role','status');status.id='gecko-translation-status';
  const sourceLabel=el('label','Язык страницы'),targetLabel=el('label','Язык перевода');sourceLabel.append(from);targetLabel.append(to);
  const translate=button('Перевести',async()=>{translate.disabled=true;status.textContent='Загрузка языковой модели и перевод…';try{await api.translation('translate',{...snapshot,from:from.value,to:to.value});const until=Date.now()+180000;const poll=async()=>{if(panel.hidden||ticket!==serial)return;try{const result=await api.translation('status',snapshot);if(result.error)throw Error(result.error);if(result.visible){status.textContent='Страница переведена';translate.disabled=false;return;}if(Date.now()>until)throw Error('Модель не загрузилась. Проверьте подключение и повторите.');timer=setTimeout(poll,800);}catch(e){status.textContent=e.message;translate.disabled=false;}};poll();}catch(e){status.textContent=e.message;translate.disabled=false;}});translate.id='gecko-translation-run';
  const restore=button('Показать оригинал',async()=>{await api.translation('restore',snapshot);close();});restore.id='gecko-translation-restore';
  const actions=el('div');actions.className='soulu-translation-actions';actions.append(translate,restore,button('Закрыть',close));panel.append(sourceLabel,targetLabel,el('p','Локальный перевод. Модели Mozilla загружаются один раз.'),status,actions);panel.hidden=false;api.setPopover(true,'translation');api.setSuggestionsHeight(innerHeight);
  const icon=document.querySelector('.soulu-translate-button');panel.style.top=((icon?.getBoundingClientRect().bottom||50)+8)+'px';
  try{const result=await api.translation('probe',snapshot);if(ticket!==serial)return;from.value=String(result.lang).split('-')[0]||'en';status.textContent=result.visible?'Страница переведена':'';}catch(e){status.textContent=e.message;}
 }
 function update(s){const old=state.page;state=s;if(old?.url!==s.page?.url||old?.id!==s.page?.id)close();document.querySelectorAll('.soulu-translate-button').forEach(n=>{if(!n.closest(state.settings.layout==='compact'?'.compact-active-tab':'.classic-address-pill'))n.remove();});if(!/^https?:/.test(s.page?.url||''))return;const host=document.querySelector(state.settings.layout==='compact'?'.compact-active-tab':'.classic-address-pill');if(!host||host.querySelector('.soulu-translate-button'))return;const icon=button('',()=>open().catch(console.error));icon.className='soulu-translate-button';icon.title='Soulu Translate';icon.setAttribute('aria-label',icon.title);icon.innerHTML='<svg viewBox="0 0 24 24"><path d="M3 5h12M9 2v3M5 5c1 6 4 9 9 12M13 5c-1 6-4 9-10 12M13 22l5-12 5 12M15 18h6"/></svg>';host.append(icon);}
 api.onState(update);api.getState().then(update);document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});document.addEventListener('pointerdown',e=>{if(!panel.hidden&&!panel.contains(e.target)&&!e.target.closest('.soulu-translate-button'))close();});
})();
