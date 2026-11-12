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
    if pathlib.Path(psutil.Process(pid.value).exe()).resolve()!=(destination/'engine/SouluEngine.exe').resolve():return True
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
def hover_text_action(ws, identifier, theme):
 point=evaluate(ws,'(()=>{const r=document.getElementById('+json.dumps(identifier)+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()')
 command(ws,'Input.dispatchMouseEvent',{'type':'mouseMoved',**point})
 check('text_action_has_no_hover_rectangle_'+identifier+'_'+theme,evaluate(ws,'getComputedStyle(document.getElementById('+json.dumps(identifier)+')).backgroundColor')=='rgba(0, 0, 0, 0)')
def presentation(ws, theme):
 check('installer_inter_loaded_'+theme, evaluate(ws,'(async()=>{const faces=await document.fonts.load("400 14px Inter");return faces.length>0&&document.fonts.check("400 14px Inter")&&getComputedStyle(document.body).fontFamily.startsWith("Inter");})()'))
 expected='rgb(252, 252, 253)' if theme=='light' else 'rgb(8, 9, 11)'
 check('installer_browser_accent_'+theme,evaluate(ws,'getComputedStyle(document.getElementById("primary")).backgroundColor')==('rgb(6, 113, 255)' if theme=='light' else 'rgb(227, 228, 223)'))
 check('installer_browser_palette_'+theme,evaluate(ws,'getComputedStyle(document.body).backgroundColor')==expected)
 check('installer_browser_caption_glyphs_'+theme,evaluate(ws,'document.querySelector("#minimize svg path").getAttribute("d")==="M4.5 12h15"&&document.querySelector("#close svg path").getAttribute("d")==="m4 4 8 8m0-8-8 8"'))
 check('installer_caption_centers_'+theme,evaluate(ws,'["minimize","close"].every(id=>{const b=document.getElementById(id).getBoundingClientRect(),g=document.querySelector("#"+id+" svg").getBoundingClientRect();return Math.abs((b.left+b.right-g.left-g.right)/2)<0.6&&Math.abs((b.top+b.bottom-g.top-g.bottom)/2)<0.6;})'))
def version(ws,stage):
 check('only_soulu_brand_'+stage,not evaluate(ws,'/firefox/i.test(document.body.innerText)'))
 value=evaluate(ws,'document.getElementById("version").textContent');check('version_visible_'+stage,'1.160.29' in value and evaluate(ws,'document.getElementById("version").getBoundingClientRect().height>0'),value)
try:
 with tempfile.TemporaryDirectory(prefix='Soulu installer acceptance ') as temporary:
  root=pathlib.Path(temporary);local=root/'userdata';profile=local/'Soulu/Profiles/default';legacy_profile=local/'Soul/Profiles/default';legacy_profile.mkdir(parents=True);mp=port()
  (legacy_profile/'user.js').write_text(f'user_pref("remote.prefs.recommended",false);user_pref("marionette.port",{mp});',encoding='utf-8')
  env=dict(os.environ,LOCALAPPDATA=str(local),WEBVIEW2_USER_DATA_FOLDER=str(root/'installer-webview'),MOZ_MARIONETTE='1',MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1',SOULU_GECKO_TEST='1')
  destination=local/'Programs/Soulu';original_proxy=proxy_snapshot()
  programs=pathlib.Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs';programs.mkdir(parents=True,exist_ok=True);stale=programs/'Firefox Private Browsing.lnk'
  fixture_script="$s=New-Object -ComObject WScript.Shell;$l=$s.CreateShortcut('"+str(stale).replace("'","''")+"');$l.TargetPath='"+str(local/'Programs/Soul/engine/private_browsing.exe').replace("'","''")+"';$l.Save()"
  subprocess.run(['powershell.exe','-NoProfile','-Command',fixture_script],check=True)
  foreign=programs/'Private Browsing (unrelated).lnk'
  foreign_script=fixture_script.replace(str(stale),str(foreign)).replace(str(local/'Programs/Soul/engine/private_browsing.exe'),str(root/'Other Browser/private_browsing.exe'))
  subprocess.run(['powershell.exe','-NoProfile','-Command',foreign_script],check=True)
  localized=[programs/'Приватный просмотр.lnk',programs/'Приватный просмотр (2).lnk']
  for index,link in enumerate(localized):
   ascii_link=programs/('fixture-private-'+str(index)+'.lnk')
   script="$s=New-Object -ComObject WScript.Shell;$l=$s.CreateShortcut('"+str(ascii_link).replace("'","''")+"');$l.TargetPath='"+str(local/'Programs/Soulu/engine/private_browsing.exe').replace("'","''")+"';$l.Arguments='-private-window';$l.Save()"
   subprocess.run(['powershell.exe','-NoProfile','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')],check=True)
   ascii_link.replace(link)


  # Reproduce Preview 8 uninstall leftovers from the user's failed installation.
  (destination/'engine/old/empty').mkdir(parents=True)
  (destination/'Uninstall Soulu.exe').write_bytes(b'legacy leftover')
  with setup(exe,env) as (ws,process):
   version(ws,'welcome');presentation(ws,'light');hover_text_action(ws,'settingsButton','light');capture(ws,'installer-welcome.png');check('default_installation_is_separate_gecko_folder',evaluate(ws,'document.getElementById("path").value')==str(destination))
   evaluate(ws,'document.getElementById("settingsButton").click();document.getElementById("ru").click();document.getElementById("dark").click();true');version(ws,'settings');presentation(ws,'dark');hover_text_action(ws,'back','dark');capture(ws,'installer-settings.png')
   evaluate(ws,'document.getElementById("accept").click();true');wait(lambda:evaluate(ws,'document.body.dataset.stage==="installing"'));version(ws,'installing');capture(ws,'installer-progress.png')
   wait(lambda:finished(ws),120);version(ws,'finish');capture(ws,'installer-finish.png')
   long_buffer=C.create_unicode_buffer(32768)
   C.windll.kernel32.GetLongPathNameW(str(destination/'Soulu.exe'),long_buffer,len(long_buffer))
   long_exe=long_buffer.value or str(destination/'Soulu.exe')
   icon_script="$shell=New-Object -ComObject WScript.Shell;$roots=@([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'));foreach($r in $roots){Get-ChildItem -LiteralPath $r -Filter Soulu.lnk -Recurse -ErrorAction SilentlyContinue|ForEach-Object{$link=$shell.CreateShortcut($_.FullName);if($link.TargetPath -eq '"+long_exe.replace("'","''")+"'){$link.IconLocation}}}"
   icon_output=subprocess.check_output(['powershell.exe','-NoProfile','-Command',icon_script],text=True)
   locations=[line.strip() for line in icon_output.splitlines() if line.strip()]
   check('desktop_and_start_links_use_fresh_icon',len(locations)>=2 and all('soulu-app-1.160.24.ico' in line for line in locations),locations)
   check('stale_firefox_private_shortcut_removed',not stale.exists())
   check('unrelated_private_shortcut_preserved',foreign.exists());foreign.unlink()
   for remaining in (p for p in localized if p.exists()):
    print("Unresolved fixture",remaining.name,remaining.read_bytes().hex(),flush=True)
    script="$l=(New-Object -ComObject WScript.Shell).CreateShortcut('"+str(remaining).replace("'","''")+"');Write-Output $l.TargetPath;Write-Output $l.Arguments"
    subprocess.run(['powershell.exe','-NoProfile','-EncodedCommand',base64.b64encode(script.encode('utf-16le')).decode('ascii')])
   check('both_localized_private_shortcuts_removed',not any(p.exists() for p in localized))
   check('preview12_profile_migrated',profile.exists() and not legacy_profile.exists())
   check('only_current_product_launchers_are_installed',sorted(p.name for p in destination.glob('*.exe'))==['Soulu.exe','Uninstall Soulu.exe'])
   check('installed_engine_and_uninstaller_exist',(destination/'Soulu.exe').is_file() and (destination/'engine/xul.dll').is_file() and (destination/'Uninstall Soulu.exe').is_file())
   check('installer_does_not_change_system_proxy',proxy_snapshot()==original_proxy)
   recording,recorder,observed=watch_launch(destination)
   evaluate(ws,'document.getElementById("launch").checked=true;document.getElementById("done").click();true');process.wait(timeout=20)
  def listening():
   with socket.create_connection(('127.0.0.1',mp),timeout=.2):return True
  wait(listening,60);m=Marionette('127.0.0.1',port=mp);m.start_session();m.set_context('chrome');m.timeout.script=60
  wait(lambda:m.execute_script('return !!window.Soulu?.ready&&!window.__souluStartupHidden&&document.documentElement.hasAttribute("soulu-ui-ready")'))
  time.sleep(.5);recording.set();recorder.join(timeout=5);(out/'launch-windows.json').write_text(json.dumps(observed,indent=2))
  check('no_visible_firefox_window_during_first_launch',bool(observed) and not any('firefox' in x['title'].lower() for x in observed))
  check('engine_application_identity_is_soul',m.execute_script('return Services.appinfo.name')=='Soulu')
  check('no_new_firefox_os_registration',firefox_registrations()==original_firefox)
  check('payload_has_no_firefox_installer_tools',not any(p.name.lower() in ['firefox.exe','private_browsing.exe','helper.exe','default-browser-agent.exe','maintenanceservice_installer.exe'] for p in destination.rglob('*.exe')))
  check('first_installed_launch_uses_own_engine',pathlib.Path(m.execute_script('return Services.dirsvc.get("GreD",Ci.nsIFile).path')).resolve()==(destination/'engine').resolve())
  check('no_pending_taskbar_style_after_presentation',m.execute_script('return !window.__souluStartupHidden&&!!window.__souluStartupPresentation.presentedAt'))
  check('first_installed_launch_has_one_browser_window',m.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].length')==1)
  check('installer_choices_apply_only_to_new_profile',m.execute_script('return Soulu.config.settings.theme==="dark"&&Soulu.config.settings.language==="ru"'))
  paths=m.execute_script('const out={};for(const key of ["UAppData","ULocalAppData","UpdRootD"]){out[key]=Services.dirsvc.get(key,Ci.nsIFile).path;}return out;')
  check('application_directories_belong_to_soulu',all('soulu' in p.lower() and 'mozilla' not in p.lower() and 'firefox' not in p.lower() for p in paths.values()),paths)
  check('runtime_really_is_160',m.execute_script('return Services.appinfo.platformVersion')=='160.0')
  check('windows_autostart_disabled',m.execute_script('return ["browser.startup.windowsLaunchOnLogin.defaultEnabled","browser.startup.windowsLaunchOnLogin.enabled","toolkit.winRegisterApplicationRestart"].every(p=>Services.prefs.prefIsLocked(p)&&Services.prefs.getBoolPref(p)===false)'))
  check('unicode_settings_encryption_roundtrip',m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{const old=structuredClone(Soulu.backend.shared.config.vpn);try{Soulu.backend.shared.config.vpn.directDomains="пример.рф\\n日本語.example";await Soulu.backend.save();const disk=await IOUtils.readJSON(PathUtils.join(PathUtils.profileDir,"soulu-settings.json"));const raw=Cc["@mozilla.org/security/sdr;1"].getService(Ci.nsISecretDecoderRing).decryptString(disk.vpn.protected);return JSON.parse(raw).directDomains==="пример.рф\\n日本語.example";}finally{Soulu.backend.shared.config.vpn=old;await Soulu.backend.save();}})().then(done,e=>done({error:String(e)}));') is True)

  check('default_toolbar',m.execute_script('const s=Soulu.config.settings;return s.layout==="adaptive"&&!s.mattePanel&&!s.showExtensions&&!s.showHome&&!s.vpnToolbarVisible'))
  check('first_installed_launch_version_is_preview22',m.execute_script('return document.documentElement.getAttribute("soulu-version")')=='Soulu Preview 1.160.29')
  check('first_installed_launch_shows_soulu_welcome',m.execute_script('return gBrowser.selectedBrowser.currentURI.spec.endsWith("/onboarding.html")'))
  check('semantic_release_order',m.execute_script('const make=v=>{const tag="soulu-preview-"+v,name="Soulu-"+v+"-Preview-x64.exe";return {draft:false,tag_name:tag,assets:[{id:1,name,size:1,digest:"sha256:"+"a".repeat(64),browser_download_url:"https://github.com/sanderstripa/soulu/releases/download/"+tag+"/"+name}]};};return Soulu.updateCandidate([make("1.160.29")])===null && Soulu.updateCandidate([make("1.160.21")])===null && Soulu.updateCandidate([make("1.160.30")])!==null && Soulu.updateCandidate([make("1.161.1")])!==null;'))
  (out/'installed-first-launch.png').write_bytes(base64.b64decode(m.screenshot()))
  result=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{const {PlacesUtils}=ChromeUtils.importESModule("resource://gre/modules/PlacesUtils.sys.mjs");await PlacesUtils.bookmarks.insert({parentGuid:PlacesUtils.bookmarks.toolbarGuid,url:"https://example.org/preview22-persistence",title:"Preview 17 installer persistence"});Soulu.config.onboarding={done:true,step:6};await Soulu.backend.save();return true;})().then(done,e=>done({error:String(e)}));');check('real_bookmark_saved_before_upgrade',result is True)
  # Verify actual shell-decoded desktop/Start/pinned shortcuts and native HWND.
  import importlib.util
  spec=importlib.util.spec_from_file_location('iconcheck',pathlib.Path(__file__).resolve().parents[2]/'scripts/verify-branding.py')
  iconcheck=importlib.util.module_from_spec(spec);spec.loader.exec_module(iconcheck)
  expected=iconcheck.verify_assets()
  for binary in [destination/'Soulu.exe',destination/'Uninstall Soulu.exe',*list((destination/'engine').glob('*.exe'))]:
   iconcheck.verify_binary(binary,expected)
  import ctypes as iconct
  handles=[]
  callback=iconct.WINFUNCTYPE(iconct.c_bool,iconct.c_void_p,iconct.c_void_p)
  @callback
  def find_icon_window(hwnd,param):
   pid=iconct.c_ulong();iconct.windll.user32.GetWindowThreadProcessId(iconct.c_void_p(hwnd),iconct.byref(pid))
   if iconct.windll.user32.IsWindowVisible(iconct.c_void_p(hwnd)):
    try:
     import psutil
     if pathlib.Path(psutil.Process(pid.value).exe()).resolve()==(destination/'engine/SouluEngine.exe').resolve():handles.append(hwnd)
    except (OSError,psutil.Error):pass
   return True
  iconct.windll.user32.EnumWindows(find_icon_window,0)
  check('native_icon_window_found',bool(handles))
  for hwnd in handles:iconcheck.verify_window(hwnd,expected)
  shell_script="[Environment]::GetFolderPath('Desktop');[Environment]::GetFolderPath('Programs');Join-Path $env:APPDATA 'Microsoft/Internet Explorer/Quick Launch/User Pinned/TaskBar'"
  icon_roots=subprocess.check_output(['powershell.exe','-NoProfile','-Command',shell_script],text=True).splitlines()
  shortcuts=[]
  for directory in icon_roots:
   if pathlib.Path(directory).is_dir():
    for shortcut in pathlib.Path(directory).rglob('Soulu*.lnk'):
     iconcheck.verify_shortcut(shortcut,expected);shortcuts.append(str(shortcut))
  check('shell_shortcuts_use_new_icon',len(shortcuts)>=2,shortcuts)
  check('all_installed_executable_icons_match_master',True)
  from toolbar19 import verify_toolbar
  verify_toolbar(m,check,wait)
  from about22 import verify_about
  verify_about(m,check,wait)
  from branding25 import verify_branding
  verify_branding(m,check,wait,out)
  from fullscreen26 import verify_fullscreen
  verify_fullscreen(m,check,wait,out)
  from home24 import verify_home
  verify_home(m,check,wait)
  m.execute_script('Soulu.dispatch("browser.newIncognito");return true;')
  private_window='[...Services.wm.getEnumerator("navigator:browser")].find(w=>w.Soulu?.ready && w.Soulu.backend.isPrivate)'
  check('incognito_uses_soulu_shell',wait(lambda:m.execute_script('const w='+private_window+';return !!w?.document.documentElement.hasAttribute("soulu-ui-ready")')))
  m.execute_script('const w='+private_window+';w.close();return true;')
  wait(lambda:m.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].length===1'))
  helper=m.execute_async_script('const done=arguments[arguments.length-1];Soulu.dispatch("browser.components.manage",{component:"xray",operation:"status"}).then(()=>done(!!Soulu.backend.shared.helper),e=>done({error:String(e)}));')
  check('native_vpn_helper_started_before_close',helper is True,helper)
  pid=m.execute_script('return Services.appinfo.processID')
  try:m.execute_script('Soulu.dispatch("window.close").catch(console.error);return true;')
  except Exception:pass

  def exited():
   import psutil
   return not psutil.pid_exists(pid)
  wait(exited,30);m=None
  reopened=subprocess.Popen([str(destination/'Soulu.exe')],env=env)
  wait(listening,60);again=Marionette('127.0.0.1',port=mp);again.start_session();again.set_context('chrome');again.timeout.script=60
  def live_reopened_window():
   for handle in again.window_handles:
    try:
     again.switch_to_window(handle);again.set_context('chrome')
     if again.execute_script('return !!window.Soulu?.ready&&Soulu.config.onboarding.done&&!window.__souluStartupHidden'):return True
    except Exception:pass
   return False
  check('launcher_reopens_after_normal_close',wait(live_reopened_window))
  check('logo_choice_survives_restart',again.execute_script('return Soulu.config.settings.homeShowLogo===false'))
  (out/'installed-reopened.png').write_bytes(base64.b64decode(again.screenshot()))
  again.execute_script('openTrustedLinkIn("about:addons","window",{});return true;')
  def manager_consolidated():
   if not live_reopened_window():return False
   return again.execute_script('const wins=[...Services.wm.getEnumerator("navigator:browser")].filter(w=>!w.closed);return wins.length===1&&[...gBrowser.tabs].some(t=>t.linkedBrowser.currentURI.spec==="about:addons");')
  try:check('automatic_extension_window_becomes_tab',wait(manager_consolidated,45))
  except Exception:
   print(again.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].map(w=>({closed:w.closed,ready:!!w.Soulu?.ready,hidden:!!w.__souluStartupHidden,error:w.__souluStartupPresentation?.error,input:w.Soulu?.backend?.shared.initialUserInput,owner:w.Soulu?.backend?.shared.initialWindow===w,tabs:[...w.gBrowser.tabs].map(t=>t.linkedBrowser.currentURI.spec)}))'),flush=True)
   raise
  windows=again.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].filter(w=>!w.closed).map(w=>({uri:w.document.documentURI,ready:!!w.Soulu?.ready,title:w.document.title,hidden:!!w.__souluStartupHidden,startupError:w.Soulu?.startupWindowError||null,startupMode:w.Soulu?.config.settings.startupMode,tabs:[...w.gBrowser.tabs].map(t=>t.linkedBrowser.currentURI.spec)}));');check('reopened_browser_has_one_window',len(windows)==1,windows)
  second_pid=again.execute_script('return Services.appinfo.processID');second_handle=int(again.execute_script('return String(window.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).nativeHandle)'),16);C.windll.user32.PostMessageW(C.c_void_p(second_handle),0x0010,0,0);reopened.wait(timeout=30)
  check('reopened_browser_process_exits_normally',wait(lambda:not psutil.pid_exists(second_pid),30))
  third=subprocess.Popen([str(destination/'Soulu.exe')],env=env);wait(listening,60);again=Marionette('127.0.0.1',port=mp);again.start_session();again.set_context('chrome');again.timeout.script=60
  check('third_launch_one_window',wait(live_reopened_window) and again.execute_script('return [...Services.wm.getEnumerator("navigator:browser")].filter(w=>!w.closed).length===1'))
  third_pid=again.execute_script('return Services.appinfo.processID');third_handle=int(again.execute_script('return String(window.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).nativeHandle)'),16);C.windll.user32.PostMessageW(C.c_void_p(third_handle),0x0010,0,0);third.wait(timeout=30);wait(lambda:not psutil.pid_exists(third_pid),30)
  # A partially removed install is still recognized by its ownership manifest.
  (destination/'Soulu.exe').unlink()
  with setup(exe,env) as (ws,process):
   version(ws,'upgrade');evaluate(ws,'document.getElementById("primary").click();true');wait(lambda:finished(ws),120);evaluate(ws,'document.getElementById("launch").checked=false;document.getElementById("done").click();true');process.wait(timeout=20)
  settings=json.loads((profile/'soulu-settings.json').read_text());check('upgrade_keeps_existing_profile_settings',settings['settings']['theme']=='dark' and settings['onboarding']['done'])
  with contextlib.closing(sqlite3.connect(profile/'places.sqlite')) as db:check('upgrade_keeps_real_bookmarks',db.execute('select count(*) from moz_bookmarks where title=?',('Preview 17 installer persistence',)).fetchone()[0]==1)
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Soulu') as key:check('windows_installed_apps_has_correct_version',winreg.QueryValueEx(key,'DisplayVersion')[0]=='1.160.29')
  subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('restart18.py')),str(destination),str(out)],check=True)
  uninstaller=destination/'Uninstall Soulu.exe'
  with setup(uninstaller,env,True) as (ws,process):
   version(ws,'uninstall');evaluate(ws,'document.getElementById("primary").click();true');wait(lambda:evaluate(ws,'document.body.dataset.stage==="finish"'),90);evaluate(ws,'document.getElementById("done").click();true');process.wait(timeout=20)
  check('uninstall_removes_application_but_preserves_profile',not (destination/'Soulu.exe').exists() and (profile/'soulu-settings.json').exists() and (profile/'places.sqlite').exists())
  check('uninstall_cleans_own_executable_and_empty_engine_tree',wait(lambda:not destination.exists(),20))
  report['passed']=True
except Exception as e:report['error']=str(e);raise
finally:(out/'installer26.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

