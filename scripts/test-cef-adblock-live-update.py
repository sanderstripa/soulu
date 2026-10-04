"""Hold CONNECT until a real CEF content page is active; preserve end-to-end TLS."""
import http.server,importlib.util,json,os,select,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('s',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
release=threading.Event();ads=0
class Handler(http.server.BaseHTTPRequestHandler):
 def do_CONNECT(self):
  host,port=self.path.rsplit(':',1)
  if host not in ('easylist.to','easylist-downloads.adblockplus.org') or port!='443':self.send_error(403);return
  release.wait(8)
  try:
   address=socket.getaddrinfo(host,443,socket.AF_INET,socket.SOCK_STREAM)[0][4];upstream=socket.create_connection(address,timeout=8);self.send_response(200);self.end_headers()
   peers=(self.connection,upstream)
   end=time.monotonic()+100
   while time.monotonic()<end:
    ready,_,_=select.select(peers,[],[],2)
    for incoming in ready:
     data=incoming.recv(65536)
     if not data:return
     (upstream if incoming is self.connection else self.connection).sendall(data)
  except OSError:pass
  finally:
   if 'upstream' in locals():upstream.close()
 def do_GET(self):
  global ads
  if self.path.startswith('/ad'):ads+=1;body=b'window.adReached=true';kind='text/javascript'
  else:
   body=('<title>Live update fixture</title><h1>Ordinary content</h1><script>setInterval(()=>fetch("http://ad.doubleclick.net:'+str(self.server.server_port)+'/ad-ping").catch(()=>{}),200)</script>').encode();kind='text/html'
  self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.end_headers()
  try:self.wfile.write(body)
  except OSError:pass
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();result={};process=None
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
def wait(fn,timeout=100):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  r=fn()
  if r:return r
  time.sleep(.2)
 raise AssertionError('Live update timeout')
with tempfile.TemporaryDirectory(prefix='soulu-live-update-',ignore_cleanup_errors=True) as root:
 env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1')
 for key in ('SOULU_ADBLOCK_NO_UPDATE','SOULU_ADBLOCK_TEST_RULES','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):env.pop(key,None)
 env['HTTPS_PROXY']='http://127.0.0.1:'+str(server.server_port)
 try:
  process=subprocess.Popen([sys.argv[1],'--no-proxy-server','--host-resolver-rules=MAP ad.doubleclick.net 127.0.0.1'],env=env)
  target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None),40);shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE);page=s.page_socket()
  wait(lambda:s.evaluate(shell,"typeof window.browserShell==='object'"),15)
  s.evaluate(shell,'window.browserShell.setContentBlocking({domain:"",value:1})');s.navigate(page,'http://127.0.0.1:'+str(server.server_port)+'/fixture')
  status=lambda:s.evaluate(shell,'window.browserShell.getCurrentSite()')['adblock']
  before=wait(lambda:(r if (r:=status())['blockedRequests']>0 else None),4);result['before']=before
  assert before['source']=='bundled' and before['lastSuccessfulUpdate']==0,'Update was not held until page became active'
  release.set()
  def updated():
   r=status();result['lastStatus']=r
   if r['lastUpdateError']:raise AssertionError(r['lastUpdateError'])
   return r if r['lastSuccessfulUpdate']>0 else None
  after=wait(updated);result['after']=after;time.sleep(1);last=status()
  assert last['blockedRequests']>after['blockedRequests'] and last['active'] and ads==0
  assert s.evaluate(page,"document.title==='Live update fixture'&&!window.adReached")
  result.update(passed=True,serverAdRequests=ads,tlsIntercepted=False,afterUpdateNewRequestCount=last['blockedRequests']-after['blockedRequests'])
  page.close();shell.close();s.close_normally(process)
 except Exception as e:result.update(passed=False,error=type(e).__name__+': '+str(e))
 finally:
  release.set()
  if process and process.poll() is None:process.kill();process.wait()
  Path(sys.argv[2]).write_text(json.dumps(result,indent=2),encoding='utf-8')
server.shutdown();print(json.dumps({k:v for k,v in result.items() if k not in ('before','after','lastStatus')}))

if not result.get('passed'):raise AssertionError(result.get('error','Live update verification failed'))
