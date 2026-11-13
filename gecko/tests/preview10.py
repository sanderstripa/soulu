"""Windows regression checks limited to migration, startup and product registration."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
import sqlite3,winreg
report={'passed':False,'checks':{}}
# Synthetic source data only. The runner's real browser profiles are untouched.
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
def import_ui(code,target='page'):
 return ui(code,target)
def close_import(target='page'):
 import_ui('document.getElementById("sona-import").close();return true;',target)
try:
 started=time.monotonic();start();elapsed=time.monotonic()-started
 wait(lambda:chrome('return !window.__sonaStartupHidden'))
 timing=chrome('return {presentation:window.__sonaStartupPresentation,timing:Sona.startupTimings}')
 check('startup_under_seven_seconds',timing['timing']['functionalFirstFrameProcessAge']<7000,{'attachSeconds':elapsed,**timing})
 check('sona_first_frame_no_firefox_toolbox',chrome('return getComputedStyle(document.getElementById("navigator-toolbox")).display==="none"&&document.documentElement.hasAttribute("sona-ui-ready")'))
 check('complete_backend_not_dead_stub',chrome('return Sona.ready&&!!Sona.integrationKey&&!!Sona.native'))
 # Point the native directory service at synthetic source profiles only.
 chrome('const d=Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);d.initWithPath('+json.dumps(str(root/'environment'))+');try{Services.dirsvc.undefine("LocalAppData");}catch{}Services.dirsvc.set("LocalAppData",d);return true;')
 wait(lambda:ui('return location.pathname.endsWith("/onboarding.html")','page'))
 ui('document.querySelector("#actions button.primary").click();return true;','page')
 wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("2")','page'))
 ui('document.querySelector("#controls button").click();return true;','page')
 check('welcome_button_opens_sona_import',wait(lambda:import_ui('return [...document.querySelectorAll("#sona-import-source option")].some(n=>n.textContent.includes("Chrome"));')))
 check('welcome_stays_on_import_step',ui('return document.getElementById("counter").textContent.startsWith("2")','page'))
 check('no_native_migration_or_preferences_window',chrome('return ![...Services.wm.getEnumerator(null)].some(w=>/migration\/|about:preferences/.test(w.document.documentURI))'))
 for label,brand in [('chrome','Chrome'),('edge','Edge')]:
  check(label+'_source_detected',import_ui('return [...document.querySelectorAll("#sona-import-source option")].some(n=>n.textContent.includes('+json.dumps(brand)+'));'))
  import_ui('const s=document.getElementById("sona-import-source");s.value=[...s.options].find(n=>n.textContent.includes('+json.dumps(brand)+')).value;s.dispatchEvent(new Event("change"));return true;')
  detected=import_ui('return [...document.querySelectorAll("#sona-import-types input")].map(n=>n.value);')
  check(label+'_profile_and_data_types_detected',all(k in detected for k in ['BOOKMARKS','HISTORY','FORMDATA']),detected)
  import_ui('document.getElementById("sona-import-start").click();return true;')
  wait(lambda:import_ui('return !document.getElementById("sona-import-start").disabled;'),45)
  check(label+'_sona_import_reports_success',import_ui('return document.getElementById("sona-import-status").textContent==="Импорт завершён. Данные сохранены в Sona.";'))
  check(label+'_bookmarks_imported_through_sona',any(x.get('url')=='https://'+label+'.migration.example.org/' for x in call('browser.bookmarks.get')))
  check(label+'_history_imported',bool(call('history.query',{'search':label+'.history.example.org'})['rows']))
  check(label+'_autofill_imported',run('const {FormHistory}=ChromeUtils.importESModule("resource://gre/modules/FormHistory.sys.mjs");return (await FormHistory.search(["fieldname","value"],{fieldname:'+json.dumps('fixture'+label)+'})).some(x=>x.value==="imported value");'))
 close_import()
 call('browser.settings.openWindow','profiles')
 wait(lambda:ui('return !!window.sonaBrowserImport&&!!window.sonaOpenImport','settings'))
 ui('window.sonaBrowserImport.open();return true;','settings')
 check('settings_import_opens_sona_dialog',wait(lambda:import_ui('return !!document.querySelector("#sona-import-source option");','settings')))
 check('no_firefox_text_in_sona_import',import_ui('return !/firefox/i.test(document.getElementById("sona-import").textContent);','settings'))
 close_import('settings')
 # The native CSV path is the engine-supported fallback for protected passwords.
 csv=root/'passwords.csv';csv.write_text('url,username,password\nhttps://password.migration.example.org/,fixture-user,fixture-password\n')
 imported=run('return await Sona.importFile("passwords",'+json.dumps(str(csv))+');')
 check('password_csv_reaches_native_nss',any(x['username']=='fixture-user' for x in call('browser.passwords.get')),imported)
 # Snapshot actual Windows registrations after browser startup.
 hits=[]
 for hive in [winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE]:
  try:
   with winreg.OpenKey(hive,r'Software\Clients\StartMenuInternet') as parent:
    for i in range(winreg.QueryInfoKey(parent)[0]):
     name=winreg.EnumKey(parent,i)
     if not name.lower().startswith('firefox'):continue
     try:
      with winreg.OpenKey(parent,name+r'\shell\open\command') as k:command=winreg.QueryValueEx(k,'')[0]
      if str(binary.parent.parent).lower() in command.lower():hits.append(command)
     except OSError:pass
  except OSError:pass
 check('startup_does_not_register_firefox',not hits,hits)
 check('payload_has_no_firefox_installer_or_registration_helpers',not any(p.name.lower() in {'helper.exe','default-browser-agent.exe','maintenanceservice_installer.exe'} for p in binary.parent.rglob('*')))
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:report['importUI']=ui('return {message:document.getElementById("message")?.textContent,dialog:document.getElementById("sona-import")?.innerText,scripts:[...document.scripts].map(s=>s.src)};','page');print('import_failure_UI',report['importUI'],flush=True)
 except Exception:pass
 try:report['console']=chrome('return Services.console.getMessageArray().map(x=>x.message).slice(-40)')
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'preview10.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
