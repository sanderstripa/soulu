"""Only native Mica paint, content-edge pixels and video after the USER-sheet fix."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{}}
try:
 (profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'done':True},'settings':{'theme':'light'}}));start();call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 call('browser.settings.set',{'mattePanel':False});check('disabled_matte_paints_opaque_soulu_background',chrome('return getComputedStyle(document.documentElement).backgroundColor!=="rgba(0, 0, 0, 0)"&&!document.documentElement.hasAttribute("windowsmica")'))
 call('browser.settings.set',{'mattePanel':True});state=chrome('return {available:Soulu.material.native,enabled:document.documentElement.hasAttribute("windowsmica"),background:getComputedStyle(document.documentElement).backgroundColor};')
 check('enabled_matte_releases_opaque_early_paint',state['background']=='rgba(0, 0, 0, 0)' and state['enabled'] if state['available'] else state['background']!='rgba(0, 0, 0, 0)',state)
 before=content('return {height:innerHeight,width:innerWidth,time:document.querySelector("video").currentTime};');time.sleep(1);after=content('return {height:innerHeight,width:innerWidth,time:document.querySelector("video").currentTime};');check('native_backdrop_keeps_video_playing_and_geometry_stable',after['time']>before['time'] and after['height']==before['height'] and after['width']==before['width'])
 if os.name=='nt':
  import ctypes as C
  from ctypes import wintypes as W
  from PIL import ImageGrab
  u=C.windll.user32;u.SetProcessDpiAwarenessContext(C.c_void_p(-4));u.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];u.FindWindowW.restype=W.HWND;hwnd=u.FindWindowW('MozillaWindowClass',None);r=W.RECT();p=W.POINT();u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)];assert u.GetClientRect(hwnd,C.byref(r)) and u.ClientToScreen(hwnd,C.byref(p))
  outer=W.RECT();u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.GetWindowRect(hwnd,C.byref(outer));u.MoveWindow.argtypes=[W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.BOOL];u.MoveWindow(hwnd,40,30,900+outer.right-outer.left-r.right,600+outer.bottom-outer.top-r.bottom,True);u.SetForegroundWindow.argtypes=[W.HWND];u.SetForegroundWindow(hwnd);time.sleep(.3);u.GetClientRect(hwnd,C.byref(r));u.ClientToScreen(hwnd,C.byref(p))
  content('document.documentElement.style.background="#e0e8f0";document.body.style.background="#e0e8f0";return true;');time.sleep(.3)
  image=ImageGrab.grab(all_screens=True).crop((p.x,p.y,p.x+r.right,p.y+r.bottom));image.save(out/'mica-native-window.png');pixel=image.getpixel((r.right//2,r.bottom-4));check('bottom_content_has_no_black_band',sum(pixel[:3])>100,{'pixel':pixel})
 report['passed']=True
except Exception as e:
 report['error']=str(e);raise
finally:
 try:stop()
 finally:(out/'mica-final5.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
