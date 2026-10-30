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
  s.evaluate(shell,"browserShell.setSettings({vpnToolbarVisible:true});document.querySelector('#vpnButton').click()")
  settings=connect(wait(lambda:next((t for t in s.targets() if '/ui/settings.html' in t.get('url','')),None)))
  wait(lambda:s.evaluate(settings,"document.body.classList.contains('ready')"))
  s.evaluate(settings,"Promise.resolve(window.souluSelectReady)")
  check(s.evaluate(settings,"document.querySelector('#sectionNav [data-section=vpn]').classList.contains('active')"),'A toolbar click without a key opens VPN Settings directly')
  for section in ('general','interface','startup','search','privacy','reading'):
   s.evaluate(settings,'souluSettings.openSection('+json.dumps(section)+')');time.sleep(.2)
   check(s.evaluate(settings,"[...document.querySelectorAll('#sectionContent select')].filter(x=>!x.disabled).every(x=>x.classList.contains('soulu-select-source')&&x.parentElement.querySelector('.soulu-select-button'))"),section+': Soulu dropdowns')
  s.evaluate(settings,"souluSettings.openSection('interface')");time.sleep(.2)
  s.evaluate(settings,"document.querySelector('#addressPosition').parentElement.querySelector('button').click()")
  wait(lambda:s.evaluate(settings,"!!document.querySelector('.soulu-select-menu:popover-open')"))
  bounds=s.evaluate(settings,"(()=>{const n=document.querySelector('.soulu-select-menu:popover-open'),r=n.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:innerWidth,height:innerHeight,style:n.getAttribute('style')}})()")
  print('DROPDOWN_BOUNDS',json.dumps(bounds),flush=True)
  check(bounds['left']>=0 and bounds['top']>=0 and bounds['bottom']<=bounds['height'] and bounds['right']<=bounds['width'],'Dropdown stays inside settings viewport')
  shot=s.command(settings,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'dropdown-light.png').write_bytes(base64.b64decode(shot['data']))
  s.evaluate(settings,"document.querySelector('.soulu-select-menu:popover-open .soulu-select-option').click()")
  wait(lambda:s.evaluate(settings,"souluSettings.persisted.settings.addressPosition==='left'"));check(True,'Custom selection persists')
  s.evaluate(settings,"souluSettings.openSection('vpn')");time.sleep(.2);check(s.evaluate(settings,"!!document.querySelector('#vpn-directDomains')"),'Direct VPN routing UI')
  s.evaluate(settings,"(()=>{const n=document.querySelector('#vpn-directDomains');n.value='https://Example.COM/path\\n*.bank.example\\nexample.com';n.dispatchEvent(new Event('change',{bubbles:true}))})()")
  wait(lambda:s.evaluate(settings,"souluSettings.persisted.vpn.directDomains==='example.com\\nbank.example'"))
  check(True,'Routing domains normalize, deduplicate and persist through the native settings store')
  for protocol,key in [('sudoku','sudoku://'+base64.urlsafe_b64encode(json.dumps({'h':'127.0.0.1','p':443,'k':'ab'*32,'hd':True}).encode()).decode().rstrip('=')),('vless','vless://12345678-1234-1234-1234-123456789abc@127.0.0.1:443?security=none&type=tcp')]:
   s.evaluate(settings,"document.querySelector('#vpn-profile-key').value="+json.dumps('  '+key+'  ')+";document.querySelector('#vpn-profile-save').click()")
   wait(lambda:s.evaluate(settings,"souluSettings.persisted.vpn.profiles.some(p=>p.link==="+json.dumps(key)+")"))
   s.evaluate(settings,"(()=>{const p=souluSettings.persisted.vpn.profiles.find(p=>p.link==="+json.dumps(key)+");document.querySelector('input[name=vpn-default-profile][value=\"'+p.id+'\"]').click()})()")
   wait(lambda:s.evaluate(settings,"souluSettings.persisted.vpn.protocol==="+json.dumps(protocol)+"&&souluSettings.persisted.vpn.link==="+json.dumps(key)))
   check(s.evaluate(settings,"souluSettings.persisted.vpn.profiles.some(p=>p.protocol==="+json.dumps(protocol)+"&&p.link==="+json.dumps(key)+")"),'VPN recognizes and saves '+protocol+' keys without connecting')
  check(s.evaluate(settings,"souluSettings.persisted.vpn.profiles.length===2"),'Both protocol keys remain saved when the default changes')
  def click_toolbar(selector):
   point=s.evaluate(shell,"(()=>{const r=document.querySelector("+json.dumps(selector)+").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
   for kind in ('mousePressed','mouseReleased'):s.command(shell,'Input.dispatchMouseEvent',dict(point,type=kind,button='left',clickCount=1))
  s.evaluate(settings,'souluSettingsRequestClose()');wait(lambda:not s.evaluate(shell,'browserShell.getState().then(s=>s.settingsOverlayOpen)'))
  s.evaluate(shell,"browserShell.setSettings({layout:'adaptive',addressPosition:'center',extensionsPosition:'right',vpnToolbarVisible:true})")
  wait(lambda:s.evaluate(shell,"document.body.dataset.layout==='adaptive'&&document.body.dataset.addressPosition==='center'"))
  geometry=s.evaluate(shell,"(()=>{const b=document.querySelector('#vpnButton'),r=b.getBoundingClientRect(),a=document.querySelector('#classicAddressForm').getBoundingClientRect();return {left:r.left,right:r.right,address:a.left,glyph:b.querySelector('svg').getBoundingClientRect().width,color:getComputedStyle(b).color,other:getComputedStyle(document.querySelector('#newTabButton')).color}})()")
  check(geometry['right']<=geometry['address']-3 and geometry['address']-geometry['right']<14 and geometry['glyph']==18 and geometry['color']==geometry['other'],'Connect mark sits immediately left of the address and matches other toolbar glyphs')
  check(s.evaluate(shell,"!document.querySelector('#vpnPanel,#vpnFrame')"),'No legacy VPN side panel or iframe')
  shot=s.command(shell,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'vpn-toolbar-off.png').write_bytes(base64.b64decode(shot['data']))
  click_toolbar('#vpnButton');wait(lambda:s.evaluate(shell,"document.querySelector('#vpnButton').classList.contains('connected')"))
  wait(lambda:s.evaluate(shell,"vpn.send('status').then(s=>s.connected)"))
  # The shared toolbar animates color. Class changes precede the first painted
  # frame, so checking equality immediately can observe the previous off color.
  wait(lambda:s.evaluate(shell,"getComputedStyle(document.querySelector('#vpnButton')).color==='rgb(8, 127, 91)'"))
  check(True,'One click starts the saved VLESS core and turns the mark green')
  check(not s.evaluate(shell,'browserShell.getState().then(s=>s.settingsOverlayOpen)'),'Configured toolbar connection opens no settings or extra interface')
  shot=s.command(shell,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'vpn-toolbar-on.png').write_bytes(base64.b64decode(shot['data']))
  click_toolbar('#vpnButton');wait(lambda:not s.evaluate(shell,"document.querySelector('#vpnButton').classList.contains('connected')"))
  check(not s.evaluate(shell,"vpn.send('status').then(s=>s.connected)"),'Second click stops the local VPN core')
  s.evaluate(shell,"browserShell.openSettingsWindow('vpn')")
  settings.close();settings=connect(wait(lambda:next((t for t in s.targets() if '/ui/settings.html' in t.get('url','')),None)))
  wait(lambda:s.evaluate(settings,"document.body.classList.contains('ready')&&!!document.querySelector('#vpn-profile-key')"))
  s.evaluate(settings,"(()=>{const p=souluSettings.persisted.vpn.profiles.find(p=>p.protocol==='sudoku');document.querySelector('input[name=vpn-default-profile][value=\"'+p.id+'\"]').click()})()")
  wait(lambda:s.evaluate(settings,"souluSettings.persisted.vpn.protocol==='sudoku'"))
  shot=s.command(settings,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(out/'vpn-profiles.png').write_bytes(base64.b64decode(shot['data']))
  sudoku_id=s.evaluate(settings,'souluSettings.persisted.vpn.defaultProfileId')
  s.evaluate(settings,'souluSettingsRequestClose()');wait(lambda:not s.evaluate(shell,'browserShell.getState().then(s=>s.settingsOverlayOpen)'))
  s.evaluate(shell,"browserShell.setSettings({layout:'compact',extensionsPosition:'right'})");wait(lambda:s.evaluate(shell,"document.body.dataset.layout==='compact'"))
  check(s.evaluate(shell,"(()=>{const b=document.querySelector('#compactVpnButton').getBoundingClientRect(),a=document.querySelector('#compactTabFlow').getBoundingClientRect();return b.right<=a.left&&a.left-b.right<12})()"),'Compact VPN mark also remains immediately left regardless of the old extension-side preference')
  click_toolbar('#compactVpnButton');wait(lambda:s.evaluate(shell,"vpn.send('status').then(s=>s.connected&&s.activeProfileId==="+json.dumps(sudoku_id)+")"))
  check(True,'The selected Sudoku key is used by the one-click toolbar action')
  s.evaluate(shell,"browserShell.openSettingsWindow('vpn')");settings.close();settings=connect(wait(lambda:next((t for t in s.targets() if '/ui/settings.html' in t.get('url','')),None)))
  wait(lambda:s.evaluate(settings,"document.body.classList.contains('ready')&&!!document.querySelector('#vpn-profile-key')"))
  s.evaluate(settings,"document.querySelector('[data-vpn-profile=\""+sudoku_id+"\"] .vpn-profile-row-actions button:last-child').click()")
  wait(lambda:s.evaluate(settings,"souluSettings.persisted.vpn.profiles.length===1&&souluSettings.persisted.vpn.protocol==='vless'"))
  wait(lambda:not s.evaluate(shell,"vpn.send('status').then(s=>s.connected)"))
  check(True,'Deleting the active key disconnects VPN and retains the other saved key')
  saved=json.loads((Path(root)/'Soulu'/'User Data'/'settings.json').read_text())['vpn']
  check(len(saved['profiles'])==1 and saved['defaultProfileId']==saved['lastProfileId'],'Saved list and default are written to the native persistent store')
  s.evaluate(settings,"souluSettings.openSection('reading')");time.sleep(.2)
  check(s.evaluate(settings,"document.querySelector('#videoTranslationEnabled').checked"),'Video Translate is enabled by default')
  s.evaluate(settings,"souluVideoSettings.open()")
  wait(lambda:s.evaluate(settings,"document.querySelector('#actionDialog').open&&document.querySelectorAll('#actionContent .row').length>=40"))
  check(True,'Video Translate options are available inside Reading and translation')
  s.evaluate(settings,"(async()=>{const n=[...document.querySelectorAll('#actionContent button')].find(n=>n.getAttribute('aria-label')==='Горячая клавиша перевода');n.click();await Promise.resolve();n.dispatchEvent(new KeyboardEvent('keydown',{key:'Control',code:'ControlLeft',ctrlKey:true,bubbles:true}));n.dispatchEvent(new KeyboardEvent('keydown',{key:'k',code:'KeyK',ctrlKey:true,bubbles:true}))})()")
  wait(lambda:s.evaluate(settings,"new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'browser.video.settings'}),onSuccess:s=>resolve(JSON.parse(s).translationHotkey==='ControlLeft+K'),onFailure:(_,s)=>reject(Error(s))}))"))
  check(True,'Video hotkey capture preserves physical modifier codes required by VOT')
  s.evaluate(settings,"document.querySelector('#closeAction').click();souluSettings.openSection('about')")
  wait(lambda:s.evaluate(settings,"[...document.querySelectorAll('.component-card')].every(n=>n.textContent.includes('Установлена: v'))"))
  check(s.evaluate(settings,"document.querySelectorAll('.component-card').length===2"),'About shows installed Xray and Sudoku')
  s.evaluate(settings,"souluSettings.openSection('interface');document.querySelector('input[name=settings-theme][value=dark]').click()")
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
