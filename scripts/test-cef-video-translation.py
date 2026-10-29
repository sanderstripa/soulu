"""Real YouTube smoke test for the bundled VOT runtime and translated-track readiness."""
import base64,importlib.util,json,os,subprocess,sys,tempfile,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1';os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);report={'checks':[],'events':[]};process=None;shell=page=None
def wait(fn,timeout=60):
 end=time.monotonic()+timeout;last=''
 while time.monotonic()<end:
  try:
   v=fn()
   if v:return v
  except Exception as e:last=str(e)
  time.sleep(.3)
 raise AssertionError('Video wait timeout: '+last)
def connect(t):return s.websocket.create_connection(t['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
def deep(selector,expression='node'):
 return s.evaluate(page,"(()=>{const queue=[document];while(queue.length){const root=queue.shift();const node=root.querySelector("+json.dumps(selector)+");if(node)return "+expression+";for(const n of root.querySelectorAll('*'))if(n.shadowRoot)queue.push(n.shadowRoot)}return null})()")
def check(ok,label):
 assert ok,label
 report['checks'].append(label);print('PASS:',label,flush=True)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
 profile=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';profile.mkdir(parents=True)
 (profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'layout':'adaptive','mattePanel':False,'videoTranslationEnabled':True}),encoding='utf-8')
 try:
  process=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server'],env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT)))
  shell=connect(wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None)))
  wait(lambda:s.evaluate(shell,'!!window.browserShell'))
  s.evaluate(shell,"browserShell.openTab('https://www.youtube.com/watch?v=jNQXAC9IVRw')")
  page=connect(wait(lambda:next((t for t in s.targets() if 'youtube.com/watch' in t.get('url','')),None)))
  original_recv=page.recv
  def capture():
   raw=original_recv()
   try:
    event=json.loads(raw)
    if event.get('method') in ('Runtime.consoleAPICalled','Runtime.exceptionThrown','Log.entryAdded'):report['events'].append(event)
   except Exception:pass
   return raw
  page.recv=capture
  s.command(page,'Runtime.enable');s.command(page,'Log.enable')
  wait(lambda:s.evaluate(page,"!!document.querySelector('video')"),90)
  check(s.evaluate(page,"typeof window.__souluVideoNative==='undefined'"),'No public native video bridge on YouTube')
  wait(lambda:deep('.vot-translate-button','true'),90)
  check(True,'Pinned VOT creates controls on a real YouTube player')
  report['before']=deep('.vot-segmented-button','({status:node.dataset.status,text:node.textContent})')
  rect=s.evaluate(page,"(()=>{const r=document.querySelector('video').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+30}})()")
  s.command(page,'Input.dispatchMouseEvent',dict(type='mouseMoved',**rect));time.sleep(.5)
  rect=deep('.vot-translate-button','(()=>{const r=node.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()')
  for kind in ('mouseMoved','mousePressed','mouseReleased'):
   s.command(page,'Input.dispatchMouseEvent',dict(type=kind,**rect,button='left' if kind!='mouseMoved' else 'none',clickCount=1 if kind!='mouseMoved' else 0))
  def status():
   state=deep('.vot-segmented-button','({status:node.dataset.status,text:node.textContent})')
   if state:report['translation']=state
   return state and state['status'] in ('success','error') and state
  final=wait(status,180)
  shot=s.command(page,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'youtube-vot.png').write_bytes(base64.b64decode(shot['data']))
  check(final['status']=='success','Russian translation audio track becomes ready')
  report['passed']=True
 finally:
  if page:
   try:
    report['page']=s.evaluate(page,"({url:location.href,title:document.title,text:document.body?.innerText?.slice(0,8000),player:window.ytInitialPlayerResponse?.playabilityStatus,hosts:document.querySelectorAll('vot-shadow-host').length})")
    shot=s.command(page,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'youtube-diagnostic.png').write_bytes(base64.b64decode(shot['data']))
   except Exception as e:report['diagnosticError']=str(e)
  print('VIDEO_DIAGNOSTIC',json.dumps(report,ensure_ascii=False),flush=True)
  for ws in (page,shell):
   if ws:
    try:ws.close()
    except Exception:pass
  if process and process.poll() is None:
   try:s.close_normally(process)
   except Exception:process.kill();process.wait()
  (out/'video-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
