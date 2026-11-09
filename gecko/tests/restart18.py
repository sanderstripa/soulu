"""Native Windows launches with no Marionette, WebDriver or testing environment."""
import ctypes as C,ctypes.wintypes as W,json,os,pathlib,subprocess,sys,tempfile,time,threading,http.server
import psutil,hashlib
from PIL import ImageGrab
base=pathlib.Path(sys.argv[1]).resolve();out=pathlib.Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True);baseline='--baseline' in sys.argv
report={'passed':False,'checks':{},'automation':False};user=C.windll.user32
user.IsWindowVisible.argtypes=[W.HWND];user.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int];user.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];user.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];user.SetForegroundWindow.argtypes=[W.HWND];C.windll.dwmapi.DwmGetWindowAttribute.argtypes=[W.HWND,W.DWORD,C.c_void_p,W.DWORD]
user.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)];user.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)]
user.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];user.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
def wait(fn,seconds=35):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  v=fn()
  if v:return v
  time.sleep(.1)
 raise AssertionError('Timed out waiting for '+getattr(fn,'__name__','state'))
def check(name,value,detail=None):
 report['checks'][name]={'passed':bool(value),'detail':detail};print(name,value,detail or '',flush=True)
 if not value:raise AssertionError(name)
def processes():
 rows=[]
 for p in psutil.process_iter(['pid','exe']):
  try:
   if p.info['exe'] and pathlib.Path(p.info['exe']).is_relative_to(base):rows.append(p)
  except (psutil.Error,OSError):pass
 return rows
def windows():
 found=[];pids={p.pid for p in processes()}
 @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
 def visit(hwnd,_):
  pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,C.byref(pid))
  if pid.value not in pids or not user.IsWindowVisible(hwnd):return True
  cloaked=W.DWORD();C.windll.dwmapi.DwmGetWindowAttribute(hwnd,14,C.byref(cloaked),4)
  if cloaked.value:return True
  title=C.create_unicode_buffer(1024);user.GetWindowTextW(hwnd,title,1024)
  cls=C.create_unicode_buffer(128);user.GetClassNameW(hwnd,cls,128)
  if cls.value=='MozillaWindowClass':found.append((hwnd,pid.value,title.value))
  return True
 user.EnumWindows(visit,0);return found
class Site(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  b=b'<!doctype html><title>Soulu restart fixture</title><h1>Soulu restart fixture</h1><input autofocus><script>setInterval(()=>localStorage.setItem("restart",Date.now()),500)</script>'
  self.send_response(200);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Site);threading.Thread(target=server.serve_forever,daemon=True).start()
root=pathlib.Path(tempfile.mkdtemp(prefix='soulu-native-restart-'));profile=root/'Soulu/Profiles/default';profile.mkdir(parents=True)
(profile/'soulu-settings.json').write_text(json.dumps({'settings':{'theme':'light','language':'ru','startupMode':'soulu','mattePanel':False},'onboarding':{'done':True,'step':6},'vpn':{'profiles':[]}}))
env=dict(os.environ,LOCALAPPDATA=str(root))
for key in ['MOZ_MARIONETTE','MOZ_REMOTE_ALLOW_SYSTEM_ACCESS','SOULU_GECKO_TEST']:env.pop(key,None)
# Reproduce the old existence-vs-ownership trap: the object exists, but no thread owns it.
mutex_name='Local\\Soulu.'+hashlib.sha256(str(profile).lower().encode()).hexdigest()[:32]
C.windll.kernel32.CreateMutexW.argtypes=[C.c_void_p,W.BOOL,W.LPCWSTR];C.windll.kernel32.CreateMutexW.restype=W.HANDLE
C.windll.kernel32.CloseHandle.argtypes=[W.HANDLE]
retained=C.windll.kernel32.CreateMutexW(None,False,mutex_name)
assert retained
try:
 for cycle in range(1,13):
  check('no_old_process_'+str(cycle),not processes())
  p=subprocess.Popen([str(base/'Soulu.exe'),'--url',f'http://127.0.0.1:{server.server_port}/'],env=env)
  def ready():return next((w for w in windows() if 'Soulu restart fixture' in w[2]),None)
  hwnd,pid,title=wait(ready,45);time.sleep(25 if cycle==1 else 3)
  check('visible_window_'+str(cycle),len(windows())==1,{'pid':pid,'title':title})
  if cycle==1:
   remote=profile/'soulu-remote.json';saved_remote=remote.read_bytes();remote.write_text('{}')
   fallback=subprocess.Popen([str(base/'Soulu.exe')],env=env);fallback.wait(timeout=10)
   check('native_focus_without_loopback',len(windows())==1 and windows()[0][1]==pid and fallback.returncode==0)
   remote.write_bytes(saved_remote)
   # A second shortcut click while running must focus the existing real window.
   second=subprocess.Popen([str(base/'Soulu.exe')],env=env);second.wait(timeout=15);check('existing_window_forwarded',len(windows())==1)
  ImageGrab.grab().save(out/f'launch-{cycle}.png')
  if cycle==8:
   p.kill()
   p.wait(timeout=10)
   check('abrupt_launcher_exit',True)
  elif cycle%2:
   user.PostMessageW(W.HWND(hwnd),0x0010,0,0)
  else:
   # Real pointer click on Soulu's top-right close control, not driver shutdown.
   rect=W.RECT();user.GetClientRect(W.HWND(hwnd),C.byref(rect));point=W.POINT(rect.right-40,28);user.ClientToScreen(W.HWND(hwnd),C.byref(point));user.SetForegroundWindow(W.HWND(hwnd));user.SetCursorPos(point.x,point.y);user.mouse_event(2,0,0,0,0);user.mouse_event(4,0,0,0,0)
  if cycle==2:
   # Click while the old browser is closing: never wait for its process exit first.
   wait(lambda:not windows(),10)
   wave=[subprocess.Popen([str(base/'Soulu.exe')],env=env) for _ in range(50)]
   wait(lambda:bool(windows()) and windows()[0][1]!=pid,45)
   wait(lambda:sum(p.poll() is None for p in wave)==1,45)
   check('fifty_clicks_during_close_open_one_window',len(windows())==1)
   check('fifty_clicks_leave_one_session_owner',sum(p.poll() is None for p in wave)==1)
   ImageGrab.grab().save(out/'fifty-clicks.png')
   user.PostMessageW(W.HWND(windows()[0][0]),0x0010,0,0)
  wait(lambda:not processes(),30);check('all_processes_exit_'+str(cycle),not processes())
 check('same_profile_preserved',bool(json.loads((profile/'soulu-settings.json').read_text())['onboarding']['done']))
 report['passed']=True
except Exception as e:
 report['error']=str(e);report['remaining']=[{'pid':p.pid,'exe':p.exe()} for p in processes()];report['windows']=windows();ImageGrab.grab().save(out/'failure.png')
 if not baseline:raise
finally:
 C.windll.kernel32.CloseHandle(retained)
 if (profile/'soulu-launcher.log').exists():(out/'soulu-launcher.log').write_bytes((profile/'soulu-launcher.log').read_bytes())
 (out/'restart18.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));server.shutdown()
 # Only test-owned processes, after recording a failure; never part of product recovery.
 for p in processes():
  try:p.kill()
  except psutil.Error:pass
