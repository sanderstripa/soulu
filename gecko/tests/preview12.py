"""Requested Soul regressions against the production application surface."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
source=source.replace("exec(compile(source,", "source=source.replace(\"else:command=[str(binary),*headless\",\"else:command=[str(binary),'-app',str(binary.parent/'browser/application.ini'),*headless\")\nexec(compile(source,")
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
import sqlite3
report={'passed':False,'checks':{}}
for relative,name in [('Google/Chrome/User Data','chrome'),('Microsoft/Edge/User Data','edge')]:
 base=root/'environment'/relative;folder=base/'Default';folder.mkdir(parents=True,exist_ok=True)
 (base/'Local State').write_text(json.dumps({'profile':{'info_cache':{'Default':{'name':'Fixture '+name}}}}))
 (folder/'Preferences').write_text('{}')
 node={'type':'url','name':'Imported '+name,'url':'https://'+name+'.migration.example.org/','date_added':'13300000000000000','id':'1'}
 (folder/'Bookmarks').write_text(json.dumps({'version':1,'roots':{k:{'type':'folder','name':k,'children':[node] if k=='bookmark_bar' else []} for k in ['bookmark_bar','other','synced']}}))
 with sqlite3.connect(folder/'History') as db:
  db.execute('CREATE TABLE urls (id INTEGER PRIMARY KEY,url TEXT,title TEXT,last_visit_time INTEGER,typed_count INTEGER,hidden INTEGER)')
  db.execute('INSERT INTO urls VALUES (1,?,?,?,?,0)',('https://'+name+'.history.example.org/','Imported history '+name,int((time.time()+11644473600)*1000000),1))
 with sqlite3.connect(folder/'Web Data') as db:
  db.execute('CREATE TABLE autofill (name TEXT,value TEXT,count INTEGER,date_created INTEGER,date_last_used INTEGER)')
  db.execute('INSERT INTO autofill VALUES (?,?,?,?,?)',('fixture'+name,'imported value',2,int(time.time()),int(time.time())))

try:
 start()
 check('opaque_by_default',chrome('return Sona.config.settings.mattePanel===false'))
 check('weather_defaults',chrome('return Sona.config.settings.homeWeatherMode==="automatic"&&Sona.config.settings.homeWeatherUnits==="celsius"'))
 check('engine_identity_soul',chrome('return Services.appinfo.name==="Soul"'))
 wait(lambda:ui('return !!document.querySelector("#actions .primary")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page')
 wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("2")','page'))
 chrome('const d=Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);d.initWithPath('+json.dumps(str(root/'environment'))+');try{Services.dirsvc.undefine("LocalAppData");}catch{}Services.dirsvc.set("LocalAppData",d);return true;')
 ui('document.querySelector("#controls button").click();return true;','page')
 wait(lambda:ui('return !!document.querySelector("#sona-import-source option")','page'))
 ui('const n=document.getElementById("sona-import-source");n.value=[...n.options].find(x=>x.textContent.includes("Chrome")).value;n.dispatchEvent(new Event("change"));document.getElementById("sona-import-start").click();return true;','page')
 check('import_completion_disables_repeat_action',wait(lambda:ui('const b=document.getElementById("sona-import-start");return b.textContent==="OK"&&b.disabled;','page')))
 ui('document.getElementById("sona-import").close();return true;','page')
 # Proceed through the existing welcome steps and save a key without leaving it.
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("3")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("4")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return !!document.getElementById("welcomeVpnKey")','page'))
 ui('document.getElementById("welcomeVpnName").value="Fixture";document.getElementById("welcomeVpnKey").value="vless://00000000-0000-4000-8000-000000000001@example.org:443?security=tls&type=tcp#Fixture";document.querySelector("#controls button").click();return true;','page')
 check('vpn_key_saved_inside_welcome',wait(lambda:chrome('return Sona.config.vpn.profiles.some(p=>p.name==="Fixture")&&!Sona.settingsRequested')))
 check('welcome_remains_visible',ui('return location.pathname.endsWith("/onboarding.html")&&document.getElementById("controls").textContent.includes("OK")','page'))
 call('browser.settings.openWindow','extensions')
 wait(lambda:ui('return [...document.querySelectorAll(\"button\")].some(b=>b.textContent===\"Установленные расширения\")','settings'))
 ui('const b=[...document.querySelectorAll(\"button\")].find(b=>b.textContent===\"Установленные расширения\");b.click();return true;','settings')
 check('extensions_manager_opens',wait(lambda:chrome('return gBrowser.selectedBrowser.currentURI.spec==="about:addons"')))
 check('extensions_manager_is_not_covered_by_settings',wait(lambda:chrome('return !Sona.settingsRequested&&document.getElementById(\"sona-settings-frame\").hidden')))
 check('extensions_manager_has_soul_title',wait(lambda:content('return document.title.includes(\"Soul\")&&!document.body.innerText.includes(\"Firefox\");')))
 check('no_stock_toolbar',chrome('return getComputedStyle(document.getElementById("navigator-toolbox")).display==="none"'))
 run('Sona.config.onboarding={done:true,step:6};await Sona.backend.save();return true;')
 stop();start()
 check('same_profile_reopens',chrome('return Sona.ready&&Sona.config.onboarding.done&&Sona.config.vpn.profiles.some(p=>p.name==="Fixture")'))
 call('browser.settings.openWindow','startup')
 wait(lambda:ui('return !!document.getElementById("homeWeatherMode")','settings'))
 check('automatic_weather_disables_city',ui('return document.getElementById("homeWeatherMode").value==="automatic"&&document.getElementById("homeWeatherCity").disabled','settings'))
 ui('const n=document.getElementById("homeWeatherMode");n.value="configured";n.dispatchEvent(new Event("change",{bubbles:true}));return true;','settings')
 check('manual_weather_enables_city',wait(lambda:ui('return !document.getElementById("homeWeatherCity").disabled','settings')))
 # Exercise the shipping network stack against the actual public weather service.
 run('Sona.config.settings.homeWeatherMode="configured";Sona.config.settings.homeWeatherCity="Yekaterinburg";return true;')
 live=call('home.weather')
 check('live_weather_service_returns_temperature',live.get('status')=='ready' and isinstance(live.get('current',{}).get('temperature_2m'),(int,float)),live)
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:
  from PIL import ImageGrab
  ImageGrab.grab().save(out/'failure-desktop.png')
 except Exception:pass
 try:print(chrome('return {uri:document.documentURI,name:Services.appinfo.name,console:Services.console.getMessageArray().map(x=>x.message).slice(-40)}'),flush=True)
 except Exception as diagnostics_error:
  print('normal diagnostics unavailable',str(diagnostics_error),flush=True)
  try:
   print('window handles',m.window_handles,flush=True)
   for handle in m.window_handles:
    m.switch_to_window(handle);m.set_context('chrome')
    print(m.execute_script('return {uri:document.documentURI,console:Components.classes["@mozilla.org/consoleservice;1"].getService(Components.interfaces.nsIConsoleService).getMessageArray().map(x=>x.message).slice(-60)};'),flush=True)
  except Exception as error:print('fallback diagnostics',str(error),flush=True)
 raise
finally:
 try:stop()
 finally:(out/'preview12.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');log.close();server.shutdown()
