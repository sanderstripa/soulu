"""Real MV3 action -> popup -> service worker -> active Chrome-style Soulu tab.
Uses the native folder chooser and synthetic credentials, never a user vault.
"""
import base64,ctypes,http.server,importlib.util,json,os,subprocess,sys,tempfile,threading,time
from pathlib import Path
from PIL import Image,ImageGrab
from pywinauto.controls.win32_controls import EditWrapper,ButtonWrapper

def module(name,file):
 spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
s=module('storage','test-cef-storage.py');p=module('platform','test-cef-platform.py')
s.DEBUG_PORT=s.free_port();s.BASE=f'http://127.0.0.1:{s.DEBUG_PORT}'
os.environ['NO_PROXY']='localhost,127.0.0.1,::1';os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
def wait(fn,timeout=40):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.15)
 raise AssertionError('Extension action timed out')
class Page(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  body=b'<!doctype html><title>Soulu extension integration</title><form id="login"><input id="username" name="username" autocomplete="username"><input id="password" name="password" type="password" autocomplete="current-password"><button type="submit">Sign in</button></form><script>login.addEventListener("submit",e=>e.preventDefault())</script>'
  self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*_):pass

def main():
 exe=str(Path(sys.argv[1]).resolve());output=Path(sys.argv[2]).resolve();output.parent.mkdir(parents=True,exist_ok=True)
 report={'passed':False,'checks':[]};connections=[];process=None
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Page);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/login'
 def check(ok,label):
  assert ok,label
  report['checks'].append(label);print('PASS:',label,flush=True)
 def socket(fragment):
  def find():
   for t in s.targets():
    if fragment in t.get('url','') and '/shortcuts' not in t.get('url',''):
     ws=s.websocket.create_connection(t['webSocketDebuggerUrl'],timeout=40,origin=s.BASE);connections.append(ws);return ws
  return wait(find)
 def call(shell,method,value=None):return s.evaluate(shell,'browserShell.'+method+'('+('' if value is None else json.dumps(value))+')')
 def extension(shell,op,profile,**payload):return s.evaluate(shell,'browserShell.extensions('+json.dumps(op)+','+json.dumps({'profile':profile,**payload})+')')
 def stop():
  nonlocal process
  for ws in connections:
   try:ws.close()
   except Exception:pass
  connections.clear()
  if process:
   s.close_normally(process);check(process.returncode==0,'Normal exit with MV3 worker and popup lifecycle');process=None
 try:
  with tempfile.TemporaryDirectory(prefix='soulu-extension-actions-',ignore_cleanup_errors=True) as temporary:
   root=Path(temporary);fixture=root/'extension';fixture.mkdir()
   manifest={'manifest_version':3,'name':'Soulu functional extension','version':'1.0','permissions':['storage','scripting','activeTab','tabs'],'host_permissions':['http://127.0.0.1/*'],'background':{'service_worker':'worker.js'},'action':{'default_popup':'popup.html','default_icon':{'48':'icon.png'}},'icons':{'48':'icon.png'},'content_scripts':[{'matches':['http://127.0.0.1/*'],'js':['content.js']}]}
   (fixture/'manifest.json').write_text(json.dumps(manifest));Image.new('RGB',(48,48),(25,110,240)).save(fixture/'icon.png')
   (fixture/'worker.js').write_text('''chrome.runtime.onInstalled.addListener(()=>chrome.storage.local.set({workerStarted:true}));
chrome.runtime.onMessage.addListener((m,sender,reply)=>{(async()=>{
 if(m.op==='save'){await chrome.storage.local.set({credentials:m.credentials});return {saved:true}}
 const tabs=await chrome.tabs.query({active:true,currentWindow:true});const tab=tabs[0];if(!tab)throw Error('No active Chrome tab');
 if(m.op==='fill'){await chrome.scripting.executeScript({target:{tabId:tab.id},func:()=>{document.querySelector('#username').value='fixture-user';document.querySelector('#password').value='fixture-password';document.querySelector('#username').dispatchEvent(new Event('input',{bubbles:true}));}});return {filled:tab.id,url:tab.url}}
 return {tab,storage:await chrome.storage.local.get(null)};
})().then(reply,e=>reply({error:String(e)}));return true});''')
   (fixture/'content.js').write_text('''document.documentElement.dataset.extensionReady='yes';document.querySelector('form')?.addEventListener('submit',async()=>{const result=await chrome.runtime.sendMessage({op:'save',credentials:{username:document.querySelector('#username').value,password:document.querySelector('#password').value}});document.documentElement.dataset.extensionSaved=String(result.saved)});''')
   (fixture/'popup.html').write_text('<!doctype html><html><head><meta charset="utf-8"><style>body{width:330px;min-height:180px;margin:12px;font:14px sans-serif}pre{white-space:pre-wrap}</style></head><body><h1>Functional popup</h1><button id="fill">Fill login</button><pre id="state"></pre><pre id="result"></pre><script src="popup.js"></script></body></html>')
   (fixture/'popup.js').write_text("chrome.runtime.sendMessage({op:'get'}).then(r=>document.querySelector('#state').textContent=JSON.stringify(r));document.querySelector('#fill').onclick=()=>chrome.runtime.sendMessage({op:'fill'}).then(r=>document.querySelector('#result').textContent=JSON.stringify(r));")
   env=dict(os.environ,LOCALAPPDATA=str(root/'local'),APPDATA=str(root/'roaming'),SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1')
   def start():
    nonlocal process
    process=subprocess.Popen([exe,'--no-proxy-server','--enable-logging','--log-file='+str(output.parent/'cef.log')],env=env);shell=socket('/ui/index.html');wait(lambda:s.evaluate(shell,"typeof window.browserShell?.extensions==='function'"));return shell
   shell=start();call(shell,'openSettingsWindow');settings=socket('/ui/settings.html');wait(lambda:s.evaluate(settings,"document.body?.classList.contains('ready')"));s.evaluate(settings,"souluSettings.openSection('extensions')");manager=socket('chrome://extensions/')
   wait(lambda:s.evaluate(manager,"typeof window.chrome?.developerPrivate?.loadUnpacked==='function'"))
   s.evaluate(manager,'chrome.developerPrivate.updateProfileConfiguration({inDeveloperMode:true})')
   s.sequence+=1;manager.send(json.dumps({'id':s.sequence,'method':'Runtime.evaluate','params':{'expression':"chrome.developerPrivate.loadUnpacked({failQuietly:true,populateError:true});true"}}))
   controls=wait(lambda:p.dialog_controls(process.pid));edits=[c for c in controls if c[1]=='Edit'];edit=next((e for e in edits if e[3]==1152),edits[-1]);button=next(c for c in controls if c[1]=='Button' and c[3]==1)
   EditWrapper(edit[0]).set_edit_text(str(fixture));ButtonWrapper(button[0]).click_input()
   def row():return s.evaluate(manager,"chrome.developerPrivate.getExtensionsInfo({includeDisabled:true,includeTerminated:true}).then(rows=>rows.find(e=>e.name==='Soulu functional extension')||null)")
   installed=wait(row);print('Native extension info:',json.dumps(installed),flush=True);ident=installed['id'];report['extensionId']=ident;check(True,'Install real MV3 fixture with action, worker and content script')
   profile=call(shell,'getState')['activeProfileId']
   # Pin using the real settings control, not a synthetic backend-only flag.
   wait(lambda:s.evaluate(settings,"!!document.querySelector('#extensionPins input[data-extension-id="+json.dumps(ident)+"]')"))
   s.evaluate(settings,"(()=>{const t=document.querySelector('#extensionPins input[data-extension-id="+json.dumps(ident)+"]');t.checked=true;t.dispatchEvent(new Event('change',{bubbles:true}));return true})()")
   wait(lambda:any(e['id']==ident and e['pinned'] for e in extension(shell,'list',profile)['items']))
   check(True,'Profile-local pin saved through Settings control')
   s.evaluate(settings,'souluSettingsRequestClose()');wait(lambda:not any('/ui/settings.html' in t.get('url','') for t in s.targets()))
   call(shell,'openTab',url);content=socket(url);wait(lambda:s.evaluate(content,"document.documentElement.dataset.extensionReady==='yes'"))
   wait(lambda:s.evaluate(shell,"!!document.querySelector('[data-extension-toolbar] [data-extension-id="+json.dumps(ident)+"]')"))
   check(s.evaluate(shell,"[...document.querySelectorAll('[data-extension-toolbar]')].every(h=>h.previousElementSibling.classList.contains('vpn-button'))"),'Extension icons are immediately after VPN')
   check(s.evaluate(shell,"!!document.querySelector('[data-extension-id="+json.dumps(ident)+"] img[src^=\"data:image/\"]')"),'Real extension icon is supplied from its profile')
   before=len(call(shell,'getState')['tabs'])
   s.evaluate(shell,"[...document.querySelectorAll('[data-extension-id="+json.dumps(ident)+"]')].find(b=>b.getClientRects().length).click()")
   popup=socket('chrome-extension://'+ident+'/popup.html')
   state=wait(lambda:s.evaluate(popup,"document.querySelector('#state')?.textContent"));state=json.loads(state)
   check(not state.get('error') and state['tab']['url']==url,'Popup messages reach the worker and resolve the active Soulu page')
   check(len(call(shell,'getState')['tabs'])==before,'Action opens its native popup without creating a Soulu tab')
   ImageGrab.grab().save(output.parent/'extension-popup.png')
   s.evaluate(popup,"document.querySelector('#fill').click()")
   wait(lambda:s.evaluate(content,"username.value==='fixture-user'&&password.value==='fixture-password'"));check(True,'Worker uses chrome.scripting to autofill the active login form')
   # A real submit also offers Soulu's own password save. Decline that
   # separate vault prompt so it cannot block the extension worker test.
   s.sequence+=1;content.send(json.dumps({'id':s.sequence,'method':'Runtime.evaluate','params':{'expression':"username.value='saved-user';password.value='saved-password';login.requestSubmit();true"}}))
   decline=wait(lambda:next((c for c in p.dialog_controls(process.pid) if c[1]=='Button' and c[3]==7),None))
   ButtonWrapper(decline[0]).click_input()
   wait(lambda:s.evaluate(content,"document.documentElement.dataset.extensionSaved==='true'"));check(True,'Content script saves synthetic credentials through the worker')
   stop();shell=start();profile=call(shell,'getState')['activeProfileId'];rows=extension(shell,'list',profile)['items'];check(any(e['id']==ident and e['pinned'] for e in rows),'Installed extension and pin survive restart')
   call(shell,'openTab',url);content=socket(url);wait(lambda:s.evaluate(content,"document.documentElement.dataset.extensionReady==='yes'"));wait(lambda:s.evaluate(shell,"!!document.querySelector('[data-extension-id="+json.dumps(ident)+"]')"))
   s.evaluate(shell,"[...document.querySelectorAll('[data-extension-id="+json.dumps(ident)+"]')].find(b=>b.getClientRects().length).click()")
   popup=socket('chrome-extension://'+ident+'/popup.html');state=json.loads(wait(lambda:s.evaluate(popup,"document.querySelector('#state')?.textContent")))
   check(state['storage']['credentials']=={'username':'saved-user','password':'saved-password'},'Saved synthetic credentials survive worker and browser restart')
   call(shell,'createProfile','Extension isolation');other=call(shell,'getState')['activeProfileId'];check(not any(e['id']==ident for e in extension(shell,'list',other)['items']),'Second profile has an isolated extension registry')
   call(shell,'switchProfile',profile);call(shell,'openSettingsWindow');settings=socket('/ui/settings.html');wait(lambda:s.evaluate(settings,"document.body?.classList.contains('ready')"));s.evaluate(settings,"souluSettings.openSection('extensions')")
   wait(lambda:s.evaluate(settings,"!!document.querySelector('#extensionPins input[data-extension-id="+json.dumps(ident)+"]')"));s.evaluate(settings,"(()=>{const t=document.querySelector('#extensionPins input[data-extension-id="+json.dumps(ident)+"]');t.checked=false;t.dispatchEvent(new Event('change',{bubbles:true}));return true})()")
   wait(lambda:not any(e['id']==ident and e['pinned'] for e in extension(shell,'list',profile)['items']));s.evaluate(settings,'souluSettingsRequestClose()');wait(lambda:s.evaluate(shell,"!document.querySelector('[data-extension-toolbar] [data-extension-id="+json.dumps(ident)+"]')"));check(True,'Unpin removes the icon without uninstalling the extension')
   stop();report['passed']=True
 finally:
  if process and not report['passed']:
   try:
    ImageGrab.grab().save(output.parent/'failure.png')
    report['browserState']=call(shell,'getState')
    report['toolbarErrors']=s.evaluate(shell,"[...document.querySelectorAll('[data-extension-toolbar] button')].map(b=>({id:b.dataset.extensionId,title:b.title,disabled:b.disabled}))")
    report['targets']=[{'type':t.get('type'),'url':t.get('url')} for t in s.targets()]
    print('FAILURE TARGETS',json.dumps(report['targets']),flush=True)
   except Exception:pass
  if process:
   try:stop()
   except Exception:process.kill();process.wait()
  server.shutdown();output.write_text(json.dumps(report,indent=2),encoding='utf-8')
if __name__=='__main__':main()
