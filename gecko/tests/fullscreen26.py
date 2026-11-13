"""Real trusted Fullscreen API entry/exit for video and cross-origin iframe video."""
import base64,contextlib,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

VIDEO='''<!doctype html><style>html,body{margin:0;background:#111;color:white}video{width:320px;height:180px}video:fullscreen{width:100vw;height:100vh;background:#111;object-fit:contain}</style><button id="enter">Fullscreen video</button><video id="video" muted autoplay playsinline></video><script>const c=document.createElement('canvas');c.width=640;c.height=360;const x=c.getContext('2d');x.fillStyle='#0671ff';x.fillRect(0,0,640,360);video.srcObject=c.captureStream(1);enter.onclick=()=>video.requestFullscreen();</script>'''
def verify_fullscreen(m,check,wait,out):
 class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
   body=(f'<!doctype html><iframe id="player" allow="fullscreen;autoplay" allowfullscreen src="http://127.0.0.1:{child.server_port}/video" style="width:640px;height:360px;border:0"></iframe>' if self.path=='/embedded' else VIDEO).encode()
   self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body)
  def log_message(self,*args):pass
 with contextlib.ExitStack() as stack:
  child=ThreadingHTTPServer(('127.0.0.1',0),Handler);outer=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  for server in [child,outer]:
   threading.Thread(target=server.serve_forever,daemon=True).start();stack.callback(server.server_close);stack.callback(server.shutdown)
  previous=m.current_window_handle
  for label,path in [('direct','/video'),('iframe','/embedded')]:
   handles=set(m.window_handles)
   m.execute_script('gBrowser.selectedTab=gBrowser.addTrustedTab(arguments[0]);return true;',script_args=[f'http://127.0.0.1:{outer.server_port}{path}'])
   added=wait(lambda:list(set(m.window_handles)-handles));m.switch_to_window(added[0]);m.set_context('chrome')
   wait(lambda:m.execute_script('return !Sona.snapshot().adaptiveToolbar.active;'))
   baseline=m.execute_script('const r=document.getElementById("browser").getBoundingClientRect();return {top:r.top,tabs:gBrowser.tabs.length};')
   check('normal_toolbar_space_'+label,baseline['top']>0,baseline)
   m.set_context('content');wait(lambda:m.execute_script('return document.readyState==="complete";'))
   if label=='iframe':m.switch_to_frame(m.find_element('id','player'))
   wait(lambda:m.execute_script('return !!document.getElementById("enter");'))
   m.find_element('id','enter').click()
   wait(lambda:m.execute_script('return document.fullscreenElement?.id==="video";'))
   m.set_context('chrome')
   check('native_dom_fullscreen_'+label,wait(lambda:m.execute_script('return document.documentElement.hasAttribute("inDOMFullscreen");')))
   geometry=wait(lambda:m.execute_script('const r=document.getElementById("browser").getBoundingClientRect(),s=getComputedStyle(document.getElementById("sona-shell-frame"));return Math.abs(r.top)<1&&s.display==="none"?{top:r.top,height:r.height,windowHeight:innerHeight}:null;'))
   check('fullscreen_no_reserved_toolbar_'+label,abs(geometry['height']-geometry['windowHeight'])<1,geometry)
   (out/('fullscreen-'+label+'.png')).write_bytes(base64.b64decode(m.screenshot()))
   # Exiting via the native browser controller exercises the same path as Escape.
   m.execute_script('document.exitFullscreen();return true;')
   check('native_dom_fullscreen_exited_'+label,wait(lambda:m.execute_script('return !document.documentElement.hasAttribute("inDOMFullscreen");')))
   check('fullscreen_exit_restores_toolbar_'+label,wait(lambda:m.execute_script('const r=document.getElementById("browser").getBoundingClientRect();return !document.documentElement.hasAttribute("inDOMFullscreen")&&Math.abs(r.top-arguments[0])<1&&getComputedStyle(document.getElementById("sona-shell-frame")).display!=="none";',script_args=[baseline['top']])))
   check('fullscreen_keeps_tabs_'+label,m.execute_script('return gBrowser.tabs.length')==baseline['tabs'])
   m.execute_script('gBrowser.removeTab(gBrowser.selectedTab,{animate:false});return true;');m.switch_to_window(previous);m.set_context('chrome')
