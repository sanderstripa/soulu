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
 check('product_name',chrome('return Services.appinfo.name==="Soulu"'))
 check('extensions_default_off',chrome('return Soulu.config.settings.showExtensions===false'))
 check('extensions_icon_hidden',wait(lambda:ui('return document.getElementById("soulu-extensions-menu")?.hidden')))
 check('no_default_mozilla_folder',not any(r.get('title') in ['Mozilla Firefox','Mozilla'] for r in call('browser.bookmarks.get')))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("2")','page'))
 chrome('const d=Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);d.initWithPath('+json.dumps(str(root/'environment'))+');try{Services.dirsvc.undefine("LocalAppData");}catch{}Services.dirsvc.set("LocalAppData",d);return true;')
 ui('document.querySelector("#controls button").click();return true;','page');wait(lambda:ui('return !!document.querySelector("#soulu-import-source option")','page'))
 ui('const s=document.getElementById("soulu-import-source");s.value=[...s.options].find(x=>x.textContent.includes("Chrome")).value;s.dispatchEvent(new Event("change"));document.getElementById("soulu-import-start").click();return true;','page')
 check('one_active_import_ok',wait(lambda:ui('const buttons=[...document.querySelectorAll(".soulu-import-actions button")].filter(b=>!b.hidden);return buttons.length===1&&buttons[0].textContent==="OK"&&!buttons[0].disabled;','page')))
 (out/'import-complete.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('document.getElementById("soulu-import-close").click();document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("3")','page'))
 ui('const s=document.querySelector("#controls select");s.value="dark";s.dispatchEvent(new Event("change"));return true;','page');wait(lambda:ui('return document.body.dataset.theme==="dark"','page'))
 check('dark_theme_control_readable',ui('const s=document.querySelector("#controls select"),c=getComputedStyle(s);return c.backgroundColor!=="rgb(255, 255, 255)"&&c.color!==c.backgroundColor&&getComputedStyle(document.body).colorScheme==="dark";','page'))
 (out/'welcome-dark.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("4")','page'))
 ui('document.querySelector("#controls input[type=checkbox]").click();return true;','page');wait(lambda:chrome('return Soulu.config.rules.sites["soulu://home"]?.geolocation===0'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return !!document.getElementById("welcomeVpnKey")','page'))
 check('single_vpn_input_composition',ui('const k=document.getElementById("welcomeVpnKey");return !document.getElementById("welcomeVpnName")&&k.getBoundingClientRect().width>400&&k.rows===3;','page'))
 ui('document.getElementById("welcomeVpnKey").value="vless://00000000-0000-4000-8000-000000000001@example.org:443?security=tls&type=tcp#Fixture";document.querySelector("#controls button").click();return true;','page')
 check('canonical_welcome_vpn',wait(lambda:chrome('return Soulu.config.vpn.profiles.some(p=>p.name==="Fixture"&&p.protocol==="vless"&&p.address==="example.org:443")')))
 check('vpn_success_confirmation',wait(lambda:ui('return document.getElementById("welcomeVpnResult").textContent.includes("успешно");','page')))
 (out/'welcome-vpn.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("6")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return !!document.getElementById("weatherToggle")','page'))
 auto=call('home.weather');check('live_automatic_weather_after_welcome',auto.get('status')=='ready' and isinstance(auto.get('current',{}).get('temperature_2m'),(int,float)) and bool(auto.get('city')),auto)
 # Also cover the incomplete row schema written by Preview 12.
 run('Soulu.config.vpn.profiles.push({id:"legacy",name:"Legacy",link:"vless://00000000-0000-4000-8000-000000000002@legacy.example.org:443#Legacy"});Soulu.config.vpn.defaultProfileId="legacy";await Soulu.backend.save();return true;')
 call('browser.settings.openWindow','vpn');wait(lambda:ui('return !!document.getElementById("vpn-profile-key")','settings'))
 check('vpn_settings_after_welcome_and_legacy_row',ui('return window.souluSettings.current.vpn.profiles.every(r=>r.protocol&&r.address)&&!document.getElementById("dataMessage").textContent&&document.querySelectorAll("[data-vpn-profile]").length===2;','settings'))
 (out/'vpn-settings.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('window.souluSettings.report(Error("Проверка сообщения"));window.souluSettings.openSection("about");return true;','settings')
 check('section_errors_do_not_leak',ui('return document.getElementById("dataMessage").textContent===""&&!document.getElementById("dataMessage").classList.contains("error")&&!document.getElementById("sectionError");','settings'))
 call('settings.close')
 run('Soulu.config.settings.showExtensions=true;Soulu.refresh();Soulu.notify();return true;');wait(lambda:ui('return document.getElementById("soulu-extensions-menu")&&!document.getElementById("soulu-extensions-menu").hidden'))
 chrome('Soulu.dispatch("browser.extensions.overflow",{profile:Soulu.config.profile,tabId:Soulu.native.tabID(gBrowser.selectedTab),generation:gBrowser.selectedBrowser.browsingContext.currentWindowGlobal.innerWindowId,anchor:{x:innerWidth-180,y:10,width:28,height:28}},{appURI:"file:///index.html",gesture:{at:Date.now()}}).catch(console.error);return true;')
 check('empty_extensions_menu_has_label',wait(lambda:chrome('return [...document.querySelectorAll("menupopup[data-soulu-extensions] menuitem")].some(n=>n.parentElement.state==="open"&&n.getAttribute("label")==="Нет расширений")')))
 (out/'extensions-empty.png').write_bytes(base64.b64decode(m.screenshot()))
 chrome('for(const p of document.querySelectorAll("menupopup[data-soulu-extensions]"))p.hidePopup();return true;')
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:
  from PIL import ImageGrab
  ImageGrab.grab().save(out/'failure-desktop.png')
  print(chrome('return Services.console.getMessageArray().map(x=>x.message).slice(-25)'),flush=True)
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'preview13.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');log.close();server.shutdown()
