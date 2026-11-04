"""Only requested Preview 11 regressions: weather and bookmark folder deletion."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{}};geo_requests=0;forecast_requests=0
phase=os.environ.get("SOULU_GECKO11_PHASE","all")
original_get=Site.do_GET
def data_response(handler,data):
 data=json.dumps(data).encode();handler.send_response(200);handler.send_header('Content-Type','application/json');handler.send_header('Content-Length',str(len(data)));handler.end_headers();handler.wfile.write(data)
def post(handler):
 global geo_requests
 if handler.path.startswith('/geolocation'):
  geo_requests+=1;data_response(handler,{'location':{'lat':56.84,'lng':60.61},'accuracy':20})
 else:handler.send_error(404)
def get(handler):
 global forecast_requests
 if handler.path.startswith('/forecast'):
  forecast_requests+=1;data_response(handler,{'current':{'temperature_2m':7,'apparent_temperature':5,'relative_humidity_2m':60,'wind_speed_10m':8,'precipitation':0,'weather_code':1},'daily':{'time':['2026-11-05','2026-11-06'],'weather_code':[1,2],'temperature_2m_max':[8,9],'temperature_2m_min':[1,2],'precipitation_probability_max':[10,20]}})
 elif handler.path.startswith('/geocoding'):data_response(handler,{'results':[{'latitude':56.84,'longitude':60.61,'name':'Екатеринбург'}]})
 else:original_get(handler)
Site.do_POST=post;Site.do_GET=get
loopback=f'http://127.0.0.1:{server.server_port}'
try:
 start()
 run('Soulu.config.onboarding={done:true,step:6};await Soulu.backend.save();return true;')
 call('browser.navigate','soulu://home');wait(lambda:ui('return !!document.getElementById("weatherToggle")','page'))
 if phase!='weather':
  # Create the same non-empty Mozilla folder and an unrelated bookmark to protect.
  fixture=run('const b=Soulu.backend.PlacesUtils.bookmarks;const f=await b.insert({parentGuid:b.toolbarGuid,type:b.TYPE_FOLDER,title:"Mozilla"});const sub=await b.insert({parentGuid:f.guid,type:b.TYPE_FOLDER,title:"Вложенная папка"});const child=await b.insert({parentGuid:sub.guid,url:"https://mozilla.test/",title:"Удаляемая закладка"});const keep=await b.insert({parentGuid:b.toolbarGuid,url:"https://keep.example.org/",title:"Сохранить"});await Soulu.bookmarks("invalidate");return {folder:f.guid,sub:sub.guid,child:child.guid,keep:keep.guid};')
  rows=call('browser.bookmarks.get');folder=next(x for x in rows if x.get('guid')==fixture['folder']);folder_id=folder['id']
  def open_delete():
   ui('await window.souluNavigation.openBookmarks();return true;')
   ui('document.querySelector('+json.dumps('[data-bookmark-id="'+str(folder_id)+'"]')+').dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,clientX:70,clientY:200}));return true;')
   wait(lambda:chrome('return [...document.querySelectorAll("menupopup menuitem")].some(n=>n.parentElement.state==="open"&&n.getAttribute("label")==="Удалить");'))
   chrome('const item=[...document.querySelectorAll("menupopup menuitem")].find(n=>n.parentElement.state==="open"&&n.getAttribute("label")==="Удалить");item.doCommand();item.parentElement.hidePopup();return true;')
   wait(lambda:ui('return !!document.getElementById("soulu-bookmark-delete")?.open;'))
  open_delete()
  check('folder_delete_opens_soulu_confirmation',ui('return document.getElementById("soulu-bookmark-delete").textContent.includes("Mozilla")'))
  check('confirmation_is_visible_and_clickable',wait(lambda:ui('const b=document.getElementById("soulu-bookmark-delete-confirm"),r=b.getBoundingClientRect();return r.width>0&&r.y>=0&&r.bottom<=innerHeight&&document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===b;')))
  (out/'bookmark-confirm11.png').write_bytes(base64.b64decode(m.screenshot()))
  ui('document.querySelector("#soulu-bookmark-delete button").click();return true;')
  check('cancel_preserves_nonempty_folder',any(x['id']==folder_id for x in call('browser.bookmarks.get')))
  open_delete();ui('document.getElementById("soulu-bookmark-delete-confirm").click();return true;')
  check('mozilla_folder_and_all_children_deleted',wait(lambda:not any(x.get('guid') in [fixture['folder'],fixture['sub'],fixture['child']] for x in call('browser.bookmarks.get'))))
  check('unrelated_bookmark_preserved',any(x.get('guid')==fixture['keep'] for x in call('browser.bookmarks.get')))
  # Verify actual Places storage, not only the visible cached list.
  check('deletion_persisted_in_places',run('const b=Soulu.backend.PlacesUtils.bookmarks;return !await b.fetch('+json.dumps(fixture['folder'])+')&&!await b.fetch('+json.dumps(fixture['child'])+')&&!!await b.fetch('+json.dumps(fixture['keep'])+');'))
 if phase!='bookmarks':
  # Exercise the real WebIDL Geolocation service using Gecko's local test provider.
  configured=run('Services.prefs.setBoolPref("geo.provider.testing",true);Services.prefs.setBoolPref("geo.prompt.testing",true);Services.prefs.setBoolPref("geo.prompt.testing.allow",true);Services.prefs.setBoolPref("geo.provider.ms-windows-location",false);Services.prefs.setStringPref("geo.provider.network.url",'+json.dumps(loopback+'/geolocation')+');Services.prefs.setIntPref("geo.provider.network.timeToWaitBeforeSending",10);Soulu.config.rules.sites["soulu://home"]={geolocation:0};Soulu.config.settings.homeWeatherMode="automatic";Soulu.config.settings.homeWeatherCity="";window.__souluWeatherObserver={observe(subject){const c=subject.QueryInterface(Ci.nsIHttpChannel);if(!["api.open-meteo.com","geocoding-api.open-meteo.com"].includes(c.URI.host))return;if(window.__souluWeatherFail){c.cancel(Cr.NS_ERROR_FAILURE);return;}c.redirectTo(Services.io.newURI('+json.dumps(loopback)+'+(c.URI.host==="api.open-meteo.com"?"/forecast":"/geocoding")));}};Services.obs.addObserver(window.__souluWeatherObserver,"http-on-modify-request");return true;')
  check('weather_fixture_configured',configured is True,configured)
  print('weather_before_request',chrome('return {api:typeof navigator.geolocation?.getCurrentPosition,backend:typeof Soulu.weather,uri:document.documentURI};'),flush=True)
  automatic=call('home.weather',{'interactive':False})
  check('automatic_weather_uses_working_geolocation',isinstance(automatic,dict) and automatic.get('status')=='ready' and automatic.get('current',{}).get('temperature_2m')==7,automatic)
  check('actual_native_geolocation_provider_called',geo_requests>0,geo_requests)
  run('Soulu.config.settings.homeWeatherMode="configured";Soulu.config.settings.homeWeatherCity="Екатеринбург";return true;')
  manual=call('home.weather',{'interactive':False});check('configured_city_weather_works',manual.get('status')=='ready' and manual.get('city')=='Екатеринбург',manual)
  run('Soulu.config.settings.homeWeatherCity="ошибка";window.__souluWeatherFail=true;return true;')
  failed=call('home.weather',{'interactive':False});check('weather_failures_have_readable_message',failed.get('status')=='unavailable' and 'Не удалось получить погоду' in failed.get('error','') and 'QueryInterface' not in failed.get('error',''),failed)
  run('Soulu.notify();return true;');time.sleep(.3)
  ui('document.getElementById("weatherToggle").click();return true;','page')
  check('home_weather_never_displays_internal_exception',wait(lambda:ui('return document.getElementById("weatherDetail").textContent.includes("Не удалось получить погоду")&&!/QueryInterface|getService|@mozilla/.test(document.getElementById("weatherDetail").textContent);','page')))
  (out/'weather11.png').write_bytes(base64.b64decode(m.screenshot()))
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:report['console']=chrome('return Services.console.getMessageArray().map(x=>x.message).slice(-30)');print('failure_console',report['console'],flush=True)
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/((phase+'11.json') if phase!='all' else 'preview11.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');log.close();server.shutdown()
