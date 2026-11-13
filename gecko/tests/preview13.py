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
 check('product_name',chrome('return Services.appinfo.name==="Sona"'))
 check('extensions_default_off',chrome('return Sona.config.settings.showExtensions===false'))
 check('extensions_icon_hidden',wait(lambda:ui('return document.getElementById("sona-extensions-menu")?.hidden')))
 check('no_default_mozilla_folder',not any(r.get('title') in ['Mozilla Firefox','Mozilla'] for r in call('browser.bookmarks.get')))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("2")','page'))
 chrome('const d=Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);d.initWithPath('+json.dumps(str(root/'environment'))+');try{Services.dirsvc.undefine("LocalAppData");}catch{}Services.dirsvc.set("LocalAppData",d);return true;')
 ui('document.querySelector("#controls button").click();return true;','page');wait(lambda:ui('return !!document.querySelector("#sona-import-source option")','page'))
 ui('const s=document.getElementById("sona-import-source");s.value=[...s.options].find(x=>x.textContent.includes("Chrome")).value;s.dispatchEvent(new Event("change"));document.getElementById("sona-import-start").click();return true;','page')
 check('one_active_import_ok',wait(lambda:ui('const buttons=[...document.querySelectorAll(".sona-import-actions button")].filter(b=>!b.hidden);return buttons.length===1&&buttons[0].textContent==="OK"&&!buttons[0].disabled;','page')))
 (out/'import-complete.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('document.getElementById("sona-import-close").click();document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("3")','page'))
 ui('document.querySelector("[data-theme-choice=dark]").click();return true;','page');wait(lambda:ui('return document.body.dataset.theme==="dark"','page'))
 check('dark_theme_control_readable',ui('const buttons=[...document.querySelectorAll("[data-theme-choice]")];return buttons.length===3&&buttons.every(b=>b.textContent.trim()&&getComputedStyle(b).color!==getComputedStyle(b).backgroundColor)&&buttons.find(b=>b.dataset.themeChoice==="dark").getAttribute("aria-pressed")=="true";','page'))
 ui('await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return true;','page')
 (out/'welcome-dark.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("4")','page'))
 ui('document.querySelector("#controls input[type=checkbox]").click();return true;','page');wait(lambda:chrome('return Sona.config.rules.sites["sona://home"]?.geolocation===0'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return !!document.getElementById("welcomeVpnKey")','page'))
 check('single_vpn_input_composition',ui('const k=document.getElementById("welcomeVpnKey");return !document.getElementById("welcomeVpnName")&&k.getBoundingClientRect().width>400&&k.rows===3;','page'))
 ui('document.getElementById("welcomeVpnKey").value="vless://00000000-0000-4000-8000-000000000001@example.org:443?security=tls&type=tcp#Fixture";document.querySelector("#controls button").click();return true;','page')
 check('canonical_welcome_vpn',wait(lambda:chrome('return Sona.config.vpn.profiles.some(p=>p.name==="Fixture"&&p.protocol==="vless"&&p.address==="example.org:443")')))
 check('vpn_success_confirmation',wait(lambda:ui('return document.getElementById("welcomeVpnResult").textContent.includes("успешно");','page')))
 ui('await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return true;','page')
 (out/'welcome-vpn.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("6")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return !!document.getElementById("weatherToggle")','page'))
 auto=call('home.weather');check('live_automatic_weather_after_welcome',auto.get('status')=='ready' and isinstance(auto.get('current',{}).get('temperature_2m'),(int,float)) and bool(auto.get('city')),auto)
 # Also cover the incomplete row schema written by Preview 12.
 run('Sona.config.vpn.profiles.push({id:"legacy",name:"Legacy",link:"vless://00000000-0000-4000-8000-000000000002@legacy.example.org:443#Legacy"});Sona.config.vpn.defaultProfileId="legacy";await Sona.backend.save();return true;')
 call('browser.settings.openWindow','vpn');wait(lambda:ui('return !!document.getElementById("vpn-profile-key")','settings'))
 check('vpn_settings_after_welcome_and_legacy_row',ui('return window.sonaSettings.current.vpn.profiles.every(r=>r.protocol&&r.address)&&!document.getElementById("dataMessage").textContent&&document.querySelectorAll("[data-vpn-profile]").length===2;','settings'))
 (out/'vpn-settings.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('window.sonaSettings.report(Error("Проверка сообщения"));window.sonaSettings.openSection("about");return true;','settings')
 check('section_errors_do_not_leak',ui('return document.getElementById("dataMessage").textContent===""&&!document.getElementById("dataMessage").classList.contains("error")&&!document.getElementById("sectionError");','settings'))
 call('settings.close')
 run('Sona.config.settings.showExtensions=true;Sona.refresh();Sona.notify();return true;');wait(lambda:ui('return document.getElementById("sona-extensions-menu")&&!document.getElementById("sona-extensions-menu").hidden'))
 chrome('Sona.dispatch("browser.extensions.overflow",{profile:Sona.config.profile,tabId:Sona.native.tabID(gBrowser.selectedTab),generation:gBrowser.selectedBrowser.browsingContext.currentWindowGlobal.innerWindowId,anchor:{x:innerWidth-180,y:10,width:28,height:28}},{appURI:"file:///index.html",gesture:{at:Date.now()}}).catch(console.error);return true;')
 check('empty_extensions_menu_has_label',wait(lambda:chrome('return [...document.querySelectorAll("menupopup[data-sona-extensions] menuitem")].some(n=>n.parentElement.state==="open"&&n.getAttribute("label")==="Нет расширений")')))
 (out/'extensions-empty.png').write_bytes(base64.b64decode(m.screenshot()))
 chrome('for(const p of document.querySelectorAll("menupopup[data-sona-extensions]"))p.hidePopup();return true;')
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
