"""Real CEF-style installer UI: install, launch, upgrade, uninstall, and preserved data."""
import base64,contextlib,ctypes as C,json,os,pathlib,socket,sqlite3,subprocess,sys,tempfile,time,urllib.request,winreg
import websocket,threading,psutil
from PIL import ImageGrab
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
def firefox_registrations():
 result={}
 for hive,label in [(winreg.HKEY_CURRENT_USER,'user'),(winreg.HKEY_LOCAL_MACHINE,'machine')]:
  for path in [r'Software\Microsoft\Windows\CurrentVersion\Uninstall',r'Software\Clients\StartMenuInternet',r'Software\RegisteredApplications']:
   try:
    with winreg.OpenKey(hive,path) as k:
     index=0
     while True:
      try:
       if path.endswith('RegisteredApplications'):name,value,kind=winreg.EnumValue(k,index);entry=(name,str(value))
       else:
        name=winreg.EnumKey(k,index);entry=(name,)
        with winreg.OpenKey(k,name) as child:
         for field in ['DisplayName','InstallLocation','UninstallString']:
          try:entry+= (str(winreg.QueryValueEx(child,field)[0]),)
          except OSError:pass
       if any('firefox' in v.lower() for v in entry):result[label+path+name]=entry
       index+=1
      except OSError:break
   except OSError:pass
 return result
original_firefox=firefox_registrations()
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
def watch_launch(destination):
 stopped=threading.Event();observed=[]
 def record():
  index=0
  @C.WINFUNCTYPE(C.c_bool,C.c_void_p,C.c_void_p)
  def inspect(hwnd,_):
   nonlocal index
   if not C.windll.user32.IsWindowVisible(hwnd):return True
   pid=C.c_ulong();C.windll.user32.GetWindowThreadProcessId(hwnd,C.byref(pid))
   try:
    if pathlib.Path(psutil.Process(pid.value).exe()).resolve()!=(destination/'engine/SoulEngine.exe').resolve():return True
   except (OSError,psutil.Error):return True
   cloaked=C.c_int();C.windll.dwmapi.DwmGetWindowAttribute(hwnd,14,C.byref(cloaked),4)
   if cloaked.value:return True
   title=C.create_unicode_buffer(1024);C.windll.user32.GetWindowTextW(hwnd,title,1024)
   observed.append({'at':time.monotonic(),'title':title.value})
   if index<30:
    picture=ImageGrab.grab();picture.thumbnail((1000,700));picture.save(out/f'launch-frame-{index:02}.png');index+=1
   return True
  while not stopped.is_set():C.windll.user32.EnumWindows(inspect,0);stopped.wait(.1)
 thread=threading.Thread(target=record,daemon=True);thread.start()
 return stopped,thread,observed
def finished(ws):
 stage=evaluate(ws,'document.body.dataset.stage');
 if stage in ['error','failed']:
  capture(ws,'installer-error.png');raise RuntimeError(evaluate(ws,'document.body.innerText'))
 return stage=='finish'
def capture(ws,name):
 data=command(ws,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/name).write_bytes(base64.b64decode(data['data']))
def version(ws,stage):
 check('only_soulu_brand_'+stage,not evaluate(ws,'/firefox/i.test(document.body.innerText)'))
 value=evaluate(ws,'document.getElementById("version").textContent');check('version_visible_'+stage,'0.12.0-preview' in value and evaluate(ws,'document.getElementById("version").getBoundingClientRect().height>0'),value)
try:
 with tempfile.TemporaryDirectory(prefix='Soul installer acceptance ') as temporary:
  root=pathlib.Path(temporary);local=root/'userdata';profile=local/'Soul/Profiles/default';profile.mkdir(parents=True);mp=port()
  (profile/'user.js').write_text(f'user_pref("remote.prefs.recommended",false);user_pref("marionette.port",{mp});',encoding='utf-8')
  env=dict(os.environ,LOCALAPPDATA=str(local),WEBVIEW2_USER_DATA_FOLDER=str(root/'installer-webview'),MOZ_MARIONETTE='1',MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1',SOULU_GECKO_TEST='1')
  destination=local/'Programs/Soul';original_proxy=proxy_snapshot()
  # Reproduce Preview 8 uninstall leftovers from the user's failed installation.
  (destination/'engine/old/empty').mkdir(parents=True)
  (destination/'Uninstall Soul.exe').write_bytes(b'legacy leftover')
  with setup(exe,env) as (ws,process):
   version(ws,'welcome');capture(ws,'installer-welcome.png');check('default_installation_is_separate_gecko_folder',evaluate(ws,'document.getElementById("path").value')==str(destination))
   evaluate(ws,'document.getElementById("settingsButton").click();document.getElementById("ru").click();document.getElementById("dark").click();true');version(ws,'settings');capture(ws,'installer-settings.png')
   evaluate(ws,'document.getElementById("accept").click();true');wait(lambda:evaluate(ws,'document.body.dataset.stage==="installing"'));version(ws,'installing');capture(ws,'installer-progress.png')
   wait(lambda:finished(ws),120);version(ws,'finish');capture(ws,'installer-finish.png')
   check('only_current_product_launchers_are_installed',sorted(p.name for p in destination.glob('*.exe'))==['Soul.exe','Uninstall Soul.exe'])
   check('installed_engine_and_uninstaller_exist',(destination/'Soul.exe').is_file() and (destination/'engine/xul.dll').is_file() and (destination/'Uninstall Soul.exe').is_file())
   check('installer_does_not_change_system_proxy',proxy_snapshot()==original_proxy)
   recording,recorder,observed=watch_launch(destination)
   evaluate(ws,'document.getElementById("launch").checked=true;document.getElementById("done").click();true');process.wait(timeout=20)
  def listening():
   with socket.create_connection(('127.0.0.1',mp),timeout=.2):return True
  wait(listening,60);m=Marionette('127.0.0.1',port=mp);m.start_session();m.set_context('chrome');m.timeout.script=60
  wait(lambda:m.execute_script('return !!window.Soulu?.ready&&!window.__souluStartupHidden&&document.documentElement.hasAttribute("soulu-ui-ready")'))
  time.sleep(.5);recording.set();recorder.join(timeout=5);(out/'launch-windows.json').write_text(json.dumps(observed,indent=2))
  check('no_visible_firefox_window_during_first_launch',bool(observed) and not any('firefox' in x['title'].lower() for x in observed))
  check('engine_application_identity_is_soul',m.execute_script('return Services.appinfo.name')=='Soul')
  check('no_new_firefox_os_registration',firefox_registrations()==original_firefox)
  check('payload_has_no_firefox_installer_tools',not any(p.name.lower() in ['firefox.exe','helper.exe','default-browser-agent.exe','maintenanceservice_installer.exe'] for p in destination.rglob('*.exe')))
  check('first_installed_launch_uses_own_engine',pathlib.Path(m.execute_script('return Services.dirsvc.get("GreD",Ci.nsIFile).path')).resolve()==(destination/'engine').resolve())
  check('first_installed_launch_has_one_browser_window',m.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].length')==1)
  check('installer_choices_apply_only_to_new_profile',m.execute_script('return Soulu.config.settings.theme==="dark"&&Soulu.config.settings.language==="ru"'))
  check('first_installed_launch_version_is_preview12',m.execute_script('return document.documentElement.getAttribute("soulu-version")')=='Soul 0.12.0 Preview')
  check('first_installed_launch_shows_soulu_welcome',m.execute_script('return gBrowser.selectedBrowser.currentURI.spec.endsWith("/onboarding.html")'))
  (out/'installed-first-launch.png').write_bytes(base64.b64decode(m.screenshot()))
  result=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{const {PlacesUtils}=ChromeUtils.importESModule("resource://gre/modules/PlacesUtils.sys.mjs");await PlacesUtils.bookmarks.insert({parentGuid:PlacesUtils.bookmarks.toolbarGuid,url:"https://example.org/preview12-persistence",title:"Preview 11 installer persistence"});Soulu.config.onboarding={done:true,step:6};await Soulu.backend.save();return true;})().then(done,e=>done({error:String(e)}));');check('real_bookmark_saved_before_upgrade',result is True)
  pid=m.execute_script('return Services.appinfo.processID');handle=int(m.execute_script('return String(window.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).nativeHandle)'),16);C.windll.user32.PostMessageW(C.c_void_p(handle),0x0010,0,0)
  def exited():
   import psutil
   return not psutil.pid_exists(pid)
  wait(exited,30);m=None
  reopened=subprocess.Popen([str(destination/'Soul.exe')],env=env)
  wait(listening,60);again=Marionette('127.0.0.1',port=mp);again.start_session();again.set_context('chrome');again.timeout.script=60
  check('launcher_reopens_after_normal_close',wait(lambda:again.execute_script('return !!window.Soulu?.ready&&Soulu.config.onboarding.done&&!window.__souluStartupHidden')))
  windows=again.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].filter(w=>!w.closed).map(w=>({uri:w.document.documentURI,ready:!!w.Soulu?.ready,title:w.document.title,hidden:!!w.__souluStartupHidden,startupError:w.Soulu?.startupWindowError||null,startupMode:w.Soulu?.config.settings.startupMode,tabs:[...w.gBrowser.tabs].map(t=>t.linkedBrowser.currentURI.spec)}));');check('reopened_browser_has_one_window',len(windows)==1,windows)
  second_pid=again.execute_script('return Services.appinfo.processID');second_handle=int(again.execute_script('return String(window.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).nativeHandle)'),16);C.windll.user32.PostMessageW(C.c_void_p(second_handle),0x0010,0,0);reopened.wait(timeout=30)
  check('reopened_browser_process_exits_normally',wait(lambda:not psutil.pid_exists(second_pid),30))
  # A partially removed install is still recognized by its ownership manifest.
  (destination/'Soul.exe').unlink()
  with setup(exe,env) as (ws,process):
   version(ws,'upgrade');evaluate(ws,'document.getElementById("primary").click();true');wait(lambda:finished(ws),120);evaluate(ws,'document.getElementById("launch").checked=false;document.getElementById("done").click();true');process.wait(timeout=20)
  settings=json.loads((profile/'soulu-settings.json').read_text());check('upgrade_keeps_existing_profile_settings',settings['settings']['theme']=='dark' and settings['onboarding']['done'])
  with contextlib.closing(sqlite3.connect(profile/'places.sqlite')) as db:check('upgrade_keeps_real_bookmarks',db.execute('select count(*) from moz_bookmarks where title=?',('Preview 11 installer persistence',)).fetchone()[0]==1)
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Soul') as key:check('windows_installed_apps_has_correct_version',winreg.QueryValueEx(key,'DisplayVersion')[0]=='0.12.0-preview')
  uninstaller=destination/'Uninstall Soul.exe'
  with setup(uninstaller,env,True) as (ws,process):
   version(ws,'uninstall');evaluate(ws,'document.getElementById("primary").click();true');wait(lambda:evaluate(ws,'document.body.dataset.stage==="finish"'),90);evaluate(ws,'document.getElementById("done").click();true');process.wait(timeout=20)
  check('uninstall_removes_application_but_preserves_profile',not (destination/'Soul.exe').exists() and (profile/'soulu-settings.json').exists() and (profile/'places.sqlite').exists())
  check('uninstall_cleans_own_executable_and_empty_engine_tree',wait(lambda:not destination.exists(),20))
  report['passed']=True
except Exception as e:report['error']=str(e);raise
finally:(out/'installer12.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

