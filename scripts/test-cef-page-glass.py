import importlib.util,json,os,sys,subprocess,tempfile,time,threading,ctypes as C
from ctypes import wintypes as W
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from PIL import ImageGrab
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1';os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
u=C.windll.user32;u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND;u.MapWindowPoints.argtypes=[W.HWND,W.HWND,C.POINTER(W.POINT),W.UINT];u.GetDpiForWindow.argtypes=[W.HWND];u.GetDpiForWindow.restype=W.UINT
u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
class Fixture(BaseHTTPRequestHandler):
 def do_GET(self):
  b=b'<style>html,body{margin:0}section{height:230px;background:#d44332}section:nth-of-type(2n){background:#228866}section:nth-of-type(3n){background:#376bd0}nav{position:fixed;top:0;left:0;right:0;height:24px;background:#263c38;color:white;z-index:10}h1{margin:0;padding:30px;font:48px sans-serif;color:white}</style><nav>Site navigation</nav><section><h1>VISIBLE TOP / 0</h1></section><section><h1>SECOND / 230</h1></section><section><h1>THIRD / 460</h1></section><section><h1>FOURTH</h1></section><section><h1>FIFTH</h1></section><script>window.identity=Math.random();window.clicks=0;document.addEventListener("click",()=>clicks++)</script>'
  self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Fixture);threading.Thread(target=server.serve_forever,daemon=True).start()
def wait(fn,timeout=40):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  try:
   v=fn()
   if v:return v
  except Exception:pass
  time.sleep(.1)
 raise AssertionError('Page glass wait timeout')
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);evidence={};p=None;ws=None;page=None
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
 folder=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';folder.mkdir(parents=True);(folder/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'layout':'adaptive','mattePanel':False,'theme':'light','bookmarksBarMode':'never'}))
 try:
  log=(out/'process.log').open('w',encoding='utf-8');p=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server','--log-file='+str((out/'cef.log').resolve())],stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT)))
  t=wait(lambda:next((x for x in s.targets() if '/ui/index.html' in x.get('url','')),None));ws=s.websocket.create_connection(t['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
  wait(lambda:s.evaluate(ws,"document.documentElement.classList.contains('typography-ready')&&!!window.browserShell"))
  def state():return s.evaluate(ws,'browserShell.getState()')
  def call(name,value):return s.evaluate(ws,'browserShell.'+name+'('+json.dumps(value)+')')
  hwnds=[]
  @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
  def visit(hwnd,_):
   pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));name=C.create_unicode_buffer(128);u.GetClassNameW(hwnd,name,128)
   if pid.value==p.pid and name.value=='SouluBrowserWindow':hwnds.append(hwnd)
   return True
  u.EnumWindows(visit,0);hwnd=hwnds[0];u.SetWindowPos(hwnd,None,60,60,980,650,0x0040);u.SetForegroundWindow(hwnd)
  def capture(name):
   time.sleep(.4);r=W.RECT();u.GetWindowRect(hwnd,C.byref(r));im=ImageGrab.grab(all_screens=True).crop((r.left,r.top,r.right,r.bottom));im.save(out/(name+'.png'));return im
  call('navigate',f'http://127.0.0.1:{server.server_port}/glass')
  t=wait(lambda:next((x for x in s.targets() if '/glass' in x.get('url','')),None));page=s.websocket.create_connection(t['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
  wait(lambda:s.evaluate(page,'typeof identity==="number"'));call('setSettings',{'mattePanel':True});identity=s.evaluate(page,'identity');evidence['glassReady']=state().get('pageGlassReady');evidence['glassError']=state().get('pageGlassError');initial=capture('initial')
  scale=u.GetDpiForWindow(hwnd)/96
  content_tops=[]
  @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
  def child_visit(child,_):
   name=C.create_unicode_buffer(128);u.GetClassNameW(child,name,128)
   if u.GetParent(child)==hwnd and u.IsWindowVisible(child) and name.value in ('CefBrowserWindow','Chrome_WidgetWin_1'):
    r=W.RECT();u.GetWindowRect(child,C.byref(r));point=W.POINT(r.left,r.top);u.MapWindowPoints(None,hwnd,C.byref(point),1);content_tops.append(point.y)
   return True
  u.EnumChildWindows(hwnd,child_visit,0)
  evidence['initialNativeContentTops']=content_tops
  assert any(abs(top-68*scale)<=1 for top in content_tops),'Initial website must begin below the 68px toolbar'

  evidence['initialPagePixel']=initial.getpixel((round(20*scale),round(120*scale)))[:3]
  assert evidence['initialPagePixel'][0]>evidence['initialPagePixel'][1]+50, 'Initial document must remain visible below the panel'
  assert evidence['glassReady'],evidence
  s.evaluate(page,'scrollTo(0,260)');wait(lambda:s.evaluate(page,'scrollY>=250'));green=capture('scroll-260')
  s.evaluate(page,'scrollTo(0,500)');wait(lambda:s.evaluate(page,'scrollY>=490'));blue=capture('scroll-500')
  evidence['fixedHeaderTop']=s.evaluate(page,"document.querySelector('nav').getBoundingClientRect().top")
  assert abs(evidence['fixedHeaderTop']-68)<1, 'Fixed site navigation must stay below the browser panel'
  a=green.getpixel((round(130*scale),round(64*scale)))[:3];b=blue.getpixel((round(130*scale),round(64*scale)))[:3];evidence['underGlassPixels']=[a,b]
  assert sum(abs(x-y) for x,y in zip(a,b))>14, 'Glass must sample the changing live page, not a constant background'
  def click_at(x,y):
   r=W.RECT();u.GetWindowRect(hwnd,C.byref(r));u.SetCursorPos(r.left+round(x*scale),r.top+round(y*scale));u.mouse_event(2,0,0,0,0);time.sleep(.05);u.mouse_event(4,0,0,0,0);time.sleep(.15)
  click_at(150,20)
  assert s.evaluate(page,'clicks')==0, 'Toolbar background must block clicks to hidden site content'
  click_at(150,76)
  assert s.evaluate(page,'clicks')==1, 'Feathered edge must not block the page below the toolbar'
  call('setSettings',{'mattePanel':False});wait(lambda:s.evaluate(ws,"document.body.dataset.matte==='false'"));capture('off')
  evidence['offStyle']=s.evaluate(ws,"getComputedStyle(document.querySelector('.classic-toolbar')).backgroundColor")
  assert evidence['offStyle']=='rgb(255, 255, 255)',evidence
  assert s.evaluate(page,'identity')==identity
  s.evaluate(page,'scrollTo(0,0)');capture('off-top');call('setSettings',{'mattePanel':True});capture('back-top')
  # Regressions: dark chrome, both layouts, tab lifetime and native resizing.
  call('setSettings',{'theme':'dark','mattePanel':False})
  wait(lambda:s.evaluate(ws,"document.body.dataset.theme==='dark'"))
  evidence['darkOffStyle']=s.evaluate(ws,"getComputedStyle(document.querySelector('.classic-toolbar')).backgroundColor")
  assert evidence['darkOffStyle']=='rgb(8, 9, 11)',evidence
  capture('dark-off');call('setSettings',{'mattePanel':True});s.evaluate(page,'scrollTo(0,260)');capture('dark-glass')
  assert state()['pageGlassReady'] and s.evaluate(page,'identity')==identity
  first=state()['activeTabId'];call('newTab',None)
  wait(lambda:len(state()['tabs'])==2);second=state()['activeTabId']
  call('navigate',f'http://127.0.0.1:{server.server_port}/glass?second')
  t=wait(lambda:next((x for x in s.targets() if '?second' in x.get('url','')),None))
  other=s.websocket.create_connection(t['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
  wait(lambda:s.evaluate(other,'typeof identity==="number"'));other_identity=s.evaluate(other,'identity')
  s.evaluate(other,'scrollTo(0,300)');capture('two-tabs-dark')
  evidence['twoTabFixedTop']=s.evaluate(other,"document.querySelector('nav').getBoundingClientRect().top")
  assert abs(evidence['twoTabFixedTop']-88)<1,evidence
  call('switchTab',first);time.sleep(.4)
  assert s.evaluate(page,'identity')==identity and s.evaluate(page,'scrollY')==260
  call('switchTab',second);time.sleep(.4)
  assert s.evaluate(other,'identity')==other_identity and s.evaluate(other,'scrollY')==300
  for width in (640,980):
   u.SetWindowPos(hwnd,None,60,60,width,650,0x0040);time.sleep(.4)
   assert state()['pageGlassReady']
   assert abs(s.evaluate(other,"document.querySelector('nav').getBoundingClientRect().top")-88)<1
   capture('resize-'+str(width))
  other.close();call('closeTab',second);wait(lambda:len(state()['tabs'])==1);time.sleep(.4)
  assert s.evaluate(page,'identity')==identity
  assert abs(s.evaluate(page,"document.querySelector('nav').getBoundingClientRect().top")-68)<1
  call('setSettings',{'layout':'compact'});time.sleep(.5);capture('compact-glass')
  assert abs(s.evaluate(page,"document.querySelector('nav').getBoundingClientRect().top")-58)<1
  call('setSettings',{'layout':'adaptive','theme':'light'});time.sleep(.4)
  # Real external HTTPS pages: verify scroll, fixed controls and no reload on toggles.
  evidence['externalSites']=[]
  page.close();page=None
  for url in ('https://example.com','https://www.wikipedia.org','https://developer.mozilla.org/en-US/docs/Web/CSS'):
   call('navigate',url)
   target=wait(lambda:next((x for x in s.targets() if x.get('url','').startswith(url)),None))
   remote=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
   wait(lambda:s.evaluate(remote,"document.readyState==='complete'"),60)
   info=s.evaluate(remote,"({url:location.href,title:document.title,height:document.documentElement.scrollHeight,viewport:innerHeight})")
   assert info['title'] and not info['url'].startswith('chrome-error:'),info
   s.evaluate(remote,'window.__glassTestIdentity=Math.random();scrollTo(0,300)');time.sleep(.7)
   token=s.evaluate(remote,'__glassTestIdentity');call('setSettings',{'mattePanel':False});time.sleep(.3);call('setSettings',{'mattePanel':True});time.sleep(.4)
   assert s.evaluate(remote,'__glassTestIdentity')==token
   info['scrollY']=s.evaluate(remote,'scrollY');evidence['externalSites'].append(info)
   capture('site-'+str(len(evidence['externalSites'])))
   remote.close()
  evidence['passed']=True
 finally:
  evidence['exitCodeBeforeClose']=p.poll() if p else None
  print(json.dumps(evidence),flush=True)
  (out/'evidence.json').write_text(json.dumps(evidence,indent=2))
  if page:page.close()
  if ws:ws.close()
  if p and p.poll() is None:
   try:s.close_normally(p)
   except Exception:p.kill();p.wait()
  server.shutdown()
