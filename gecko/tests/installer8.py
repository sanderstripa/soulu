"""Real CEF-style installer UI: install, launch, upgrade, uninstall, and preserved data."""
import base64,contextlib,ctypes as C,json,os,pathlib,socket,sqlite3,subprocess,sys,tempfile,time,urllib.request,winreg
import websocket
from marionette_driver.marionette import Marionette
exe=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
report={'passed':False,'checks':{}};serial=0;opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def check(name,value,detail=None):
 report['checks'][name]={'passed':bool(value),'detail':detail};print(name,bool(value),detail or '',flush=True)
 if not value:raise AssertionError(name+': '+str(detail))
def wait(fn,timeout=45):
 end=time.monotonic()+timeout;error=None
 while time.monotonic()<end:
  try:
   value=fn()
   if value:return value
  except Exception as e:error=e
  time.sleep(.1)
 raise AssertionError('Timeout: '+str(error))
def proxy_snapshot():
 values={}
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
  for name in ['ProxyEnable','ProxyServer','ProxyOverride','AutoConfigURL']:
   try:values[name]=winreg.QueryValueEx(key,name)
   except FileNotFoundError:values[name]=None
 return values
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def command(ws,method,params=None):
 global serial
 serial+=1;ident=serial;ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
 while True:
  msg=json.loads(ws.recv())
  if msg.get('id')==ident:
   if 'error' in msg:raise RuntimeError(msg['error'])
   return msg.get('result',{})
def evaluate(ws,expression):
 r=command(ws,'Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
 if r.get('exceptionDetails'):raise RuntimeError(r['exceptionDetails'])
 return r.get('result',{}).get('value')
@contextlib.contextmanager
def debug_policy(binary,arguments):
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 path=r'SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments';access=winreg.KEY_READ|winreg.KEY_WRITE|winreg.KEY_WOW64_64KEY
 with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,path,0,access) as key:
  try:previous=winreg.QueryValueEx(key,binary.name)
  except FileNotFoundError:previous=None
  try:winreg.SetValueEx(key,binary.name,0,winreg.REG_SZ,arguments);yield
  finally:
   if previous is None:winreg.DeleteValue(key,binary.name)
   else:winreg.SetValueEx(key,binary.name,0,previous[1],previous[0])
@contextlib.contextmanager
def setup(binary,environment,uninstall=False):
 p=port();arguments=f'--remote-debugging-port={p} --remote-allow-origins=*';ws=None;process=None
 with debug_policy(binary,arguments):
  process=subprocess.Popen([str(binary),*(['--uninstall'] if uninstall else [])],env=dict(environment,WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=arguments))
  def connect():
   nonlocal ws
   with opener.open(f'http://127.0.0.1:{p}/json/list',timeout=2) as r:targets=json.load(r)
   for target in targets:
    if target.get('type')!='page' or not target.get('webSocketDebuggerUrl'):continue
    candidate=websocket.create_connection(target['webSocketDebuggerUrl'],timeout=15,suppress_origin=True)
    if evaluate(candidate,'!!document.getElementById("version")&&!!window.setupConfig'):
     ws=candidate;return True
    candidate.close()
   return False
  try:wait(connect,60);yield ws,process
  finally:
   if ws:
    try:command(ws,'Page.close')
    except Exception:pass
    ws.close()
   if process:
    try:process.wait(timeout=15)
    except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
def capture(ws,name):
 data=command(ws,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/name).write_bytes(base64.b64decode(data['data']))
def version(ws,stage):
 value=evaluate(ws,'document.getElementById("version").textContent');check('version_visible_'+stage,'0.8.0-preview8' in value and evaluate(ws,'document.getElementById("version").getBoundingClientRect().height>0'),value)
try:
 with tempfile.TemporaryDirectory(prefix='Soulu Gecko installer acceptance ') as temporary:
  root=pathlib.Path(temporary);local=root/'userdata';profile=local/'SouluGecko/Profiles/default';profile.mkdir(parents=True);mp=port()
  (profile/'user.js').write_text(f'user_pref("remote.prefs.recommended",false);user_pref("marionette.port",{mp});',encoding='utf-8')
  env=dict(os.environ,LOCALAPPDATA=str(local),WEBVIEW2_USER_DATA_FOLDER=str(root/'installer-webview'),MOZ_MARIONETTE='1',MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1',SOULU_GECKO_TEST='1')
  destination=local/'Programs/SouluGecko';original_proxy=proxy_snapshot()
  with setup(exe,env) as (ws,process):
   version(ws,'welcome');capture(ws,'installer-welcome.png');check('default_installation_is_separate_gecko_folder',evaluate(ws,'document.getElementById("path").value')==str(destination))
   evaluate(ws,'document.getElementById("settingsButton").click();document.getElementById("ru").click();document.getElementById("dark").click();true');version(ws,'settings');capture(ws,'installer-settings.png')
   evaluate(ws,'document.getElementById("accept").click();true');wait(lambda:evaluate(ws,'document.body.dataset.stage==="installing"'));version(ws,'installing');capture(ws,'installer-progress.png')
   wait(lambda:evaluate(ws,'document.body.dataset.stage==="finish"'),120);version(ws,'finish');capture(ws,'installer-finish.png')
   check('installed_runtime_and_uninstaller_exist',(destination/'Soulu.exe').is_file() and (destination/'runtime/xul.dll').is_file() and (destination/'Uninstall Soulu Gecko.exe').is_file())
   check('installer_does_not_change_system_proxy',proxy_snapshot()==original_proxy)
   evaluate(ws,'document.getElementById("launch").checked=true;document.getElementById("done").click();true');process.wait(timeout=20)
  def listening():
   with socket.create_connection(('127.0.0.1',mp),timeout=.2):return True
  wait(listening,60);m=Marionette('127.0.0.1',port=mp);m.start_session();m.set_context('chrome');m.timeout.script=60
  wait(lambda:m.execute_script('return !!window.Soulu?.ready&&!window.__souluStartupHidden&&document.documentElement.hasAttribute("soulu-ui-ready")'))
  check('first_installed_launch_uses_own_runtime',pathlib.Path(m.execute_script('return Services.dirsvc.get("GreD",Ci.nsIFile).path')).resolve()==(destination/'runtime').resolve())
  check('first_installed_launch_has_one_browser_window',m.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].length')==1)
  check('installer_choices_apply_only_to_new_profile',m.execute_script('return Soulu.config.settings.theme==="dark"&&Soulu.config.settings.language==="ru"'))
  check('first_installed_launch_version_is_preview8',m.execute_script('return document.documentElement.getAttribute("soulu-version")')=='Soulu Gecko Preview 8')
  check('first_installed_launch_shows_soulu_welcome',m.execute_script('return gBrowser.selectedBrowser.currentURI.spec.endsWith("/onboarding.html")'))
  (out/'installed-first-launch.png').write_bytes(base64.b64decode(m.screenshot()))
  result=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{const {PlacesUtils}=ChromeUtils.importESModule("resource://gre/modules/PlacesUtils.sys.mjs");await PlacesUtils.bookmarks.insert({parentGuid:PlacesUtils.bookmarks.toolbarGuid,url:"https://example.org/preview8-persistence",title:"Preview 8 installer persistence"});Soulu.config.onboarding={done:true,step:6};await Soulu.backend.save();return true;})().then(done,e=>done({error:String(e)}));');check('real_bookmark_saved_before_upgrade',result is True)
  pid=m.execute_script('return Services.appinfo.processID');handle=int(m.execute_script('return String(window.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).nativeHandle)'),16);C.windll.user32.PostMessageW(C.c_void_p(handle),0x0010,0,0)
  def exited():
   import psutil
   return not psutil.pid_exists(pid)
  wait(exited,30);m=None
  with setup(exe,env) as (ws,process):
   version(ws,'upgrade');evaluate(ws,'document.getElementById("primary").click();true');wait(lambda:evaluate(ws,'document.body.dataset.stage==="finish"'),120);evaluate(ws,'document.getElementById("launch").checked=false;document.getElementById("done").click();true');process.wait(timeout=20)
  settings=json.loads((profile/'soulu-settings.json').read_text());check('upgrade_keeps_existing_profile_settings',settings['settings']['theme']=='dark' and settings['onboarding']['done'])
  with contextlib.closing(sqlite3.connect(profile/'places.sqlite')) as db:check('upgrade_keeps_real_bookmarks',db.execute('select count(*) from moz_bookmarks where title=?',('Preview 8 installer persistence',)).fetchone()[0]==1)
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Uninstall\SouluGecko') as key:check('windows_installed_apps_has_correct_version',winreg.QueryValueEx(key,'DisplayVersion')[0]=='0.8.0-preview8')
  uninstaller=destination/'Uninstall Soulu Gecko.exe'
  with setup(uninstaller,env,True) as (ws,process):
   version(ws,'uninstall');evaluate(ws,'document.getElementById("primary").click();true');wait(lambda:evaluate(ws,'document.body.dataset.stage==="finish"'),90);evaluate(ws,'document.getElementById("done").click();true');process.wait(timeout=20)
  check('uninstall_removes_application_but_preserves_profile',not (destination/'Soulu.exe').exists() and (profile/'soulu-settings.json').exists() and (profile/'places.sqlite').exists())
  report['passed']=True
except Exception as e:report['error']=str(e);raise
finally:(out/'installer8.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
