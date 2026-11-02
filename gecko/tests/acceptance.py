"""Exercise the actual packaged Gecko runtime, never a mock browser."""
import base64, http.server, json, os, pathlib, socket, subprocess, sys, tempfile, threading, time
from marionette_driver.marionette import Marionette
binary=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'gecko-acceptance');out.mkdir(parents=True,exist_ok=True)
root=pathlib.Path(tempfile.mkdtemp(prefix='soulu-gecko-'));profile=root/'Profiles/default';profile.mkdir(parents=True)
result={'platform':sys.platform,'checks':{},'limitations':[]}
if os.name!='nt':result['limitations'].append('Linux container UI checks use MOZ_DISABLE_CONTENT_SANDBOX=1 because user namespaces are unavailable. This is test environment only; production sandbox acceptance is Windows-only.')
class Page(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path.startswith('/ads/'):
   body=b'console.log("ad fixture")'
  else:body=b'<!doctype html><title>Soulu Gecko acceptance</title><style>body{margin:0}#marker{height:200px;background:#4683e8}</style><div id="marker">Gecko page</div><input id="text"><script src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>'
  self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Page);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
def check(name,condition,detail=None):
 result['checks'][name]={'passed':bool(condition),'detail':detail};print(name,condition,detail or '',flush=True)
 if not condition:raise AssertionError(name+': '+str(detail))
def start(via_launcher=False):
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 active_profile=(root/'launcher-data/SouluGecko/Profiles/launcher-check') if via_launcher else profile
 active_profile.mkdir(parents=True,exist_ok=True)
 (active_profile/'user.js').write_text('user_pref("marionette.port", '+str(port)+');\n')
 env=dict(os.environ,MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1')
 if os.name!='nt':env['MOZ_DISABLE_CONTENT_SANDBOX']='1'
 log=open(out/'runtime.log','a')
 if via_launcher:
  env['LOCALAPPDATA']=str(root/'launcher-data')
  command=[str(binary.parent.parent/'Soulu Gecko Preview 1.exe'),'--profile','launcher-check','-headless','-marionette']
 else:command=[str(binary),'-headless','-no-remote','-profile',str(profile),'-marionette']
 proc=subprocess.Popen(command,stdout=log,stderr=log,env=env)
 deadline=time.time()+60
 while time.time()<deadline:
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):break
  except OSError:
   if proc.poll() is not None:raise RuntimeError('Runtime exited: '+(out/'runtime.log').read_text())
   time.sleep(.2)
 m=Marionette('127.0.0.1',port=port,socket_timeout=30);m.start_session();m.set_context('chrome');m.timeout.script=30
 for _ in range(100):
  if m.execute_script('return !!window.Soulu?.ready'):return proc,m,log
  time.sleep(.1)
 raise AssertionError('Soulu chrome failed to initialize')
def stop(proc,m,log):
 try:m.quit()
 except Exception:proc.terminate()
 try:proc.wait(timeout=20)
 except subprocess.TimeoutExpired:proc.kill();proc.wait()
 log.close()
def run(m,script):return m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+script+'})().then(done,e=>done({TEST_ERROR:String(e),stack:e.stack}));')
proc=m=log=None
try:
 proc,m,log=start()
 check('native_gecko_startup',m.execute_script('return Services.appinfo.name==="Firefox" && !!window.Soulu.ready'))
 check('adaptive_single_tab',m.execute_script('return document.documentElement.hasAttribute("soulu-single")'))
 m.execute_script('BrowserCommands.openTab()');time.sleep(.3);m.switch_to_window(m.window_handles[-1]);m.set_context('chrome')
 check('adaptive_multiple_tabs',m.execute_script('return !document.documentElement.hasAttribute("soulu-single") && !document.getElementById("TabsToolbar").collapsed'))
 check('security_preferences',m.execute_script('return Services.prefs.getBoolPref("fission.autostart") && Services.prefs.getBoolPref("browser.safebrowsing.malware.enabled") && Services.prefs.getBoolPref("browser.safebrowsing.phishing.enabled") && Services.prefs.getIntPref("security.sandbox.content.level")>0'))
 addon=run(m,"const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');for(let i=0;i<100;i++){const a=await AddonManager.getAddonByID('uBlock0@raymondhill.net');if(a?.isActive)return {active:a.isActive,signed:a.signedState,version:a.version};await new Promise(r=>setTimeout(r,100));}return null;")
 check('signed_full_ublock_active',isinstance(addon,dict) and addon.get('active') and addon.get('signed',0)>0,addon)
 saved=run(m,"const c=await Soulu.dispatch('settings.begin');c.settings.theme='dark';c.settings.showHome=true;c.rules.defaults.camera=2;const r=await Soulu.dispatch('settings.save',c);return {ok:r.ok,error:r.error,theme:document.documentElement.hasAttribute('soulu-dark'),camera:Services.prefs.getIntPref('permissions.default.camera')};")
 check('settings_apply_and_permission_policy',saved.get('ok') and saved.get('theme') and saved.get('camera')==2,saved)
 blocked=run(m,"const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');let c=await Soulu.dispatch('settings.begin');c.rules.blocking.enabled=false;let r=await Soulu.dispatch('settings.save',c);if(!r.ok)return r;const disabled=(await AddonManager.getAddonByID('uBlock0@raymondhill.net')).userDisabled;c=await Soulu.dispatch('settings.begin');c.rules.blocking.enabled=true;r=await Soulu.dispatch('settings.save',c);return {ok:r.ok,disabled,enabled:!(await AddonManager.getAddonByID('uBlock0@raymondhill.net')).userDisabled};")
 check('adblock_toggle_controls_real_engine',blocked.get('ok') and blocked.get('disabled') and blocked.get('enabled'),blocked)

 if os.name=='nt':
  native=run(m,"const rows=[];for(const component of ['xray','sudoku'])rows.push(await Soulu.dispatch('browser.components.manage',{component,operation:'status'}));return rows;")
  check('bundled_vpn_helper_native_pipe',isinstance(native,list) and len(native)==2 and all(x.get('installed') for x in native),native)
  vpn=run(m,"const c=await Soulu.dispatch('settings.begin');c.vpn.profiles=[{id:'fixture',name:'Local fixture',link:'vless://12345678-1234-1234-1234-123456789abc@127.0.0.1:9?security=none&type=tcp',protocol:'vless',address:'127.0.0.1:9'}];c.vpn.defaultProfileId='fixture';await Soulu.dispatch('settings.save',c);const connected=await Soulu.dispatch('vpn.send',{action:'connect'});const routed=Services.prefs.getIntPref('network.proxy.type')===1&&!Services.prefs.getBoolPref('network.proxy.failover_direct')&&!Services.prefs.getBoolPref('media.peerconnection.enabled');await Soulu.dispatch('vpn.send',{action:'disconnect'});return {connected:connected.connected,routed,disconnected:Services.prefs.getIntPref('network.proxy.type')===0};")
  check('gecko_vpn_core_start_route_disconnect',vpn.get('connected') and vpn.get('routed') and vpn.get('disconnected'),vpn)

 m.execute_script('Soulu.settings()');time.sleep(.5)
 settings=run(m,"for(let i=0;i<100;i++){const w=[...Services.wm.getEnumerator(null)].find(w=>w.document.documentURI==='chrome://soulu/content/ui/settings.html');if(w?.souluSettings?.current){const ids=['general','interface','tabs','search','sites','vpn','reading','translation','extensions','performance','profiles','updates'];const errors=[];for(const id of ids){try{w.souluSettings.openSection(id);}catch(e){errors.push(id+':'+e);}}w.souluSettings.openSection('');return {sections:w.document.querySelectorAll('#homeCards button').length,errors};}await new Promise(r=>setTimeout(r,100));}return null;")
 check('soulu_settings_sections',isinstance(settings,dict) and not settings.get('errors') and settings.get('sections',0)>=12,settings)
 m.execute_script('for(const w of Services.wm.getEnumerator(null))if(w.document.documentURI.includes("soulu/content/ui/settings.html"))w.close()')
 m.set_context('content');m.navigate(url);time.sleep(.5)
 check('website_has_no_privileged_bridge',m.execute_script('return !window.Soulu && !window.cefQuery && !window.browserShell && document.getElementById("marker").getBoundingClientRect().top===0'))
 m.set_context('chrome')
 geometry=m.execute_script('return {remote:gBrowser.selectedBrowser.isRemoteBrowser,type:gBrowser.selectedBrowser.remoteType,rect:gBrowser.selectedBrowser.getBoundingClientRect().toJSON(),tabs:document.getElementById("TabsToolbar").getBoundingClientRect().toJSON()}')
 check('remote_web_content',geometry['remote'] and str(geometry['type']).startswith('web'),geometry)
 before=geometry['rect']
 m.execute_script('for(let i=0;i<100;i++){for(const id of ["soulu-vpn","back-button","soulu-newtab"]){const n=document.getElementById(id);n.dispatchEvent(new MouseEvent("mouseover",{bubbles:true}));n.dispatchEvent(new MouseEvent("mouseout",{bubbles:true}));}}');time.sleep(.3)
 after=m.execute_script('return gBrowser.selectedBrowser.getBoundingClientRect().toJSON()')
 check('hover_keeps_page_geometry',before==after,{'before':before,'after':after})
 (out/'browser.png').write_bytes(base64.b64decode(m.screenshot()))
 history=run(m,"const {PlacesUtils}=ChromeUtils.importESModule('resource://gre/modules/PlacesUtils.sys.mjs');const entry=await PlacesUtils.history.fetch('"+url+"',{includeVisits:true});const b=await PlacesUtils.bookmarks.insert({parentGuid:PlacesUtils.bookmarks.toolbarGuid,url:'"+url+"',title:'Gecko bookmark'});return {visits:entry?.visits?.length||0,bookmarks:(await Soulu.dispatch('browser.bookmarks.get')).some(r=>r.id===b.guid)};")
 check('history_and_bookmarks',history.get('visits',0)>0 and history.get('bookmarks'),history)
 profiles=run(m,"const p=await Soulu.dispatch('browser.profile.create','Acceptance profile');const list=await Soulu.dispatch('browser.state.get');return {created:p.id,found:list.profiles.some(r=>r.id===p.id&&!r.active),current:list.activeProfileId};")
 check('independent_profile_directory',profiles.get('found') and profiles.get('created')!=profiles.get('current'),profiles)
 private=run(m,"const prior=Soulu.config;OpenBrowserWindow({private:true});for(let i=0;i<100;i++){const w=[...Services.wm.getEnumerator('navigator:browser')].find(w=>w!==window);if(w?.Soulu?.ready){const {PrivateBrowsingUtils}=ChromeUtils.importESModule('resource://gre/modules/PrivateBrowsingUtils.sys.mjs');const result={private:PrivateBrowsingUtils.isWindowPrivate(w),sameConfig:w.Soulu.config===prior};w.close();return result;}await new Promise(r=>setTimeout(r,100));}return null;")
 check('private_window_and_shared_process_state',isinstance(private,dict) and private.get('private') and private.get('sameConfig'),private)
 stop(proc,m,log);proc=m=log=None
 proc,m,log=start()
 check('settings_persist_after_restart',m.execute_script('return Soulu.config.settings.theme==="dark" && Soulu.config.settings.showHome && Soulu.config.rules.defaults.camera===2 && Services.prefs.getIntPref("permissions.default.camera")===2'))
 check('bookmarks_persist_after_restart',run(m,"return (await Soulu.dispatch('browser.bookmarks.get')).some(r=>r.title==='Gecko bookmark');") is True)

 if os.name=='nt':
  stop(proc,m,log);proc=m=log=None
  proc,m,log=start(via_launcher=True)
  location=m.execute_script('return {profile:PathUtils.profileDir,id:Soulu.config.profile,sandbox:Services.prefs.getIntPref("security.sandbox.content.level")}')
  check('portable_launcher_and_isolated_profile',location.get('id')=='launcher-check' and 'SouluGecko' in location.get('profile','') and location.get('sandbox',0)>0 and proc.poll() is None,location)
 result['passed']=True
finally:
 if proc:stop(proc,m,log)
 server.shutdown();(out/'acceptance.json').write_text(json.dumps(result,indent=2))
