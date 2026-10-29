"""Native shell regression for tooltips, selects and pointer focus."""
import base64,json,os,sys,tempfile,subprocess,time,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1';os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
def wait(fn,timeout=45):
 end=time.monotonic()+timeout;last=''
 while time.monotonic()<end:
  try:
   value=fn()
   if value:return value
  except Exception as e:last=str(e)
  time.sleep(.1)
 raise AssertionError('Native UI wait timeout: '+last)
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);report={'checks':[]};shell=page=settings=None;p=None
def check(value,label):
 assert value,label
 report['checks'].append(label);print('PASS:',label,flush=True)
def connect(target):return s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as root:
 profile=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';profile.mkdir(parents=True);(profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'theme':'light','layout':'adaptive','mattePanel':False,'newTabMode':'soulu'}))
 try:
  p=subprocess.Popen([str(Path(sys.argv[1]).resolve()),'--no-proxy-server'],env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT)))
  shell=connect(wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None)))
  wait(lambda:s.evaluate(shell,"!!window.browserShell&&document.documentElement.classList.contains('typography-ready')"))
  s.evaluate(shell,'browserShell.newTab()');time.sleep(.5)
  point=s.evaluate(shell,"(()=>{const r=document.querySelector('.classic-tab.active').getBoundingClientRect();return {x:r.left+Math.min(50,r.width/2),y:r.top+r.height/2}})()")
  s.command(shell,'Input.dispatchMouseEvent',dict(type='mouseMoved',x=point['x'],y=point['y']));time.sleep(.7)
  box=wait(lambda:s.evaluate(shell,"(()=>{const n=document.querySelector('.soulu-type-tooltip');if(!n||n.hidden)return null;const r=n.getBoundingClientRect();return {bottom:r.bottom,height:r.height,viewport:innerHeight}})()"))
  check(box['height']>10 and box['bottom']+4<=box['viewport'],'Tab title tooltip fits inside the expanded native shell viewport')
  check(s.evaluate(shell,"document.querySelectorAll('.soulu-tooltip').length===0"),'One tooltip implementation')
  s.command(shell,'Input.dispatchMouseEvent',dict(type='mouseMoved',x=1,y=1))
  page=connect(wait(lambda:next((t for t in s.targets() if '/ui/home.html' in t.get('url','')),None)))
  point=s.evaluate(page,"(()=>{const r=document.querySelector('#favoritesToggle').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
  for kind in ('mouseMoved','mousePressed','mouseReleased'):
   s.command(page,'Input.dispatchMouseEvent',dict(type=kind,x=point['x'],y=point['y'],button='left' if kind!='mouseMoved' else 'none',clickCount=1 if kind!='mouseMoved' else 0))
  time.sleep(.6);check(s.evaluate(page,"document.activeElement!==document.querySelector('#favoritesGrid a')"),'Pointer app-grid opening does not focus YouTube')
  s.evaluate(shell,"browserShell.openSettingsWindow()")
  settings=connect(wait(lambda:next((t for t in s.targets() if '/ui/settings.html' in t.get('url','')),None)))
  wait(lambda:s.evaluate(settings,"document.body.classList.contains('ready')"))
  for section in ('general','interface','startup','search','privacy','reading'):
   s.evaluate(settings,'souluSettings.openSection('+json.dumps(section)+')');time.sleep(.2)
   check(s.evaluate(settings,"[...document.querySelectorAll('#sectionContent select')].filter(x=>!x.disabled).every(x=>x.classList.contains('soulu-select-source')&&x.parentElement.querySelector('.soulu-select-button'))"),section+': Soulu dropdowns')
  s.evaluate(settings,"souluSettings.openSection('interface')");time.sleep(.2)
  s.evaluate(settings,"document.querySelector('#addressPosition').parentElement.querySelector('button').click()")
  wait(lambda:s.evaluate(settings,"!!document.querySelector('.soulu-select-menu:popover-open')"))
  check(s.evaluate(settings,"(()=>{const r=document.querySelector('.soulu-select-menu:popover-open').getBoundingClientRect();return r.left>=0&&r.top>=0&&r.bottom<=innerHeight&&r.right<=innerWidth})()"),'Dropdown stays inside settings viewport')
  shot=s.command(settings,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'dropdown-light.png').write_bytes(base64.b64decode(shot['data']))
  s.evaluate(settings,"document.querySelector('.soulu-select-menu:popover-open .soulu-select-option').click()")
  wait(lambda:s.evaluate(settings,"souluSettings.persisted.settings.addressPosition==='left'"));check(True,'Custom selection persists')
  s.evaluate(settings,"souluSettings.openSection('vpn')");time.sleep(.2);check(s.evaluate(settings,"!!document.querySelector('#vpn-directDomains')"),'Direct VPN routing UI')
  s.evaluate(settings,"(()=>{const n=document.querySelector('#vpn-directDomains');n.value='https://Example.COM/path\\n*.bank.example\\nexample.com';n.dispatchEvent(new Event('change',{bubbles:true}))})()")
  wait(lambda:s.evaluate(settings,"souluSettings.persisted.vpn.directDomains==='example.com\\nbank.example'"))
  check(True,'Routing domains normalize, deduplicate and persist through the native settings store')
  s.evaluate(settings,"souluSettings.openSection('reading')");time.sleep(.2)
  check(s.evaluate(settings,"document.querySelector('#videoTranslationEnabled').checked"),'Video Translate is enabled by default')
  s.evaluate(settings,"souluVideoSettings.open()")
  wait(lambda:s.evaluate(settings,"document.querySelector('#actionDialog').open&&document.querySelectorAll('#actionContent .row').length>=40"))
  check(True,'Video Translate options are available inside Reading and translation')
  s.evaluate(settings,"document.querySelector('#closeAction').click();souluSettings.openSection('about')")
  wait(lambda:s.evaluate(settings,"[...document.querySelectorAll('.component-card')].every(n=>n.textContent.includes('Установлена: v'))"))
  check(s.evaluate(settings,"document.querySelectorAll('.component-card').length===2"),'About shows installed Xray and Sudoku')
  s.evaluate(settings,"souluSettings.openSection('startup');souluWeatherKey.open()")
  wait(lambda:s.evaluate(settings,"document.querySelector('#actionDialog').open&&!!document.querySelector('#actionContent input[type=password]')"))
  check(s.evaluate(settings,"document.querySelector('#actionContent input').value===''"),'Weather API key is never returned to the password field')
  s.evaluate(settings,"document.querySelector('#closeAction').click();souluSettings.openSection('interface');document.querySelector('input[name=settings-theme][value=dark]').click()")
  wait(lambda:s.evaluate(settings,"souluSettings.persisted.settings.theme==='dark'"))
  s.evaluate(settings,"document.querySelector('#addressPosition').parentElement.querySelector('button').click()")
  wait(lambda:s.evaluate(settings,"!!document.querySelector('.soulu-select-menu:popover-open')"))
  check(s.evaluate(settings,"getComputedStyle(document.querySelector('.soulu-select-menu:popover-open')).backgroundColor!=='rgb(252, 252, 253)'"),'Dropdown follows the dark theme')
  shot=s.command(settings,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'dropdown-dark.png').write_bytes(base64.b64decode(shot['data']))
  report['passed']=True
 finally:
  for ws in (settings,page,shell):
   if ws:
    try:ws.close()
    except Exception:pass
  if p and p.poll() is None:
   try:s.close_normally(p)
   except Exception:p.kill();p.wait()
  (out/'evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
