/* Permission-gated native location, with approximate IP fallback, over the browser network. */
(()=>{
 const {shared,IOUtils,PathUtils,save}=Sona.backend;shared.weatherState??={cache:null,inflight:null,lastError:''};const weatherState=shared.weatherState;
 let {cache,inflight,lastError}=weatherState;
 const file=PathUtils.join(PathUtils.profileDir,'sona-weather.json');
 const settingsKey=()=>{const s=shared.config.settings,city=String(s.homeWeatherCity||'').trim();return [s.homeWeatherMode||(city?'configured':'automatic'),city,s.homeWeatherUnits,s.language].join('|');};
 const userError=message=>Object.assign(Error(message),{sonaWeatherMessage:message});
 const json=async url=>{const response=await fetch(url,{credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error('Open-Meteo HTTP '+response.status);return response.json();};
 async function coordinates(interactive){
  if(shared.config.rules.sites['sona://home']?.geolocation!==0){
   if(!interactive||shared.config.rules.sites['sona://home']?.geolocation===2)throw userError('Разрешите геолокацию для погоды или укажите город в настройках → Запуск и главная.');
   const allowed=Services.prompt.confirm(window,'Погода Sona','Разрешить геолокацию для погоды? Приблизительные координаты будут переданы Open-Meteo. Город также можно указать вручную в настройках.');
   shared.config.rules.sites['sona://home']={...(shared.config.rules.sites['sona://home']||{}),geolocation:allowed?0:2};await save();if(!allowed)throw userError('Для автоматической погоды разрешите геолокацию или укажите город в настройках.');
  }
  // This backend is chrome code, not a web document. The service exposes
  // Gecko's non-window Geolocation WebIDL object directly; it has no XPCOM QI.
  try{
   const geo=Cc['@mozilla.org/geolocation;1'].getService(Ci.nsISupports);
   const position=await Promise.race([new Promise((resolve,reject)=>geo.getCurrentPosition(resolve,reject,{timeout:2500,maximumAge:900000,enableHighAccuracy:false})),new Promise((_,reject)=>setTimeout(()=>reject(Error('Location timed out')),3000))]);
   return {latitude:Math.round(position.coords.latitude*100)/100,longitude:Math.round(position.coords.longitude*100)/100,name:'Рядом с вами'};
  }catch{
   if(shared.config.rules.sites['sona://home']?.geolocation!==0)throw userError('Определение местоположения отключено.');
   const place=await json('https://ipwho.is/?fields=success,latitude,longitude,city&lang='+encodeURIComponent(shared.config.settings.language||'ru'));
   if(place.success!==true||!Number.isFinite(place.latitude)||!Number.isFinite(place.longitude)||Math.abs(place.latitude)>90||Math.abs(place.longitude)>180)throw userError('Не удалось определить город автоматически.');
   return {latitude:Math.round(place.latitude*100)/100,longitude:Math.round(place.longitude*100)/100,name:String(place.city||'Рядом с вами')};
  }
 }
 Sona.weatherReady=weatherState.cache?Promise.resolve():IOUtils.readJSON(file).then(value=>{weatherState.cache=value;cache=value;}).catch(()=>{});
 Sona.weatherSnapshot=()=>weatherState.cache?.key===settingsKey()?weatherState.cache:null;
 Sona.weather=async(options={})=>{
 cache=weatherState.cache;inflight=weatherState.inflight;
  const s=shared.config.settings,city=String(s.homeWeatherCity||'').trim(),mode=s.homeWeatherMode||(city?'configured':'automatic'),key=[mode,city,s.homeWeatherUnits,s.language].join('|');
  if(!cache)try{cache=await IOUtils.readJSON(file);weatherState.cache=cache;}catch{}
  if(cache?.key===key&&Date.now()/1000-cache.fetchedAt<900)return cache;
  if(inflight?.key===key)return inflight.promise;
  const token=Symbol('weather-request');const task=(async()=>{try{
   let place;
   if(mode==='configured'){
    if(!city)throw userError('Укажите город в настройках → Запуск и главная.');
    const data=await json('https://geocoding-api.open-meteo.com/v1/search?count=1&language='+encodeURIComponent(s.language||'ru')+'&name='+encodeURIComponent(city));place=data.results?.[0];if(!place)throw userError('Город не найден. Попробуйте полное название.');
   }else place=await coordinates(!!options.interactive);
   const query=new URLSearchParams({latitude:place.latitude,longitude:place.longitude,timezone:'auto',forecast_days:'6',current:'temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,precipitation,weather_code',daily:'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',temperature_unit:s.homeWeatherUnits==='fahrenheit'?'fahrenheit':'celsius'});
   const data=await json('https://api.open-meteo.com/v1/forecast?'+query);if(!Number.isFinite(data.current?.temperature_2m))throw userError('Погодный сервис вернул неполные данные.');
   if(mode==='automatic'&&shared.config.rules.sites['sona://home']?.geolocation!==0)throw userError('Определение местоположения отключено.');
   const result={key,status:'ready',city:place.name,current:data.current,daily:data.daily,fetchedAt:Date.now()/1000};if(key===settingsKey()){cache=result;weatherState.cache=result;lastError='';await IOUtils.writeJSON(file,result,{tmpPath:file+'.tmp'});Sona.notify?.();}return result;
  }catch(e){console.error('Sona weather',e);lastError=e.sonaWeatherMessage||'Не удалось получить погоду. Проверьте подключение к интернету или укажите город в настройках → Запуск и главная.';weatherState.lastError=lastError;return cache?.key===key?{...cache,status:'stale',error:lastError}:{status:'unavailable',error:lastError};}})();inflight={key,promise:task,token};weatherState.inflight=inflight;const cleanup=()=>{if(weatherState.inflight?.token===token)weatherState.inflight=null;if(inflight?.token===token)inflight=null;};task.then(cleanup,cleanup);return task;
 };
 Sona.weatherDiagnostics=()=>({error:lastError,cached:!!cache});
})();
