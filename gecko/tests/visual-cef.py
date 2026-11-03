"""Compare actual released CEF and actual Gecko, not mocked frontend renders."""
import base64,ctypes as C,importlib.util,json,os,pathlib,socket,subprocess,sys,tempfile,time,urllib.request,zipfile,hashlib
from ctypes import wintypes as W
from PIL import ImageGrab,Image,ImageChops,ImageStat,ImageDraw
from marionette_driver.marionette import Marionette
root=pathlib.Path(__file__).resolve().parents[2];binary=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
if os.name!='nt':raise RuntimeError('This acceptance requires Windows')
u=C.windll.user32;u.SetProcessDpiAwarenessContext(C.c_void_p(-4));u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)];u.MoveWindow.argtypes=[W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.BOOL];u.ShowWindow.argtypes=[W.HWND,C.c_int];u.SetForegroundWindow.argtypes=[W.HWND]
width,height=940,640;report={'passed':False,'reference':'Published Soulu CEF beta-1.0.76','clientSize':[width,height],'comparisons':[]};temp=pathlib.Path(tempfile.mkdtemp(prefix='soulu-visual-'))
def wait(fn,timeout=45):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   value=fn()
   if value:return value
  except Exception as e:last=e
  time.sleep(.2)
 raise AssertionError('Timeout: '+str(last))
def window_for(pid,cls):
 import psutil
 found=[];callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
 @callback
 def each(hwnd,_):
  name=C.create_unicode_buffer(128);u.GetClassNameW(hwnd,name,128);p=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(p))
  if name.value==cls and u.IsWindowVisible(hwnd):
   try:
    if p.value==pid or pid in [x.pid for x in psutil.Process(p.value).parents()]:found.append(hwnd)
   except psutil.Error:pass
  return True
 u.EnumWindows(each,0);return found[0] if found else None
def size(hwnd):
 u.ShowWindow(hwnd,9);r=W.RECT();c=W.RECT();u.GetWindowRect(hwnd,C.byref(r));u.GetClientRect(hwnd,C.byref(c));u.MoveWindow(hwnd,40,30,width+(r.right-r.left)-(c.right-c.left),height+(r.bottom-r.top)-(c.bottom-c.top),True);u.SetForegroundWindow(hwnd);time.sleep(.5)
 c=W.RECT();u.GetClientRect(hwnd,C.byref(c));assert [c.right,c.bottom]==[width,height],[c.right,c.bottom]
def grab(hwnd,path):
 u.SetForegroundWindow(hwnd);u.SetCursorPos(0,0);time.sleep(.5);p=W.POINT(0,0);u.ClientToScreen(hwnd,C.byref(p));ImageGrab.grab().crop((p.x,p.y,p.x+width,p.y+height)).save(path)
metric="""(async()=>{await document.fonts.ready;document.activeElement?.blur();return Object.fromEntries(['.classic-toolbar','.classic-main-row','#classicAddressForm','#sidebarButton','#vpnButton','#newTabButton','#windowMinimize','#windowMaximize','#windowClose','.tabs-zone'].map(s=>{const n=document.querySelector(s),r=n.getBoundingClientRect();return [s,{x:r.x,y:r.y,width:r.width,height:r.height}]}))})()"""
settingsMetric="""(async()=>{await document.fonts.ready;document.activeElement?.blur();return Object.fromEntries(['.settings-shell','#settingsTitle','#settingsSearch','#closeSettings','#homeCards'].map(s=>{const r=document.querySelector(s).getBoundingClientRect();return [s,{x:r.x,y:r.y,width:r.width,height:r.height}]}))})()"""
refroot=root/'gecko-cache/cef-reference';refroot.mkdir(parents=True,exist_ok=True)
release=json.load(urllib.request.urlopen('https://api.github.com/repos/sanderstripa/soulu/releases/tags/beta-1.0.76',timeout=30));asset=next(a for a in release['assets'] if a['name'].endswith('.zip'));archive=refroot/'reference.zip'
if not archive.exists():
 with urllib.request.urlopen(asset['browser_download_url'],timeout=180) as response,archive.open('wb') as f:
  import shutil;shutil.copyfileobj(response,f)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();assert asset.get('digest')=='sha256:'+digest,'CEF reference digest mismatch';report['referenceSHA256']=digest
with zipfile.ZipFile(archive) as z:
 assert all('..' not in pathlib.PurePosixPath(n).parts for n in z.namelist());z.extractall(refroot/'expanded')
cef=next(p for p in (refroot/'expanded').rglob('*.exe') if p.name.lower() in ['soulu.exe','soulucef.exe']);report['referenceBinary']=cef.name
spec=importlib.util.spec_from_file_location('cefui',root/'scripts/test-cef-ui.py');cefui=importlib.util.module_from_spec(spec);spec.loader.exec_module(cefui)
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
cefui.PORT=port;cefui.BASE=f'http://127.0.0.1:{port}'
env=dict(os.environ,LOCALAPPDATA=str(temp/'cef-data'),SOULU_UI_TEST_PORT=str(port),SOULU_REGRESSION_SKIP_FIRST_RUN='1',NO_PROXY='localhost,127.0.0.1,::1');proc=subprocess.Popen([str(cef),'--no-proxy-server'],env=env)
reference={};gecko={};m=None
try:
 shell=cefui.find_target('/ui/index.html',60);hwnd=wait(lambda:window_for(proc.pid,'SouluBrowserWindow'));size(hwnd)
 def cefcall(method,value=None):return cefui.evaluate(shell,'browserShell.'+method+'('+('' if value is None else json.dumps(value))+')')
 cefcall('setSettings',{'layout':'adaptive','theme':'light','mattePanel':False,'startupMode':'soulu','homeMode':'soulu','newTabMode':'soulu','showHome':False,'bookmarksBarPosition':'hidden','homeWeatherMode':'configured','homeWeatherCity':''});cefcall('goHome');home=cefui.find_target('home.html');wait(lambda:cefui.evaluate(home,'!!window.souluHomeApply && document.getElementById("providerIcon").naturalWidth>0'));time.sleep(.7)
 for name,theme,multiple,settings in [('home-single-light','light',False,False),('home-multi-dark','dark',True,False),('settings-dark','dark',False,True)]:
  cefcall('setSettings',{'theme':theme});
  if multiple:cefcall('newTab');time.sleep(.5)
  if settings:
   cefcall('openSettingsWindow');setting=cefui.find_target('settings.html');wait(lambda:cefui.evaluate(setting,'!!window.souluSettings?.current'));time.sleep(.5);reference[name]=cefui.evaluate(setting,settingsMetric)
  else:cefui.evaluate(home,'document.activeElement?.blur()');reference[name]=cefui.evaluate(shell,metric)
  time.sleep(.5);grab(hwnd,out/(name+'-cef.png'))
finally:
 try:cefcall('close')
 except:proc.terminate()
 try:proc.wait(timeout=20)
 except:proc.kill();proc.wait()
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
profile=temp/'gecko-data/Profiles/default';profile.mkdir(parents=True);(profile/'user.js').write_text('user_pref("marionette.port",'+str(port)+');')
env=dict(os.environ,SOULU_GECKO_TEST='1',MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1');log=open(out/'visual-runtime.log','w');proc=subprocess.Popen([str(binary),'-no-remote','-profile',str(profile),'-marionette'],env=env,stdout=log,stderr=log)
try:
 def ready():
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):return True
  except OSError:return False
 wait(ready,60);m=Marionette('127.0.0.1',port=port,socket_timeout=40);m.start_session();m.set_context('chrome');m.timeout.script=60
 def run(code):
  value=m.execute_async_script('const done=arguments[0];(async()=>{'+code+'})().then(done,e=>done({error:String(e)}));');assert not isinstance(value,dict) or 'error' not in value,value;return value
 def call(action,payload=None):return run('return Soulu.dispatch('+json.dumps(action)+','+json.dumps(payload)+');')
 def ui(expression,target='shell'):
  browser='gBrowser.selectedBrowser' if target=='home' else 'document.getElementById("soulu-'+target+'-frame")';return run('return '+browser+'.browsingContext.currentWindowGlobal.getActor("SouluApp").sendQuery("testing",'+json.dumps('return await '+expression+';')+');')
 wait(lambda:m.execute_script('return !!window.Soulu?.ready'));wait(lambda:ui('Promise.resolve(!!window.browserShell)'));hwnd=wait(lambda:window_for(proc.pid,'MozillaWindowClass'));size(hwnd)
 call('browser.settings.set',{'theme':'light','mattePanel':False,'startupMode':'soulu','homeMode':'soulu','newTabMode':'soulu','showHome':False,'bookmarksBarPosition':'hidden','homeWeatherMode':'configured','homeWeatherCity':''});wait(lambda:ui('Promise.resolve(document.getElementById("providerIcon").naturalWidth>0)','home'))
 for name,theme,multiple,settings in [('home-single-light','light',False,False),('home-multi-dark','dark',True,False),('settings-dark','dark',False,True)]:
  call('browser.settings.set',{'theme':theme});
  if multiple:call('browser.newTab');time.sleep(.5)
  if settings:
   call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady']);time.sleep(.5);gecko[name]=ui(settingsMetric,'settings')
  else:ui('Promise.resolve(document.activeElement?.blur())','home');gecko[name]=ui(metric)
  time.sleep(.5);grab(hwnd,out/(name+'-gecko.png'))
 for name in reference:
  deltas={s:max(abs(reference[name][s][k]-gecko[name][s][k]) for k in ['x','y','width','height']) for s in reference[name]};a=Image.open(out/(name+'-cef.png')).convert('RGB');b=Image.open(out/(name+'-gecko.png')).convert('RGB');diff=ImageChops.difference(a,b);diff.save(out/(name+'-difference.png'));area=(8,0,width-8,88) if name!='settings-dark' else (0,0,width,height);mean=sum(ImageStat.Stat(diff.crop(area)).mean)/3
  item={'name':name,'geometryMaxDelta':max(deltas.values()),'geometryDeltas':deltas,'meanRGBDifference':mean,'reference':reference[name],'gecko':gecko[name]};report['comparisons'].append(item)
  montage=Image.new('RGB',(width*2,height+28),'#ddd');montage.paste(a,(0,28));montage.paste(b,(width,28));draw=ImageDraw.Draw(montage);draw.text((8,8),'Soulu CEF 1.0.76',fill='black');draw.text((width+8,8),'Soulu Gecko Preview 2',fill='black');montage.save(out/(name+'-comparison.png'))
  print(name,json.dumps({'geometryMaxDelta':item['geometryMaxDelta'],'meanRGBDifference':mean}),flush=True)
  assert item['geometryMaxDelta']<=3,'Original frontend geometry differs: '+json.dumps(item)
  assert mean<22,'Screenshot difference needs review: '+json.dumps(item)
 report['passed']=True
finally:
 if m:
  try:m.quit()
  except:proc.terminate()
 try:proc.wait(timeout=20)
 except:proc.kill();proc.wait()
 log.close();(out/'visual-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
