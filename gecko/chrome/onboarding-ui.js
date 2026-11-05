/* Adapt the original CEF welcome composition; no browser engine in this page. */
(()=>{
const $=id=>document.getElementById(id),call=(action,payload)=>new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'onboarding.'+action,payload}),onSuccess:s=>resolve(JSON.parse(s)),onFailure:(_,e)=>reject(Error(e))}));
let data;const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
function button(label,fn,primary=false){const n=el('button',label);n.type='button';if(primary)n.className='primary';n.onclick=async()=>{n.disabled=true;try{await fn();}catch(e){$('message').textContent=e.message;}finally{n.disabled=false;}};return n;}
async function patch(p){data=await call('progress',p);render();}
function select(label,key,values){const row=el('label',label),n=el('select');for(const [value,title] of values)n.append(new Option(title,value));n.value=data.settings[key];n.onchange=()=>patch({[key]:n.value});row.append(n);$('controls').append(row);}
function toggle(label,key,value){const row=el('label',label),n=el('input');n.type='checkbox';n.checked=value;n.onchange=()=>patch({[key]:n.checked});row.append(n);$('controls').append(row);}
function render(){const en=data.settings.language==='en',step=data.flow.step||1,t=(ru,english)=>en?english:ru;
 document.documentElement.lang=en?'en':'ru';document.body.dataset.theme=data.settings.theme==='system'?(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'):data.settings.theme;$('counter').textContent=t(`${step} из 6`,`${step} of 6`);$('controls').replaceChildren();$('actions').replaceChildren();$('message').textContent='';$('art').replaceChildren();const image=el('img');image.src='branding/soulu-512.png';image.className='hero-logo';image.alt='';$('art').append(image);
 const titles=[t('Добро пожаловать в Soulu','Welcome to Soulu'),t('Импортировать данные','Import your data'),t('Оформление','Appearance'),t('Приватность и защита','Privacy and protection'),t('Встроенный VPN','Built-in VPN'),t('Всё готово','Ready to browse')];$('title').textContent=titles[step-1];$('description').textContent=t('Параметры можно изменить позже в настройках.','You can change these choices later in Settings.');
 if(step===1)select(t('Язык интерфейса','Interface language'),'language',[['ru','Русский'],['en','English']]);
 if(step===2)$('controls').append(button(t('Импортировать из браузера…','Import from a browser…'),()=>window.souluOpenImport()),el('p',t('Мастер Gecko перенесёт доступные закладки, историю и пароли. Защита исходного браузера сохраняется.','Gecko imports available bookmarks, history and passwords while respecting source-browser protections.')));
 if(step===3)select(t('Тема','Theme'),'theme',[['system',t('Системная','System')],['light',t('Светлая','Light')],['dark',t('Тёмная','Dark')]]);
 if(step===4){toggle('Разрешить местоположение для погоды','weatherLocation',data.rules.sites['soulu://home']?.geolocation===0);toggle(t('Блокировать рекламу','Block ads'),'adblock',data.rules.blocking.enabled);toggle(t('Спрашивать разрешения сайтов','Ask for site permissions'),'askPermissions',['camera','microphone','geolocation','notifications'].every(k=>data.rules.defaults[k]===1));}
 if(step===5){const name=el('input'),key=el('textarea'),note=el('p');name.placeholder='Название VPN';key.placeholder='vless://… или sudoku://…';name.id='welcomeVpnName';key.id='welcomeVpnKey';$('controls').append(name,key,button(t('Добавить ключ','Add key'),async()=>{await call('vpn',{name:name.value,link:key.value});key.value='';note.textContent='Ключ сохранён — OK';}),note);}
 if(step===5)$('controls').append(el('p',t('VPN необязателен. Системный прокси Windows не изменяется.','VPN is optional. Windows system proxy is unchanged.')));
 if(step===6)$('controls').append(button(t('Сделать Soulu браузером по умолчанию','Make Soulu the default browser'),()=>call('default')));
 if(step>1)$('actions').append(button(t('Назад','Back'),()=>patch({step:step-1})));
 $('actions').append(button(t('Не сейчас','Skip'),()=>call('finish',{skip:true})),button(step===6?t('Открыть Soulu','Start browsing'):t('Далее','Next'),()=>step===6?call('finish',{skip:false}):patch({step:step+1}),true));
 document.querySelector('main').setAttribute('aria-busy','false');
}
call('get').then(s=>{data=s;render();}).catch(e=>$('message').textContent=e.message);
})();

