"""Only the reported 1.0.76 UI regressions; no unrelated feature suites."""
import ctypes as C
from ctypes import wintypes as W
import http.server,importlib.util,json,os,subprocess,sys,tempfile,threading,time
from pathlib import Path
from PIL import ImageGrab
spec=importlib.util.spec_from_file_location('overlay',Path(__file__).with_name('test-cef-settings-overlay.py'))
o=importlib.util.module_from_spec(spec);spec.loader.exec_module(o);s=o.s;u=o.u
s.DEBUG_PORT=s.free_port();s.BASE=f'http://127.0.0.1:{s.DEBUG_PORT}'
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
class Page(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  body=b'''<!doctype html><style>html{color-scheme:light dark}body{margin:0;height:3000px;background:light-dark(white,#111);color:light-dark(black,white)}video{display:block;margin-top:340px;width:480px;height:270px}canvas{display:none}</style><video id=v muted autoplay></video><canvas id=c width=320 height=180></canvas><script>let n=0,ctx=c.getContext('2d');setInterval(()=>{ctx.fillStyle=++n%2?'#2855cc':'#39aa65';ctx.fillRect(0,0,320,180)},50);v.srcObject=c.captureStream(20);v.play().catch(()=>{});window.identity=Math.random()</script>'''
  self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*_):pass
class Cursor(C.Structure):
 _fields_=[('cbSize',W.DWORD),('flags',W.DWORD),('cursor',W.HANDLE),('point',W.POINT)]
def main():
 exe=str(Path(sys.argv[1]).resolve());out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
 report={'passed':False,'checks':[],'limitations':['Local playing-video fixture exercises viewport stability; physical YouTube/GPU performance is left to the owner.']};connections=[];process=None
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Page);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/video'
 def check(value,name):
  assert value,name
  report['checks'].append(name);print('PASS:',name,flush=True)
 def connect(fragment):
  target=o.wait(lambda:next((t for t in s.targets() if fragment in t.get('url','')),None))
  ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE);connections.append(ws);return ws
 try:
  with tempfile.TemporaryDirectory(prefix='soulu-ui-hotfix-',ignore_cleanup_errors=True) as temp:
   env=dict(os.environ,LOCALAPPDATA=temp,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1')
   process=subprocess.Popen([exe,'--no-proxy-server'],env=env);shell=connect('/ui/index.html')
   o.wait(lambda:s.evaluate(shell,"typeof browserShell?.getState==='function'"))
   def call(method,value=None):return s.evaluate(shell,'browserShell.'+method+'('+('' if value is None else json.dumps(value))+')')
   def state():return call('getState')
   hwnd=o.wait(lambda:next(iter(o.windows(process.pid,'SouluBrowserWindow')),None));u.MoveWindow(hwnd,40,30,940,640,True);u.SetForegroundWindow(hwnd)
   call('setSettings',{'theme':'light','mattePanel':True});call('navigate',url);page=connect(url)
   o.wait(lambda:s.evaluate(page,'!!window.v && v.currentTime>.1'))
   call('setSettings',{'theme':'dark'})
   check(o.wait(lambda:s.evaluate(page,"matchMedia('(prefers-color-scheme:dark)').matches")),'Dark browser appearance reaches a supporting website')
   call('setSettings',{'theme':'light'})
   check(o.wait(lambda:s.evaluate(page,"matchMedia('(prefers-color-scheme:light)').matches")),'Light browser appearance reaches a supporting website')
   s.evaluate(page,'scrollTo(0,260)');time.sleep(.3)
   metric="({width:innerWidth,height:innerHeight,y:scrollY,videoTop:v.getBoundingClientRect().top,identity,time:v.currentTime})"
   baseline=s.evaluate(page,metric);samples=[];cursor_samples=[]
   bounds=o.client_rect(hwnd)
   for x in [80,180,300,450,600,760,300,100]:
    u.SetCursorPos(bounds[0]+x,bounds[1]+24);time.sleep(.06)
    value=s.evaluate(page,metric);samples.append(value)
    cursor=Cursor();cursor.cbSize=C.sizeof(cursor);assert u.GetCursorInfo(C.byref(cursor))
    cursor_samples.append(bool(cursor.flags&1 and cursor.cursor))
   report['hoverSamples']=samples;report['cursorVisible']=cursor_samples
   check(all(all(abs(v[k]-baseline[k])<1 for k in ['width','height','y','videoTop']) and v['identity']==baseline['identity'] for v in samples),'Moving over the toolbar does not move or resize the playing video')
   check(samples[-1]['time']>baseline['time'],'Video continues playing during toolbar hover')
   check(all(cursor_samples),'Native cursor remains visible across the upper toolbar')
   # Capture durations from real running animations, not declarations alone.
   def animate(method,value,selector):
    return s.evaluate(shell,"(async()=>{const pending=browserShell."+method+'('+json.dumps(value)+");const node=document.querySelector("+json.dumps(selector)+");for(let i=0;i<30;i++){await new Promise(requestAnimationFrame);const a=node.getAnimations();if(a.length){const durations=a.map(x=>x.effect.getTiming().duration);await pending;return durations}}await pending;return []})()")
   reduced=s.evaluate(shell,"matchMedia('(prefers-reduced-motion:reduce)').matches")
   durations=animate('setOverview',True,'.tab-overview');report['overviewOpenDurations']=durations
   check(reduced or any(250<=d<=400 for d in durations),'Tab overview opens with a smooth timed transition')
   time.sleep(.35);durations=animate('setOverview',False,'.tab-overview');report['overviewCloseDurations']=durations
   check(reduced or any(200<=d<=400 for d in durations),'Tab overview closes with a smooth timed transition')
   durations=animate('setBookmarksSidebar',True,'.bookmarks-menu');report['bookmarksOpenDurations']=durations
   check(reduced or any(250<=d<=400 for d in durations),'Bookmarks open with a smooth timed transition')
   time.sleep(.3);durations=animate('setBookmarksSidebar',False,'.bookmarks-menu');report['bookmarksCloseDurations']=durations
   check(reduced or any(250<=d<=400 for d in durations),'Bookmarks retain their exit animation')
   time.sleep(.35);call('openSettingsWindow');settings=connect('/ui/settings.html')
   o.wait(lambda:state()['settingsOverlayReady']);o.wait(lambda:state()['settingsOverlayProgress']==1)
   current=state();report['settingsDuration']=current['settingsOverlayDuration'];report['settingsTicks']=current['settingsOverlayTicks']
   check(current['settingsOverlayDuration'] in (90,320) and current['settingsOverlayTicks']>=2,'Settings opening reaches its final position through native animation ticks')
   s.evaluate(settings,'souluSettingsRequestClose()');o.wait(lambda:not state()['settingsOverlayOpen'])
   check(True,'Settings closing completes without leaving an overlay')
   ImageGrab.grab().save(out/'final.png');report['passed']=True
 finally:
  for ws in connections:
   try:ws.close()
   except Exception:pass
  if process:s.close_normally(process)
  server.shutdown();(out/'evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()
