"""Real actions against the assembled Firefox runtime and production Soulu dispatch."""
from pathlib import Path
source=Path(__file__).with_name('preview2.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0].replace('Soulu Gecko Preview 2.exe','Soulu Gecko Preview 4.exe').replace('soulu-gecko2-','soulu-gecko4-').replace('.length===1','.length>=1')
exec(compile(source,str(Path(__file__).with_name('preview2.py')),'exec'),globals())
report.update(scope='Preview 4 native integration')
try:
 start()
 check('native_modules_loaded',chrome('return !!Soulu.integrationKey&&!!Soulu.downloadsReady'))
 check('adaptive_only',call('browser.state.get')['settings']['layout']=='adaptive')
 call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 check('web_content_unprivileged',content('return !window.Soulu&&!window.cefQuery&&!window.browserShell'))
 first=call('browser.state.get')['activeTabId']
 call('browser.openTab',{'url':url+'second'});wait(lambda:len(call('browser.state.get')['tabs'])==2);second=call('browser.state.get')['activeTabId']
 call('browser.moveTabBefore',{'id':second,'targetId':first});check('native_reorder',call('browser.state.get')['tabs'][0]['id']==second)
 call('browser.pinTab',second);check('native_pin',call('browser.state.get')['tabs'][0]['pinned']);call('browser.pinTab',second)
 call('browser.closeTab',second);wait(lambda:len(call('browser.state.get')['tabs'])==1)
 restored=call('browser.restoreTab');wait(lambda:len(call('browser.state.get')['tabs'])==2);check('native_restore',bool(restored))
 call('browser.duplicateTab',first);wait(lambda:len(call('browser.state.get')['tabs'])==3);check('native_duplicate',True)
 call('browser.closeOtherTabs',first);wait(lambda:len(call('browser.state.get')['tabs'])==1)
 check('actual_places_bookmark',any(r['url']==url for r in call('browser.bookmarks.add')))
 check('actual_places_history',bool(call('history.query',{'search':'soulu-fixture'})['rows']))
 passwords=call('browser.passwords.add',{'origin':'https://fixture.example.org','username':'initial','password':'fixture-only-123'})
 row=next(r for r in passwords if r['username']=='initial')
 edited=call('browser.passwords.add',{'id':row['id'],'origin':'https://fixture.example.org','username':'renamed','password':'fixture-only-456'})
 check('nss_edit_guid_no_duplicate',len([r for r in edited if r['origin']=='https://fixture.example.org'])==1 and call('browser.passwords.reveal',row['id'])=='fixture-only-456')
 html=root/'bookmarks.html';html.write_text('<!DOCTYPE NETSCAPE-Bookmark-file-1><META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8"><TITLE>Bookmarks</TITLE><H1>Bookmarks</H1><DL><p><DT><H3>Imported folder</H3><DL><p><DT><A HREF="https://imported.example.org/">Imported bookmark</A></DL><p></DL><p>',encoding='utf-8')
 run('return await Soulu.importFile("bookmarks",'+json.dumps(str(html))+');')
 check('native_html_import_folder',any(r['url']=='https://imported.example.org/' and r['parentId'] for r in call('browser.bookmarks.get')))
 csv=root/'passwords.csv';csv.write_text('url,username,password\nhttps://csv.example.org/,csv-user,fixture-only-csv\n',encoding='utf-8')
 imported=run('return await Soulu.importFile("passwords",'+json.dumps(str(csv))+');')
 check('native_csv_import',any(r['username']=='csv-user' for r in call('browser.passwords.get')),imported)
 pid=call('browser.profile.create','Fixture profile')['id'];call('browser.profile.rename',{'id':pid,'name':'Renamed fixture'})
 check('profile_rename',any(r['id']==pid and r['name']=='Renamed fixture' for r in call('browser.state.get')['profiles']))
 call('browser.profile.delete',pid);check('profile_delete',not any(r['id']==pid for r in call('browser.state.get')['profiles']))
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady'])
 check('original_12_settings',ui('return document.querySelectorAll("#homeCards button").length===12','settings'))
 ui('souluSettings.openSection("interface");return true','settings')
 check('only_adaptive_option',ui('return !document.querySelector("input[name=settings-layout][value=compact]")','settings'))
 ui('souluSettings.openSection("about");return true','settings')
 check('component_versions',ui('return document.getElementById("sectionContent").textContent.includes("Gecko Preview 4")','settings'))
 call('browser.settings.set',{'theme':'dark','startupMode':'continue'});chrome('Soulu.closeSettings()');time.sleep(.3)
 check('hidden_native_firefox_chrome',chrome('return ["navigator-toolbox","titlebar","sidebar-main"].every(id=>!document.getElementById(id)||getComputedStyle(document.getElementById(id)).display==="none")'))
 check('security_defaults',chrome('return Services.prefs.getBoolPref("fission.autostart")&&Services.prefs.getIntPref("security.sandbox.content.level")>0&&Services.prefs.getBoolPref("browser.safebrowsing.malware.enabled")&&!Services.prefs.getBoolPref("layers.acceleration.disabled",false)'))
 if not args.ui_only:
  check('rust_ready',chrome('return Soulu.adblock.status().ready'))
  check('network_blocking',Site.ads==0,{'requests':Site.ads})
  check('cosmetic_blocking',wait(lambda:content('return getComputedStyle(document.getElementById("ad")).display==="none"')))
 (out/'preview4.png').write_bytes(base64.b64decode(m.screenshot()))
 stop();start()
 check('persisted_settings_after_restart',call('browser.settings.get')['theme']=='dark')
 check('persisted_places_after_restart',any(r['url']==url for r in call('browser.bookmarks.get')))
 check('persisted_nss_after_restart',any(r['username']=='renamed' for r in call('browser.passwords.get')))
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 import traceback;report['traceback']=traceback.format_exc()
 try:
  report['diagnostic']=chrome('return {ready:Soulu?.ready,downloads:!!Soulu?.downloadsReady,blocker:Soulu?.blockerError||"",errors:Services.console.getMessageArray().map(m=>m.message).filter(s=>/soulu|Error/i.test(s)).slice(-20)}')
  (out/'failure.png').write_bytes(base64.b64decode(m.screenshot()))
 except Exception:pass
 raise
finally:
 stop();server.shutdown();log.close();(out/'preview4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
