import importlib.util,json,os,sys,subprocess,tempfile,time,threading,ctypes as C
from ctypes import wintypes as W
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from PIL import ImageGrab
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1';os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
u=C.windll.user32;u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)];u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
class Fixture(BaseHTTPRequestHandler):
 def do_GET(self):
  b=b'<style>html,body{margin:0}section{height:230px;background:#d44332}section:nth-child(2n){background:#228866}section:nth-child(3n){background:#376bd0}h1{margin:0;padding:30px;font:48px sans-serif;color:white}</style><section><h1>VISIBLE TOP / 0</h1></section><section><h1>SECOND / 230</h1></section><section><h1>THIRD / 460</h1></section><section><h1>FOURTH</h1></section><section><h1>FIFTH</h1></section><script>window.identity=Math.random()</script>'
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
 folder=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';folder.mkdir(parents=True);(folder/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'layout':'adaptive','mattePanel':True,'theme':'light','bookmarksBarMode':'never'}))
 try:
  p=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server'],env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT)))
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
  wait(lambda:s.evaluate(page,'typeof identity==="number"'));identity=s.evaluate(page,'identity');evidence['glassReady']=state().get('pageGlassReady');capture('initial')
  assert evidence['glassReady'],'Native page backdrop effect did not initialize'
  s.evaluate(page,'scrollTo(0,260)');wait(lambda:s.evaluate(page,'scrollY>=250'));green=capture('scroll-260')
  s.evaluate(page,'scrollTo(0,500)');wait(lambda:s.evaluate(page,'scrollY>=490'));blue=capture('scroll-500')
  a=green.getpixel((130,64))[:3];b=blue.getpixel((130,64))[:3];evidence['underGlassPixels']=[a,b]
  assert sum(abs(x-y) for x,y in zip(a,b))>14, 'Glass must sample the changing live page, not a constant background'
  call('setSettings',{'mattePanel':False});wait(lambda:s.evaluate(ws,"document.body.dataset.matte==='false'"));capture('off')
  evidence['offStyle']=s.evaluate(ws,"getComputedStyle(document.querySelector('.classic-toolbar')).backgroundColor")
  assert evidence['offStyle']=='rgb(255, 255, 255)',evidence
  assert s.evaluate(page,'identity')==identity
  s.evaluate(page,'scrollTo(0,0)');capture('off-top');call('setSettings',{'mattePanel':True});capture('back-top')
  evidence['passed']=True
 finally:
  (out/'evidence.json').write_text(json.dumps(evidence,indent=2))
  if page:page.close()
  if ws:ws.close()
  if p:s.close_normally(p)
  server.shutdown()
