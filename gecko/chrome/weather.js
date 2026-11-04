/* Open-Meteo over Gecko's proxy-aware network. Never infer location via a third-party IP lookup. */
(()=>{
 const {shared,IOUtils,PathUtils,save}=Soulu.backend;shared.weatherState??={cache:null,inflight:null,lastError:''};const weatherState=shared.weatherState;
 let {cache,inflight,lastError}=weatherState;
 const file=PathUtils.join(PathUtils.profileDir,'soulu-weather.json');
 const json=async url=>{const response=await fetch(url,{credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error('Open-Meteo HTTP '+response.status);return response.json();};
 async function coordinates(interactive){
  if(shared.config.rules.sites['soulu://home']?.geolocation!==0){
   if(!interactive||shared.config.rules.sites['soulu://home']?.geolocation===2)throw Error('Разрешите геолокацию для погоды или укажите город в настройках → Запуск и главная.');
   const allowed=Services.prompt.confirm(window,'Погода Soulu','Разрешить геолокацию для погоды? Приблизительные координаты будут переданы Open-Meteo. Город также можно указать вручную в настройках.');
   shared.config.rules.sites['soulu://home']={...(shared.config.rules.sites['soulu://home']||{}),geolocation:allowed?0:2};await save();if(!allowed)throw Error('Для автоматической погоды разрешите геолокацию или укажите город в настройках.');
  }
  const geo=Cc['@mozilla.org/geolocation;1'].getService(Ci.nsISupports).QueryInterface(Ci.nsIDOMGeoGeolocation);
  return new Promise((resolve,reject)=>geo.getCurrentPosition(p=>resolve({latitude:Math.round(p.coords.latitude*100)/100,longitude:Math.round(p.coords.longitude*100)/100,name:'Рядом с вами'}),()=>reject(Error('Геолокация недоступна. Укажите город в настройках → Запуск и главная.')),{timeout:8000,maximumAge:900000,enableHighAccuracy:false}));
 }
 Soulu.weatherReady=weatherState.cache?Promise.resolve():IOUtils.readJSON(file).then(value=>{weatherState.cache=value;cache=value;}).catch(()=>{});
 Soulu.weatherSnapshot=()=>weatherState.cache;
 Soulu.weather=async(options={})=>{
 cache=weatherState.cache;inflight=weatherState.inflight;
  const s=shared.config.settings,city=String(s.homeWeatherCity||'').trim(),mode=s.homeWeatherMode||(city?'configured':'automatic'),key=[mode,city,s.homeWeatherUnits,s.language].join('|');
  if(!cache)try{cache=await IOUtils.readJSON(file);weatherState.cache=cache;}catch{}
  if(cache?.key===key&&Date.now()/1000-cache.fetchedAt<900)return cache;
  if(inflight?.key===key)return inflight.promise;
  const task=(async()=>{try{
   let place;
   if(mode==='configured'){
    if(!city)throw Error('Укажите город в настройках → Запуск и главная.');
    const data=await json('https://geocoding-api.open-meteo.com/v1/search?count=1&language='+encodeURIComponent(s.language||'ru')+'&name='+encodeURIComponent(city));place=data.results?.[0];if(!place)throw Error('Город не найден. Попробуйте полное название.');
   }else place=await coordinates(!!options.interactive);
   const query=new URLSearchParams({latitude:place.latitude,longitude:place.longitude,timezone:'auto',forecast_days:'6',current:'temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,precipitation,weather_code',daily:'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',temperature_unit:s.homeWeatherUnits==='fahrenheit'?'fahrenheit':'celsius'});
   const data=await json('https://api.open-meteo.com/v1/forecast?'+query);if(!Number.isFinite(data.current?.temperature_2m))throw Error('Погодный сервис вернул неполные данные.');
   cache={key,status:'ready',city:place.name,current:data.current,daily:data.daily,fetchedAt:Date.now()/1000};weatherState.cache=cache;lastError='';await IOUtils.writeJSON(file,cache,{tmpPath:file+'.tmp'});return cache;
  }catch(e){lastError=String(e.message||e);return cache?.key===key?{...cache,status:'stale',error:lastError}:{status:'unavailable',error:lastError};}finally{inflight=null;weatherState.inflight=null;}})();inflight={key,promise:task};weatherState.inflight=inflight;return task;
 };
 Soulu.weatherDiagnostics=()=>({error:lastError,cached:!!cache});
})();
