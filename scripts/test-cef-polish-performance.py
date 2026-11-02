"""Native regressions for reported 1.0.72 UI issues and background lifecycle policy."""
import base64,ctypes,http.server,importlib.util,json,os,subprocess,sys,tempfile,threading,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('daily',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['NO_PROXY']='localhost,127.0.0.1,::1';os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
checks=[];sockets=[];passed=False
def wait(fn,timeout=30):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   result=fn()
   if result:return result
  except Exception as error:last=repr(error)
  time.sleep(.1)
 raise AssertionError('Polish/performance timeout: '+str(last))
def connect(part):
 target=wait(lambda:next((t for t in s.targets() if part in t.get('url','')),None));ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE);sockets.append(ws);return ws
def check(value,label):
 assert value,label
 checks.append(label);print('PASS:',label,flush=True)
def click(ws,selector):
 pos=wait(lambda:s.evaluate(ws,'(()=>{const n=document.querySelector('+json.dumps(selector)+');if(!n)return null;const r=n.getBoundingClientRect();return r.width&&r.height?{x:r.x+r.width/2,y:r.y+r.height/2}:null})()'))
 for kind in ['mousePressed','mouseReleased']:s.command(ws,'Input.dispatchMouseEvent',dict(type=kind,button='left',clickCount=1,**pos))
class Fixture(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  body=b'<title>Lifecycle fixture</title><input id="draft"><button id="outside">Outside</button><script>window.ticks=0;window.identity=Math.random();setInterval(()=>ticks++,40)</script>'
  self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Fixture);threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}';out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='soulu-polish-',ignore_cleanup_errors=True) as root:
 config=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';config.mkdir(parents=True)
 (config/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'layout':'adaptive','theme':'light','startupMode':'soulu','newTabMode':'blank','mattePanel':False,'bookmarksBarMode':'never'}))
 # GetModuleFileName and Chromium canonical file URLs differ when this path has Unicode/spaces.
 alias=Path(root)/'Soulu тест';runtime=Path(sys.argv[1]).resolve().parent
 subprocess.run(['cmd','/c','mklink','/J',str(alias),str(runtime)],check=True,capture_output=True)
 process=subprocess.Popen([str(alias/Path(sys.argv[1]).name),'--no-proxy-server'],env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT)))
 try:
  shell=connect('/ui/index.html');home=connect('/ui/home.html');state=lambda:s.evaluate(shell,'browserShell.getState()')
  wait(lambda:s.evaluate(shell,"document.documentElement.classList.contains('typography-ready')&&!!window.browserShell"))
  wait(lambda:s.evaluate(home,"typeof souluHomeApply==='function'&&document.readyState==='complete'"))
  check(state()['page']['url']=='soulu://home' and not state()['page']['loading'],'Unicode/space installation path canonicalizes Home without permanent loading')
  # Compare every VPN state with actual hover and pressed styling applied.
  baseline=s.evaluate(shell,"document.querySelector('#vpnButton').getBoundingClientRect().y")
  s.command(shell,'DOM.enable');doc=s.command(shell,'DOM.getDocument')['root']['nodeId'];node=s.command(shell,'DOM.querySelector',{'nodeId':doc,'selector':'#vpnButton'})['nodeId'];s.command(shell,'CSS.enable')
  for status in ['connecting','connected','disconnecting','disconnected']:
   s.evaluate(shell,'updateVpnState({state:'+json.dumps(status)+'})')
   for pseudo in [[],['hover'],['active'],['hover','active']]:
    s.command(shell,'CSS.forcePseudoState',{'nodeId':node,'forcedPseudoClasses':pseudo})
    check(abs(s.evaluate(shell,"document.querySelector('#vpnButton').getBoundingClientRect().y")-baseline)<.5,'VPN stays at the same Y in '+status+' / '+','.join(pseudo))
  s.command(shell,'CSS.forcePseudoState',{'nodeId':node,'forcedPseudoClasses':[]})
  s.evaluate(shell,'browserShell.openSettingsWindow()');settings=connect('/ui/settings.html');wait(lambda:s.evaluate(settings,"document.body.classList.contains('ready')"))
  keys=s.evaluate(settings,"[...document.querySelectorAll('#homeCards [data-section]')].map(n=>n.dataset.section)")
  check(len(keys)==12 and all(k in keys for k in ['extensions','translation','performance']),'Twelve sections include Extensions, Translation and Performance')
  s.evaluate(settings,"souluSettings.openSection('reading')")
  check(not s.evaluate(settings,"!!document.querySelector('#videoTranslationEnabled')||!!document.querySelector('#translationTarget')"),'Reader mode contains no translation controls')
  s.evaluate(settings,"souluSettings.openSection('translation')")
  check(s.evaluate(settings,"!!document.querySelector('#videoTranslationEnabled')&&!!document.querySelector('#translationTarget')"),'Page and YouTube translation controls moved together')
  check(s.evaluate(settings,"document.querySelector('#settingsTitle').textContent==='Перевод'"),'Translation section has the correct heading')
  s.evaluate(settings,"souluSettings.openSection('interface')")
  s.evaluate(settings,"document.querySelector('#showHome').click();souluSettings.flush()")
  wait(lambda:s.evaluate(shell,"[...document.querySelectorAll('[data-home]')].every(n=>!n.getClientRects().length)"));check(True,'Home button can be hidden through persisted Settings')
  s.evaluate(settings,"document.querySelector('#showHome').click();souluSettings.flush()")
  wait(lambda:s.evaluate(shell,"document.querySelector('.classic-toolbar [data-home]').getClientRects().length>0"))
  nav=s.evaluate(settings,"document.querySelector('[data-section=interface]').getBoundingClientRect().toJSON()")
  s.command(settings,'Input.dispatchMouseEvent',{'type':'mouseMoved','x':nav['x']+15,'y':nav['y']+15});time.sleep(.6)
  check(s.evaluate(settings,"!document.querySelector('.soulu-type-tooltip').hidden&&![...document.querySelectorAll('[title]')].some(n=>n.title)"),'Settings hover has one custom tooltip and no competing native titles')
  shot=s.command(settings,'Page.captureScreenshot',{'format':'png'});(out/'settings-tooltip.png').write_bytes(base64.b64decode(shot['data']))
  s.evaluate(settings,'souluSettingsRequestClose()');wait(lambda:not state()['settingsOverlayOpen'])
  s.evaluate(shell,'browserShell.navigate('+json.dumps(origin+'/first')+')');page=connect('/first');wait(lambda:s.evaluate(page,'typeof identity==="number"'))
  click(shell,'#classicAddress');wait(lambda:s.evaluate(shell,"!!document.querySelector('.suggestions.visible')"))
  click(shell,'#sidebarButton');wait(lambda:not s.evaluate(shell,"!!document.querySelector('.suggestions.visible')"));check(True,'Address suggestions close on another toolbar control')
  s.evaluate(shell,"window.__addressEvents=[];for(const type of ['focus','blur','pointerdown','click','soulu-dismiss-address'])window.addEventListener(type,e=>__addressEvents.push({type,target:e.target?.id,active:document.activeElement?.id,focus:document.hasFocus(),value:document.querySelector('#classicAddress')?.value,at:performance.now()}),true);browserShell.toggleSidebar()")
  click(shell,'#classicAddress');time.sleep(3)
  print('ADDRESS DIAGNOSTIC:',s.evaluate(shell,"JSON.stringify({events:window.__addressEvents,active:document.activeElement?.id,focus:document.hasFocus(),sidebar:document.querySelector('.sidebar')?.getBoundingClientRect().toJSON(),address:document.querySelector('#classicAddress')?.getBoundingClientRect().toJSON(),value:document.querySelector('#classicAddress')?.value,visible:!!document.querySelector('.suggestions.visible'),layout:document.body.dataset.layout})"),flush=True)
  wait(lambda:s.evaluate(shell,"!!document.querySelector('.suggestions.visible')"))
  # Deliver the same native deactivation message Windows sends for a desktop/other-app click.
  hwnds=[];u=ctypes.windll.user32
  @ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
  def enum(hwnd,_):
   pid=ctypes.c_ulong();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));name=ctypes.create_unicode_buffer(128);u.GetClassNameW(hwnd,name,128)
   if pid.value==process.pid and name.value=='SouluBrowserWindow':hwnds.append(hwnd)
   return True
  u.EnumWindows(enum,0);assert hwnds
  u.SendMessageW(ctypes.c_void_p(hwnds[0]),0x0006,0,0)
  wait(lambda:not s.evaluate(shell,"!!document.querySelector('.suggestions.visible')"));time.sleep(2)
  check(not s.evaluate(shell,"!!document.querySelector('.suggestions.visible')"),'Native deactivation dismisses suggestions and delayed network results do not reopen them')
  first=state()['activeTabId'];original=s.evaluate(page,"document.querySelector('#draft').value='Unsent text';({identity,ticks})")
  s.evaluate(shell,'browserShell.newTab()');wait(lambda:len(state()['tabs'])==2)
  second=state()['activeTabId'];s.evaluate(shell,'browserShell.navigate('+json.dumps(origin+'/second')+')');other=connect('/second');wait(lambda:s.evaluate(other,'typeof identity==="number"'))
  wait(lambda:not state()['adaptiveToolbar']['running'])
  s.evaluate(shell,'browserShell.setSettings({freezeBackgroundTabs:true,memorySaver:true,performanceMode:"balanced"})')
  s.evaluate(page,"window.__lifecycleEvents=[];for(const kind of ['freeze','resume','visibilitychange'])document.addEventListener(kind,()=>__lifecycleEvents.push({kind,ticks,visibility:document.visibilityState,at:performance.now()}))")
  s.evaluate(shell,'browserShell.optimizeBackgroundTabs()')
  try:wait(lambda:next(t for t in state()['tabs'] if t['id']==first).get('suspended'))
  except Exception:
   print('LIFECYCLE_FAILURE_STATE',json.dumps(state()),flush=True)
   print('LIFECYCLE_PAGE',s.evaluate(page,'({visibility:document.visibilityState,ticks})'),flush=True)
   raise
  check(not next(t for t in state()['tabs'] if t['id']==second).get('suspended'),'Manual optimization pauses only a background tab')
  print('LIFECYCLE BEFORE',s.evaluate(page,'({visibility:document.visibilityState,ticks,events:window.__lifecycleEvents})'),flush=True)
  for _ in range(4):
   time.sleep(.3);print('LIFECYCLE SAMPLE',s.evaluate(page,'({visibility:document.visibilityState,ticks,events:window.__lifecycleEvents})'),flush=True)
  print('DIRECT FREEZE',s.command(page,'Page.setWebLifecycleState',{'state':'frozen'}),flush=True)
  for _ in range(4):
   time.sleep(.3);print('DIRECT SAMPLE',s.evaluate(page,'({visibility:document.visibilityState,ticks,events:window.__lifecycleEvents})'),flush=True)
  before=s.evaluate(page,'ticks');time.sleep(.6);check(s.evaluate(page,'ticks')==before,'Paused tab actually stops JavaScript timers')
  s.evaluate(shell,f'browserShell.switchTab({first})');wait(lambda:not next(t for t in state()['tabs'] if t['id']==first).get('suspended'));wait(lambda:s.evaluate(page,'ticks')>before)
  check(s.evaluate(page,'identity')==original['identity'] and s.evaluate(page,"document.querySelector('#draft').value")=='Unsent text','Opening a paused tab resumes without reload or loss of form data')
  s.evaluate(shell,f'browserShell.pinTab({first});browserShell.switchTab({second})');s.evaluate(shell,'browserShell.optimizeBackgroundTabs()');time.sleep(.4)
  check(not next(t for t in state()['tabs'] if t['id']==first).get('suspended'),'Pinned tabs are protected from optimization')
  s.evaluate(shell,f'browserShell.pinTab({first})');s.evaluate(shell,'browserShell.setSettings({performanceExclusions:"127.0.0.1"})');s.evaluate(shell,'browserShell.optimizeBackgroundTabs()');time.sleep(.4)
  check(not next(t for t in state()['tabs'] if t['id']==first).get('suspended'),'Always-active domain exclusions are enforced natively')
  s.evaluate(shell,'browserShell.setSettings({performanceExclusions:"",performanceMode:"performance"})');s.evaluate(shell,'browserShell.optimizeBackgroundTabs()');time.sleep(.4)
  check(not next(t for t in state()['tabs'] if t['id']==first).get('suspended'),'Maximum performance mode keeps background tabs running')
  # Keep the address and retained sibling tabs stable through closing a third tab.
  wait(lambda:s.evaluate(shell,"!!document.querySelector('#tabStrip [data-tab-id=\""+str(first)+"\"]:not(.pinned):not(.active)')&&!!document.querySelector('#tabStrip [data-tab-id=\""+str(second)+"\"].active')"))
  s.evaluate(shell,"window.retained=document.querySelector('#tabStrip [data-tab-id=\""+str(first)+"\"]');window.retainedMarkup=retained?.tabMarkup;window.addressY=document.querySelector('#classicAddressForm').getBoundingClientRect().y")
  s.evaluate(shell,'browserShell.newTab()');third=state()['activeTabId'];s.evaluate(shell,f'browserShell.closeTab({third})');wait(lambda:len(state()['tabs'])==2)
  wait(lambda:s.evaluate(shell,"document.querySelectorAll('#tabStrip .classic-tab').length===2"))
  check(state()['activeTabId']==second,'Closing the active tab selects its adjacent sibling rather than the first tab')
  print('RETAINED_NODE',s.evaluate(shell,"({same:retained===document.querySelector('#tabStrip [data-tab-id=\""+str(first)+"\"]'),before:retainedMarkup,after:document.querySelector('#tabStrip [data-tab-id=\""+str(first)+"\"]')?.tabMarkup})"),flush=True)
  check(s.evaluate(shell,"retained===document.querySelector('#tabStrip [data-tab-id=\""+str(first)+"\"]')"),'Closing a tab preserves unchanged sibling DOM nodes')
  s.evaluate(shell,f'browserShell.closeTab({first})');wait(lambda:len(state()['tabs'])==1 and not state()['adaptiveToolbar']['running'])
  check(abs(s.evaluate(shell,"document.querySelector('#classicAddressForm').getBoundingClientRect().y-addressY"))<.5,'Address and VPN row do not jump vertically when the last extra tab closes')
  s.evaluate(shell,'browserShell.setBookmarksSidebar(true)');wait(lambda:s.evaluate(shell,"!document.querySelector('.bookmarks-menu').hidden"))
  check(s.evaluate(shell,"document.querySelector('.bookmarks-heading').querySelectorAll('button').length===0"),'Bookmark panel has no close cross')
  check(s.evaluate(shell,"[...document.querySelectorAll('.bookmark-actions button')].filter(n=>n.textContent.includes('Добавить текущую')).every(n=>{const t=document.createRange();t.selectNodeContents(n);return t.getClientRects().length<=2})"),'Add current page occupies at most two text lines')
  shot=s.command(shell,'Page.captureScreenshot',{'format':'png'});(out/'bookmarks.png').write_bytes(base64.b64decode(shot['data']));passed=True
 finally:
  for ws in sockets:
   try:ws.close()
   except Exception:pass
  s.close_normally(process);server.shutdown()
  (out/'evidence.json').write_text(json.dumps({'passed':passed,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
