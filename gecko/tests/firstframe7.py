"""Observe the actual first visible HWND, independent of WebDriver attach latency."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{},'visibleFrames':[]};done=threading.Event()
import ctypes as C
import psutil
from ctypes import wintypes as W
from PIL import ImageGrab,ImageStat
u=C.windll.user32;u.SetProcessDpiAwarenessContext(C.c_void_p(-4));u.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];u.FindWindowW.restype=W.HWND;u.IsWindowVisible.argtypes=[W.HWND];u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)]
dwm=C.windll.dwmapi;dwm.DwmGetWindowAttribute.argtypes=[W.HWND,W.DWORD,C.c_void_p,W.DWORD]
u.WindowFromPoint.argtypes=[W.POINT];u.WindowFromPoint.restype=W.HWND;u.GetAncestor.argtypes=[W.HWND,W.UINT];u.GetAncestor.restype=W.HWND
report['surfaceObservations']=[]
started=time.monotonic()
def observe():
 while not done.is_set() and time.monotonic()-started<12 and len(report['visibleFrames'])<12:
  try:
   hwnd=u.FindWindowW('MozillaWindowClass',None);pid=W.DWORD()
   cloaked=W.DWORD()
   dwmResult=dwm.DwmGetWindowAttribute(hwnd,14,C.byref(cloaked),C.sizeof(cloaked)) if hwnd else None
   if hwnd and u.IsWindowVisible(hwnd) and not cloaked.value:
    u.GetWindowThreadProcessId(hwnd,C.byref(pid))
    if proc and pathlib.Path(psutil.Process(pid.value).exe()).resolve()==binary:
     r=W.RECT();p=W.POINT();u.GetClientRect(hwnd,C.byref(r));u.ClientToScreen(hwnd,C.byref(p))
     if r.right>500 and r.bottom>100:
      hit=u.WindowFromPoint(W.POINT(p.x+r.right//2,p.y+30));surface=u.GetAncestor(hit,2) if hit else 0
      report['surfaceObservations'].append({'seconds':round(time.monotonic()-started,3),'hwnd':int(hwnd),'screenRoot':int(surface or 0),'dwmResult':dwmResult,'cloaked':cloaked.value})
      if surface!=hwnd:
       done.wait(.04);continue
      frame=ImageGrab.grab(all_screens=True).crop((p.x,p.y,p.x+r.right,p.y+68));name='first-visible-'+str(len(report['visibleFrames']))+'.png';frame.save(out/name);report['visibleFrames'].append({'hwnd':int(hwnd),'pid':pid.value,'rect':[p.x,p.y,r.right,r.bottom],'cloaked':cloaked.value,'seconds':round(time.monotonic()-started,3),'contrast':max(ImageStat.Stat(frame).stddev),'image':name})
  except Exception as e:report['observerError']=str(e)
  done.wait(.04)
try:
 monitor=threading.Thread(target=observe,daemon=True);monitor.start();start();monitor.join(timeout=8)
 report['presentation']=chrome('return {events:window.__sonaStartupEvents,presentation:window.__sonaStartupPresentation,hidden:window.__sonaStartupHidden,cloaked:window.__sonaStartupCloaked,mainHandle:String(window.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).nativeHandle),timing:Sona.startupTimings,console:Services.console.getMessageArray().map(x=>x.message).slice(-15)}')
 frames=report['visibleFrames'];check('visible_window_never_starts_with_blank_header',bool(frames) and all(f['contrast']>5 for f in frames),frames)
 report['timing']=chrome('return Sona.startupTimings');check('first_visible_window_is_functionally_ready',chrome('return Sona.ready&&document.documentElement.hasAttribute("sona-ui-ready")&&!window.__sonaStartupHidden'))
 count=len(call('browser.state.get')['tabs']);call('browser.newTab');check('new_tab_command_works_on_first_launch',wait(lambda:len(call('browser.state.get')['tabs'])==count+1));check('web_process_isolation_retained',chrome('return Services.prefs.getBoolPref("fission.autostart")&&!Services.prefs.getBoolPref("layers.acceleration.disabled",false)'))
 report['passed']=True
except Exception as e:report['error']=str(e);raise
finally:
 done.set()
 try:stop()
 finally:(out/'firstframe7.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
