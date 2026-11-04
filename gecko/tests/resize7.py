"""Real HWND resize pixel captures. The test page is solid, so black edges are defects."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{},'samples':[]}
try:
 (profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'done':True},'settings':{'theme':'light'}}));start();call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 import ctypes as C
 from ctypes import wintypes as W
 from PIL import ImageGrab
 u=C.windll.user32;u.SetProcessDpiAwarenessContext(C.c_void_p(-4));u.FindWindowW.argtypes=[W.LPCWSTR,W.LPCWSTR];u.FindWindowW.restype=W.HWND;hwnd=u.FindWindowW('MozillaWindowClass',None)
 u.MoveWindow.argtypes=[W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.BOOL];u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)]
 for theme,color in [('light','#f6f6f8'),('dark','#08090b')]:
  call('browser.settings.set',{'theme':theme,'mattePanel':True});content('document.documentElement.style.background='+json.dumps(color)+';document.body.style.background='+json.dumps(color)+';document.body.replaceChildren();return true')
  for i,width in enumerate([700,760,820,880,820,760,700]):
   u.MoveWindow(hwnd,30+i*3,25+i*2,width,650,True);time.sleep(.025);r=W.RECT();p=W.POINT();u.GetClientRect(hwnd,C.byref(r));u.ClientToScreen(hwnd,C.byref(p));im=ImageGrab.grab(all_screens=True).crop((p.x,p.y,p.x+r.right,p.y+r.bottom));im.save(out/f'resize-{theme}-{i}.png')
   points=[(r.right-3,y) for y in [110,r.bottom//2,r.bottom-8]]+[(x,r.bottom-3) for x in [30,r.right//2,r.right-8]];pixels=[im.getpixel(pt)[:3] for pt in points];report['samples'].append({'theme':theme,'width':width,'pixels':pixels});check('no_black_resize_edge_'+theme+str(i),all(sum(px)>100 for px in pixels) if theme=='light' else all(max(px)<60 and sum(px)>0 for px in pixels),pixels)
 report['passed']=True
except Exception as e:report['error']=str(e);raise
finally:
 try:stop()
 finally:(out/'resize7.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
