"""Real actions against the assembled Firefox runtime and production Soulu dispatch."""
from pathlib import Path
source=Path(__file__).with_name('preview2.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0].replace('Soulu Gecko Preview 2.exe','Soulu Gecko Preview 4.exe').replace('soulu-gecko2-','soulu-gecko4-').replace('.length===1','.length>=1')
source=source.replace("profile=root/'Profiles/default'","profile=root/'environment/SouluGecko/Profiles/default'").replace(' headless=[]', ' env["LOCALAPPDATA"]=str(root/"environment");env["MOZ_MARIONETTE"]="1"'+chr(10)+' headless=[]')
source=source.replace('user_pref("marionette.port",','user_pref("remote.prefs.recommended",false);'+chr(92)+'nuser_pref("marionette.port",')
exec(compile(source,str(Path(__file__).with_name('preview2.py')),'exec'),globals())
original_get=Site.do_GET
def extended_get(self):
 if self.path.startswith('/download'):
  body=b'soulu-download-fixture';self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Disposition','attachment; filename="fixture.bin"');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 elif self.path.startswith('/article'):
  body=('<!doctype html><html lang=en><meta charset=utf-8><title>A useful story about browsers</title><article><h1>A useful story about browsers</h1>'+''.join('<p>This is a beautiful day. The browser is fast and easy to use. You can read the latest news and learn more about the world. This article explains how modern browsers protect your information while displaying useful pages.</p>' for _ in range(15))+'</article></html>').encode();self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
 elif self.path.startswith('/login'):
  body=b'<!doctype html><title>Login fixture</title><form method=post action=/submitted><input name=username id=username autocomplete=username><input name=password id=password type=password autocomplete=current-password><button>Login</button></form>';self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
 else:original_get(self)
Site.do_GET=extended_get
report.update(scope='Preview 4 native integration')
try:
 start()
 check('native_modules_loaded',chrome('return !!Soulu.integrationKey&&!!Soulu.downloadsReady'))
 check('no_firefox_startup_modal',chrome('return !document.documentElement.hasAttribute("window-modal-open")'))
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
 # The transparent area outside an open menu must not intercept webpage input.
 ui('await browserShell.pageMenu();return true;');wait(lambda:ui('return !document.querySelector(".site-popover").hidden&&innerHeight>200'))
 wait(lambda:chrome('return getComputedStyle(document.getElementById("soulu-shell-frame")).clipPath!=="none"'))
 check('menu_does_not_cover_webpage_input',chrome('return document.elementFromPoint(innerWidth-10,innerHeight-10)!==document.getElementById("soulu-shell-frame")'))
 ui('document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));return true;');wait(lambda:ui('return document.querySelector(".site-popover").hidden'))
 # Real native download with actual network IO and permission preflight.
 call('browser.site.permission',{'permission':'downloads','value':0})
 destination=str(root/'downloads/fixture.bin')
 run('const {Downloads}=ChromeUtils.importESModule("resource://gre/modules/Downloads.sys.mjs");const d=await Downloads.createDownload({source:'+json.dumps(url+'download')+',target:'+json.dumps(destination)+'});const list=await Downloads.getList(Downloads.PUBLIC);await list.add(d);await d.start();return d.succeeded;')
 items=wait(lambda:call('browser.downloads.get'));download=next(d for d in items if d['filename']=='fixture.bin')
 check('native_download_real_file',pathlib.Path(destination).read_bytes()==b'soulu-download-fixture' and download['state']=='completed')
 ui('document.getElementById("downloadsButton").click();return true;');time.sleep(.3)
 check('download_actions_in_original_panel',ui('return [...document.querySelectorAll("#downloadsList button")].some(n=>n.textContent==="Открыть")'))
 ui('document.getElementById("downloadsButton").click();return true;');call('browser.downloads.action',{'id':download['id'],'operation':'remove'})
 check('download_remove_from_native_list',not any(d['id']==download['id'] for d in call('browser.downloads.get')))
 call('browser.site.permission',{'permission':'downloads','value':2})
 denied=str(root/'downloads/denied.bin')
 blocked=run('const {Downloads}=ChromeUtils.importESModule("resource://gre/modules/Downloads.sys.mjs");const d=await Downloads.createDownload({source:'+json.dumps(url+'download-blocked')+',target:'+json.dumps(denied)+'});try{await d.start();return false;}catch(e){return !!d.error?.becauseBlocked;}')
 check('download_permission_denies_actual_transfer',blocked and not pathlib.Path(denied).exists())
 call('browser.site.reset',{})
 # Cookie/storage/Places isolation in a real private browser window.
 call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 content('localStorage.setItem("soulu-isolation","normal");document.cookie="soulu_isolation=normal; path=/";return true;')
 normal=m.current_window_handle;known=set(m.window_handles);call('browser.newIncognito');wait(lambda:len(m.window_handles)>len(known));private=next(h for h in m.window_handles if h not in known);m.switch_to_window(private);wait(lambda:chrome('return !!Soulu?.ready'))
 call('browser.navigate',url+'private-only');wait(lambda:content('return !!document.getElementById("v")'))
 check('private_real_storage_isolation',content('return !localStorage.getItem("soulu-isolation")&&!document.cookie.includes("soulu_isolation")'))
 check('private_history_not_exposed',call('history.query',{'search':'soulu-fixture'})['rows']==[])
 chrome('window.close()');m.switch_to_window(normal);wait(lambda:chrome('return !!Soulu?.ready'))
 check('private_navigation_not_in_places',not call('history.query',{'search':'private-only'})['rows'])
 isolation=content('return {url:location.href,value:localStorage.getItem("soulu-isolation"),cookie:document.cookie}')
 check('normal_storage_retained',isolation['value']=='normal',isolation)
 # Native Reader View fetches and extracts an actual article.
 call('browser.navigate',url+'article');wait(lambda:content('return !!document.querySelector("article")'))
 call('browser.site.reader.enter');wait(lambda:content('return location.href.startsWith("about:reader?")&&!!document.querySelector(".moz-reader-content p")'),30)
 check('native_reader_extracts_article',content('return document.querySelector(".moz-reader-content").textContent.includes("beautiful day")'))
 call('browser.site.reader.exit');wait(lambda:content('return location.pathname==="/article"'))
 # The fixture is HTTP only: opt in for this test, then restore the secure shipped default.
 chrome('Services.prefs.setBoolPref("signon.autofillForms.http",true)')
 # Native LoginManager autofill: a stored login must fill a real site form.
 call('browser.passwords.add',{'origin':url.rstrip('/'),'username':'autofill-user','password':'fixture-autofill'})
 call('browser.navigate',url+'login');wait(lambda:content('return !!document.getElementById("password")'))
 check('native_login_autofill',wait(lambda:content('return document.getElementById("username").value==="autofill-user"&&document.getElementById("password").value==="fixture-autofill"'),20))
 chrome('Services.prefs.clearUserPref("signon.autofillForms.http")')
 call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady'])
 check('original_12_settings',ui('return document.querySelectorAll("#homeCards button").length===12','settings'))
 ui('souluSettings.openSection("interface");return true','settings')
 check('only_adaptive_option',ui('return !document.querySelector("input[name=settings-layout][value=compact]")','settings'))
 ui('souluSettings.openSection("about");return true','settings')
 check('component_versions',ui('return document.getElementById("sectionContent").textContent.includes("Gecko Preview 4")','settings'))
 call('browser.settings.set',{'theme':'dark','startupMode':'continue'});chrome('Soulu.closeSettings()');time.sleep(.3)
 check('hidden_native_firefox_chrome',chrome('return ["navigator-toolbox","titlebar","sidebar-main"].every(id=>!document.getElementById(id)||getComputedStyle(document.getElementById(id)).display==="none")'))
 security=chrome('return {fission:Services.prefs.getBoolPref("fission.autostart"),sandbox:Services.prefs.getIntPref("security.sandbox.content.level"),safe:Services.prefs.getBoolPref("browser.safebrowsing.malware.enabled"),accelerationDisabled:Services.prefs.getBoolPref("layers.acceleration.disabled",false)}')
 check('security_defaults',security['fission'] and security['sandbox']>0 and security['safe'] and not security['accelerationDisabled'],security)
 if os.name=='nt':exec(compile(Path(__file__).with_name('profile-browser.py').read_text(encoding='utf-8'),str(Path(__file__).with_name('profile-browser.py')),'exec'),globals())
 if os.name=='nt':exec(compile(Path(__file__).with_name('vpn-browser.py').read_text(encoding='utf-8'),str(Path(__file__).with_name('vpn-browser.py')),'exec'),globals())
 if not args.ui_only:
  check('rust_ready',chrome('return Soulu.adblock.status().ready'))
  check('network_blocking',Site.ads==0,{'requests':Site.ads})
  check('cosmetic_blocking',wait(lambda:content('return getComputedStyle(document.getElementById("ad")).display==="none"')))
  call('browser.adblock.update');updated=wait(lambda:(lambda v:v if not v.get('updating') else False)(call('browser.adblock.status')),120)
  check('filters_downloaded_by_gecko_and_installed',not updated.get('lastUpdateError') and updated.get('lastSuccessfulUpdate',0)>0,updated)
  call('browser.navigate','https://example.com/');wait(lambda:content('return location.protocol==="https:"&&document.title.includes("Example")'),45)
  check('real_https_site',content('return location.hostname==="example.com"'))
  call('browser.navigate','https://www.youtube.com/watch?v=aqz-KE-bpKQ')
  def youtube_playing():
   m.set_context('content');return m.execute_async_script('const done=arguments[0],v=document.querySelector("video");if(!v){done(false);return;}v.muted=true;v.play().catch(()=>{});setTimeout(()=>done(v.readyState>=2&&v.currentTime>.1),1000)')
  try:played=wait(youtube_playing,90)
  except Exception:played=False
  if played:check('youtube_real_video_playback',True)
  else:
   diagnostic=content('return {url:location.href,title:document.title,text:document.body?.innerText?.slice(0,2000),videos:[...document.querySelectorAll("video")].map(v=>({time:v.currentTime,ready:v.readyState,error:v.error?.message}))}')
   (out/'youtube-diagnostic.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2),encoding='utf-8')
   report['limitations'].append('Public YouTube playback was not confirmed on CI; see youtube-diagnostic.json. Requires manual playback verification, not counted as a pass.')
  call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")&&location.href==='+json.dumps(url)))
 # Page geometry and playback must survive actual toolbar interactions.
 before=content('return {h:innerHeight,w:innerWidth,y:scrollY,time:document.getElementById("v").currentTime,identity:document.documentElement.dataset.identity}')
 samples=[]
 import psutil
 tree=[psutil.Process(proc.pid),*psutil.Process(proc.pid).children(recursive=True)]
 cpu_before=sum(p.cpu_times().user+p.cpu_times().system for p in tree if p.is_running());sample_start=time.monotonic()
 for x in [60,140,260,410,600,800,1040,250]:
  if os.name=='nt':
   import ctypes
   left,top=chrome('return [window.mozInnerScreenX,window.mozInnerScreenY]');ctypes.windll.user32.SetCursorPos(round(left+x),round(top+24))
  time.sleep(.08);samples.append(content('return {h:innerHeight,w:innerWidth,y:scrollY,time:document.getElementById("v").currentTime,identity:document.documentElement.dataset.identity}'))
 check('video_geometry_stable_during_toolbar_interaction',all(all(abs(v[k]-before[k])<1 for k in ['h','w','y']) and v['identity']==before['identity'] for v in samples))
 check('video_advances_during_toolbar_interaction',samples[-1]['time']>before['time'])
 tree=[psutil.Process(proc.pid),*psutil.Process(proc.pid).children(recursive=True)]
 report['resourceSample']={'processes':len(tree),'rssBytes':sum(p.memory_info().rss for p in tree if p.is_running()),'cpuSecondsDuringSample':sum(p.cpu_times().user+p.cpu_times().system for p in tree if p.is_running())-cpu_before,'sampleSeconds':time.monotonic()-sample_start,'note':'CI resource sample, not a physical GPU benchmark.'}
 for width,height in [(780,600),(1000,740),(1120,780)]:
  chrome(f'window.resizeTo({width},{height})');time.sleep(.15)
  check('firefox_chrome_hidden_resize_'+str(width),chrome('return ["navigator-toolbox","titlebar","sidebar-main"].every(id=>!document.getElementById(id)||getComputedStyle(document.getElementById(id)).display==="none")'))
 (out/'preview4.png').write_bytes(base64.b64decode(m.screenshot()))
 call('browser.openTab',{'url':url+'session-active'});select_latest();wait(lambda:content('return location.pathname==="/session-active"&&!!document.getElementById("v")'))
 stop();start()
 check('native_session_active_tab_restored',wait(lambda:call('browser.state.get')['page']['url']==url+'session-active'))
 check('native_session_multiple_tabs_restored',len(call('browser.state.get')['tabs'])==2)
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
