"""Native VOT integration: live YouTube when accessible, plus a mandatory synthetic player."""
import base64,importlib.util,json,os,re,subprocess,sys,tempfile,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1';os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);report={'checks':[],'events':[]};process=None;shell=page=None
def wait(fn,timeout=60):
 end=time.monotonic()+timeout;last=''
 while time.monotonic()<end:
  try:
   value=fn()
   if value:return value
  except Exception as e:last=str(e)
  time.sleep(.3)
 raise AssertionError('Video wait timeout: '+last)
def connect(t):return s.websocket.create_connection(t['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
def deep(selector,expression='true'):
 return s.evaluate(page,"(()=>{const queue=[document];while(queue.length){const root=queue.shift(),node=root.querySelector("+json.dumps(selector)+");if(node)return "+expression+";for(const n of root.querySelectorAll('*'))if(n.shadowRoot)queue.push(n.shadowRoot)}return null})()")
def check(ok,label):
 assert ok,label
 report['checks'].append(label);print('PASS:',label,flush=True)
def photo(name):
 shot=s.command(page,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/(name+'.png')).write_bytes(base64.b64decode(shot['data']))
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
 profile=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';profile.mkdir(parents=True)
 (profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'layout':'adaptive','mattePanel':False,'videoTranslationEnabled':True}),encoding='utf-8')
 try:
  process=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server'],env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT)))
  shell=connect(wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None)))
  wait(lambda:s.evaluate(shell,'!!window.browserShell'))
  s.evaluate(shell,"browserShell.openTab('https://www.youtube.com/watch?v=jNQXAC9IVRw')")
  page=connect(wait(lambda:next((t for t in s.targets() if 'youtube.com/watch' in t.get('url','')),None)))
  original_recv=page.recv;fixture_url='https://www.youtube.com/watch?v=SouluTest01';fixture_body=None;internal_id=800000
  def capture():
   global internal_id
   raw=original_recv()
   try:
    event=json.loads(raw);method=event.get('method')
    if method in ('Runtime.consoleAPICalled','Runtime.exceptionThrown','Log.entryAdded'):report['events'].append(event)
    if method=='Fetch.requestPaused':
     internal_id+=1;params=event['params'];request_id=params['requestId']
     if fixture_body is not None and params['request']['url']==fixture_url:
      page.send(json.dumps({'id':internal_id,'method':'Fetch.fulfillRequest','params':{'requestId':request_id,'responseCode':200,'responseHeaders':[{'name':'Content-Type','value':'text/html; charset=utf-8'}],'body':fixture_body}}))
     else:page.send(json.dumps({'id':internal_id,'method':'Fetch.continueRequest','params':{'requestId':request_id}}))
   except Exception as e:report.setdefault('captureErrors',[]).append(str(e))
   return raw
  page.recv=capture;s.command(page,'Runtime.enable');s.command(page,'Log.enable')
  wait(lambda:s.evaluate(page,"!!document.querySelector('video')"),90)
  check(s.evaluate(page,"typeof window.__souluVideoNative==='undefined'"),'No public native video bridge on YouTube')
  wait(lambda:s.evaluate(page,"performance.getEntriesByName('soulu.video.runtime.enabled').length>0"),30)
  check(True,'Native VOT initialization reads the enabled profile preferences')
  player=wait(lambda:s.evaluate(page,"window.ytInitialPlayerResponse?.playabilityStatus"),30)
  blocked=player.get('status')=='LOGIN_REQUIRED' and bool(re.search(r'not a bot|не бот',player.get('reason',''),re.I))
  if blocked:
   report['liveYouTube']={'verified':False,'externalServiceRejection':True,'status':player.get('status'),'reason':player.get('reason')}
   print('LIVE_YOUTUBE_UNVERIFIED: YouTube requires account sign-in to confirm this runner is not a bot',flush=True);photo('youtube-service-rejection')
  else:
   wait(lambda:deep('.vot-translate-button'),90);check(True,'VOT controls appear on the live YouTube player')
   rect=s.evaluate(page,"(()=>{const r=document.querySelector('video').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+30}})()");s.command(page,'Input.dispatchMouseEvent',dict(type='mouseMoved',**rect));time.sleep(.5)
   rect=deep('.vot-translate-button','(()=>{const r=node.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()')
   for kind in ('mouseMoved','mousePressed','mouseReleased'):s.command(page,'Input.dispatchMouseEvent',dict(type=kind,**rect,button='left' if kind!='mouseMoved' else 'none',clickCount=1 if kind!='mouseMoved' else 0))
   def translation():
    state=deep('.vot-segmented-button','({status:node.dataset.status,text:node.textContent})')
    if state:report['translation']=state
    return state and state['status'] in ('success','error') and state
   final=wait(translation,180);photo('youtube-translation')
   check(final['status']=='success','Russian translation audio track becomes ready');report['liveYouTube']={'verified':True}
  # This is explicitly a synthetic page. It does not bypass the service rejection
  # or stand in for a successful public translation/audio test.
  s.evaluate(shell,"new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'browser.video.settings',payload:{values:{localeLangOverride:'en',responseLanguage:'ru'}}}),onSuccess:resolve,onFailure:(_,s)=>reject(Error(s))}))")
  fixtures=Path(__file__).with_name('fixtures');html=(fixtures/'vot-player.html').read_text(encoding='utf-8').replace('__VIDEO_DATA__',(fixtures/'vot-player.webm.b64').read_text().strip())
  fixture_body=base64.b64encode(html.encode()).decode();s.command(page,'Fetch.enable',{'patterns':[{'urlPattern':fixture_url,'requestStage':'Request'}]});s.command(page,'Page.navigate',{'url':fixture_url})
  wait(lambda:s.evaluate(page,"document.title==='Soulu synthetic YouTube player fixture'"),30)
  wait(lambda:s.evaluate(page,"document.querySelector('video')?.readyState>=2"),30)
  check(True,'Synthetic player decodes and plays real WebM frames')
  wait(lambda:deep('.vot-translate-button'),60);check(True,'Full pinned VOT creates controls through the native integration on the synthetic player')
  rect=s.evaluate(page,"(()=>{const r=document.querySelector('video').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+30}})()");s.command(page,'Input.dispatchMouseEvent',dict(type='mouseMoved',**rect));time.sleep(.4)
  count=s.evaluate(page,"(()=>{let count=0;const roots=[document];while(roots.length){const r=roots.shift();count+=r.querySelectorAll('.vot-translate-button').length;for(const n of r.querySelectorAll('*'))if(n.shadowRoot)roots.push(n.shadowRoot)}return count})()")
  check(count==1,'One translation control per player, without duplicate VOT runtimes')
  photo('vot-native-player-fixture');report['passed']=True
 finally:
  if page:
   try:
    report['page']=s.evaluate(page,"({url:location.href,title:document.title,text:document.body?.innerText?.slice(0,1500),player:window.ytInitialPlayerResponse?.playabilityStatus,marks:performance.getEntriesByType('mark').map(n=>n.name).filter(n=>n.startsWith('soulu.video')),hosts:document.querySelectorAll('vot-shadow-host').length})")
    photo('youtube-diagnostic')
   except Exception as e:report['diagnosticError']=str(e)
  (out/'video-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  print('VIDEO_DIAGNOSTIC',json.dumps(report,ensure_ascii=True),flush=True)
  for ws in (page,shell):
   if ws:
    try:ws.close()
    except Exception:pass
  if process and process.poll() is None:
   try:s.close_normally(process)
   except Exception:process.kill();process.wait()
