(()=>{
 window.souluWeatherKey={open:async()=>{
  const ui=window.souluSettings,{t,el,button,dialog}=ui;const status=await ui.invoke('weather.key');
  dialog(t('Яндекс Погода','Yandex Weather'),box=>{
   box.append(el('p',t('Официальный API Яндекс Погоды требует ключ. Он хранится зашифрованным в этом профиле и не передаётся веб-страницам.','The official Yandex Weather API requires a key. It is encrypted in this profile and is not exposed to webpages.'),'note'));
   const label=el('label',undefined,'field'),input=el('input');label.append(el('span',t('Ключ API','API key')),input);input.type='password';input.autocomplete='new-password';input.placeholder=status.configured?t('Ключ уже сохранён','A key is already saved'):t('Вставьте ключ','Paste a key');box.append(label);
   const help=el('a',t('Получить ключ на портале Яндекс Погоды','Get a key on the Yandex Weather portal'));help.href='https://yandex.ru/dev/weather/';help.target='_blank';help.rel='noopener';box.append(help);
   const message=el('p','','note'),actions=el('div',undefined,'dialog-actions');
   actions.append(button(t('Сохранить','Save'),async()=>{try{if(!input.value.trim())throw Error(t('Вставьте ключ.','Paste a key.'));await ui.invoke('weather.key',{key:input.value.trim()});input.value='';message.textContent=t('Ключ сохранён. Выберите Яндекс Погоду в списке источников.','Key saved. Select Yandex Weather in the provider list.');}catch(e){message.textContent=e.message}}),button(t('Удалить ключ','Remove key'),async()=>{try{await ui.invoke('weather.key',{key:''});input.value='';input.placeholder=t('Ключ удалён','Key removed');message.textContent=t('Ключ удалён. Open-Meteo продолжает работать без ключа.','Key removed. Open-Meteo still works without a key.');}catch(e){message.textContent=e.message}}));
   box.append(message,actions);
  });
 }};
})();
