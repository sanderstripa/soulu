"""End-to-end daily-use regressions against the built Windows CEF browser."""
import base64,ctypes,http.server,importlib.util,io,json,math,os,struct,subprocess,sys,tempfile,threading,time,wave
from pathlib import Path
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1';os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
def wait(fn,timeout=30):
 end=time.monotonic()+timeout;last=''
 while time.monotonic()<end:
  try:
   value=fn()
   if value:return value
  except Exception as error:last=str(error)
  time.sleep(.1)
 raise AssertionError('Daily-use timeout: '+last)
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);report={'checks':[]}
def check(value,label):
 assert value,label
 report['checks'].append(label);print('PASS:',label,flush=True)
def socket_for(part):
 target=wait(lambda:next((t for t in s.targets() if part in t.get('url','')),None))
 return s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
def click(ws,selector):
 point=wait(lambda:s.evaluate(ws,"(()=>{const n=document.querySelector("+json.dumps(selector)+");if(!n)return null;const r=n.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;if(!r.width||!r.height||r.left<0||r.top<0||r.right>innerWidth+.5||r.bottom>innerHeight+.5||!n.contains(document.elementFromPoint(x,y)))return null;return {x,y}})()"))
 for kind in ['mousePressed','mouseReleased']:s.command(ws,'Input.dispatchMouseEvent',dict(type=kind,button='left',clickCount=1,**point))
def native_window(pid):
 handles=[];user=ctypes.windll.user32;callback_type=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
 @callback_type
 def callback(hwnd,_):
  process=ctypes.c_ulong();user.GetWindowThreadProcessId(hwnd,ctypes.byref(process));name=ctypes.create_unicode_buffer(256);user.GetClassNameW(hwnd,name,len(name))
  if process.value==pid and name.value=='SouluBrowserWindow':handles.append(hwnd);return False
  return True
 user.EnumWindows(callback,0);return handles[0] if handles else None
buf=io.BytesIO()
with wave.open(buf,'wb') as wav:
 wav.setparams((1,2,8000,0,'NONE','not compressed'));wav.writeframes(b''.join(struct.pack('<h',int(5000*math.sin(i*math.tau*440/8000))) for i in range(8000)))
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  data=buf.getvalue() if self.path.startswith('/tone.wav') else b'<title>Daily use</title><form><input id="user" autocomplete="username"><input id="password" type="password" autocomplete="current-password"></form><audio id="audio" autoplay loop src="/tone.wav"></audio><button id="play" onclick="audio.play()">Play</button><button id="webAudio" onclick="window.ac=new AudioContext();window.osc=ac.createOscillator();window.gain=ac.createGain();gain.gain.value=.1;osc.connect(gain);gain.connect(ac.destination);osc.start();ac.resume()">Web Audio</button>'
  self.send_response(200);self.send_header('Content-Type','audio/wav' if self.path.startswith('/tone.wav') else 'text/html');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
p=None;connections=[]
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
 config=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';config.mkdir(parents=True);(config/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'theme':'light','layout':'adaptive','mattePanel':False,'newTabMode':'soulu','homeMode':'soulu','startupMode':'soulu'}))
 env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT))
 try:
  p=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server','--use-fake-device-for-media-stream'],env=env)
  shell=socket_for('/ui/index.html');connections.append(shell)
  wait(lambda:s.evaluate(shell,"!!window.browserShell&&!!document.querySelector('#classicAddress')"))
  hwnd=wait(lambda:native_window(p.pid));wait(lambda:ctypes.windll.user32.IsWindowVisible(hwnd))
  wait(lambda:s.evaluate(shell,"document.documentElement.classList.contains('typography-ready')"))
  state=lambda:s.evaluate(shell,'browserShell.getState()')
  s.evaluate(shell,'browserShell.navigate('+json.dumps(origin+'/login?full=address#fragment')+')')
  page=socket_for('/login?');connections.append(page)
  wait(lambda:s.evaluate(page,"document.readyState==='complete'"))
  wait(lambda:s.evaluate(shell,"document.querySelector('#classicAddress').value==='127.0.0.1'"))
  click(shell,'#classicAddress');wait(lambda:s.evaluate(shell,"document.querySelector('#classicAddress').value").endswith('/login?full=address#fragment'));check(True,'Address shows host at rest and full path/query/fragment on focus')
  s.evaluate(shell,"document.querySelector('#classicAddress').blur()")
  check(s.evaluate(shell,"(()=>{const a=document.querySelector('#classicAddressForm').getBoundingClientRect(),b=document.querySelector('#newTabButton').getBoundingClientRect();return b.left>=a.right&&b.left-a.right<12})()"),'New-tab button sits immediately beside the address')
  for width in (620,900,1280):
   s.command(shell,'Emulation.setDeviceMetricsOverride',{'width':width,'height':760,'deviceScaleFactor':1,'mobile':False});time.sleep(.15)
   check(s.evaluate(shell,"(()=>{const b=document.querySelector('#newTabButton').getBoundingClientRect(),a=document.querySelector('#classicAddressForm').getBoundingClientRect();return b.left>=a.right&&b.right<=innerWidth&&[...document.querySelectorAll('.classic-navigation-right button')].every(n=>{const r=n.getBoundingClientRect();return !r.width||b.right<=r.left||b.left>=r.right})})()"),f'Address/new-tab controls do not overlap service buttons at {width}px')
  s.command(shell,'Emulation.clearDeviceMetricsOverride')
  # Repeated loading/state updates must preserve the tab DOM and focused controls.
  s.evaluate(shell,"window.dailyTab=document.querySelector('.classic-tab');window.dailyFavicon=dailyTab.querySelector('.favicon')")
  for _ in range(15):s.evaluate(shell,'browserShell.getState().then(v=>__souluEmit("state",v))')
  time.sleep(.2);check(s.evaluate(shell,"window.dailyTab===document.querySelector('.classic-tab')"),'Unchanged tab nodes survive repeated state events')
  # A native translation/reader job can create an isolated world in this frame.
  # Such a world must never install its own background-media guard.
  frame=s.command(page,'Page.getFrameTree')['frameTree']['frame']['id']
  world=s.command(page,'Page.createIsolatedWorld',{'frameId':frame,'worldName':'daily-isolated'})['executionContextId']
  isolated=s.command(page,'Runtime.evaluate',{'expression':"typeof window.__souluMediaPolicy",'contextId':world,'returnByValue':True})
  check(isolated['result'].get('value')=='undefined','Service JavaScript worlds do not install a second background-playback guard')
  original=state()['activeTabId'];s.evaluate(shell,'browserShell.openTab('+json.dumps(origin+'/background')+',true)')
  background=socket_for('/background');connections.append(background);wait(lambda:s.evaluate(background,"document.querySelector('audio')?.readyState>=2"));time.sleep(1)
  check(s.evaluate(background,"document.querySelector('audio').paused"),'Opening an audio/video page in a new background tab does not start playback')
  bg=next(t['id'] for t in state()['tabs'] if '/background' in t['url']);s.evaluate(shell,f'browserShell.switchTab({bg})');wait(lambda:state()['activeTabId']==bg);click(background,'#play')
  playback=s.command(background,'Runtime.evaluate',{'expression':"document.querySelector('#audio').play().then(()=>({playing:!document.querySelector('#audio').paused}),e=>({error:e.name+': '+e.message}))",'awaitPromise':True,'returnByValue':True,'userGesture':True})
  print('PLAYBACK',json.dumps(playback),flush=True)
  print('MEDIA_STATE',json.dumps(s.evaluate(background,"(()=>{const a=document.querySelector('#audio');return {paused:a.paused,ready:a.readyState,volume:a.volume,muted:a.muted,error:a.error?.message,policy:typeof window.__souluMediaPolicy,focus:document.hasFocus()}})()")),flush=True)
  check(playback.get('result',{}).get('value',{}).get('playing'),'Selected media tab accepts a user-initiated play request')
  wait(lambda:any(t.get('audible') for t in state()['tabs'] if t['id']==bg))
  s.evaluate(shell,"window.__muteCalls=[];window.__originalMute=browserShell.toggleTabAudio;browserShell.toggleTabAudio=id=>{__muteCalls.push({id});return __originalMute(id).then(result=>{__muteCalls.push({result});return result})}")
  wait(lambda:s.evaluate(shell,"!!document.querySelector('[data-mute-tab]')"));click(shell,f'#tabStrip [data-mute-tab="{bg}"]')
  time.sleep(.3)
  print('MUTE CALLS',s.evaluate(shell,'JSON.stringify(__muteCalls)'),flush=True)
  print('MUTE STATE',json.dumps(state()),flush=True)
  print('MUTE DIRECT',json.dumps(s.evaluate(shell,f'browserShell.toggleTabAudio({bg})')),flush=True)
  time.sleep(.2)
  print('MUTE DIRECT STATE',json.dumps(state()),flush=True)
  wait(lambda:next(t for t in state()['tabs'] if t['id']==bg).get('muted'));check(True,'Playback indicator and one-click tab mute are connected to the native browser')
  s.evaluate(background,"audio.pause()")
  s.evaluate(shell,f'browserShell.toggleTabAudio({bg})');s.command(background,'Runtime.evaluate',{'expression':"document.querySelector('#webAudio').click()",'userGesture':True})
  wait(lambda:next(t for t in state()['tabs'] if t['id']==bg).get('audible'))
  s.evaluate(background,"gain.gain.value=0")
  wait(lambda:not next(t for t in state()['tabs'] if t['id']==bg).get('audible'));s.evaluate(background,"osc.stop();ac.close()")
  check(True,'Web Audio output samples produce an activity indicator; zero gain clears it')
  for permission in ['microphone','camera']:s.evaluate(shell,'browserShell.getCurrentSite().then(site=>browserShell.siteAction("permission",{...site,permission:'+json.dumps(permission)+',value:0}))')
  check(not next(t for t in state()['tabs'] if t['id']==bg).get('microphoneActive'),'A granted microphone permission alone is not marked as active capture')
  s.evaluate(background,'navigator.mediaDevices.getUserMedia({audio:true,video:true}).then(stream=>{window.dailyStream=stream;return true})')
  wait(lambda:next(t for t in state()['tabs'] if t['id']==bg).get('microphoneActive') and next(t for t in state()['tabs'] if t['id']==bg).get('cameraActive'))
  s.evaluate(background,'dailyStream.getTracks().forEach(t=>t.stop())')
  wait(lambda:not next(t for t in state()['tabs'] if t['id']==bg).get('microphoneActive') and not next(t for t in state()['tabs'] if t['id']==bg).get('cameraActive'));check(True,'Camera/microphone indicators follow actual stream start and track stop')
  # Fill both fields from a username-field click and a single saved-login selection.
  def invoke(action,payload):return s.evaluate(shell,'new Promise((resolve,reject)=>cefQuery({request:JSON.stringify('+json.dumps({'action':action,'payload':payload})+'),onSuccess:r=>resolve(JSON.parse(r||"null")),onFailure:(_,m)=>reject(Error(m))}))')
  invoke('browser.passwords.add',{'origin':origin,'username':'daily-user','password':'daily-test-secret'})
  click(background,'#user');time.sleep(.4)
  # Native menus handle keyboard selection; focus stays with the native menu.
  ctypes.windll.user32.keybd_event(0x28,0,0,0);ctypes.windll.user32.keybd_event(0x28,0,2,0)
  ctypes.windll.user32.keybd_event(0x0D,0,0,0);ctypes.windll.user32.keybd_event(0x0D,0,2,0)
  wait(lambda:s.evaluate(background,"user.value==='daily-user'&&password.value==='daily-test-secret'"));check(True,'Selecting a saved login fills username and password together')
  # Closing only the download surface must preserve both tabs.
  count=len(state()['tabs']);s.evaluate(shell,'__souluEmit("openDownloads",null)');wait(lambda:s.evaluate(shell,"document.querySelector('#downloadsPanel').classList.contains('open')"));click(shell,'#closeDownloads')
  wait(lambda:s.evaluate(shell,"!document.querySelector('#downloadsPanel').classList.contains('open')"));check(len(state()['tabs'])==count,'Downloads close button dismisses the panel without closing a tab')
  click(shell,'.classic-toolbar [data-home]');wait(lambda:state()['page']['url']=='soulu://home');check(not state()['page']['loading'],'Home button returns to the configured home page without a permanent loading spinner')
  # Native host geometry survives a clean restart, including maximize state.
  class Rect(ctypes.Structure):_fields_=[('left',ctypes.c_long),('top',ctypes.c_long),('right',ctypes.c_long),('bottom',ctypes.c_long)]
  work=Rect();ctypes.windll.user32.SystemParametersInfoW(0x0030,0,ctypes.byref(work),0)
  expected=(work.left+20,work.top+20,min(980,work.right-work.left-40),min(650,work.bottom-work.top-40))
  hwnd=wait(lambda:native_window(p.pid));wait(lambda:ctypes.windll.user32.IsWindowVisible(hwnd));ctypes.windll.user32.ShowWindow(hwnd,9);ctypes.windll.user32.MoveWindow(hwnd,*expected,True)
  for ws in connections:ws.close()
  connections.clear();s.close_normally(p);p=None
  placement=Path(root)/'Soulu'/'User Data'/'window-placement.json';check(placement.exists(),'Native window placement is persisted on close')
  p=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server'],env=env);shell=socket_for('/ui/index.html');connections.append(shell);hwnd=wait(lambda:native_window(p.pid))
  wait(lambda:ctypes.windll.user32.IsWindowVisible(hwnd));rect=Rect();ctypes.windll.user32.GetWindowRect(hwnd,ctypes.byref(rect));check(abs(rect.left-expected[0])<=2 and abs(rect.top-expected[1])<=2 and abs(rect.right-rect.left-expected[2])<=2,'Window position and normal size are restored on restart')
  ctypes.windll.user32.ShowWindow(hwnd,3)
  for ws in connections:ws.close()
  connections.clear();s.close_normally(p);p=None
  p=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server'],env=env);shell=socket_for('/ui/index.html');connections.append(shell);hwnd=wait(lambda:native_window(p.pid));wait(lambda:ctypes.windll.user32.IsZoomed(hwnd));check(True,'Maximized state is restored on restart')
 finally:
  for ws in connections:
   try:ws.close()
   except Exception:pass
  if p and p.poll() is None:
   try:s.close_normally(p)
   except Exception:p.kill()
  server.shutdown();(out/'daily-use.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
