"""Real Gecko/Windows acceptance. Every action uses the production frontend/backend."""
import argparse,base64,http.server,json,os,pathlib,socket,subprocess,tempfile,threading,time
from marionette_driver.marionette import Marionette
p=argparse.ArgumentParser();p.add_argument('binary');p.add_argument('out');p.add_argument('--ui-only',action='store_true');args=p.parse_args()
binary=pathlib.Path(args.binary).resolve();out=pathlib.Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
root=pathlib.Path(tempfile.mkdtemp(prefix='soulu-gecko2-'));profile=root/'Profiles/default';profile.mkdir(parents=True)
report={'passed':False,'complete':not args.ui_only,'checks':{},'limitations':[]}
if os.name!='nt':report['limitations'].append('Linux UI-only harness disables the content sandbox because the container cannot create user namespaces; no shipped preference disables it.')
class Site(http.server.BaseHTTPRequestHandler):
 ads=0
 def do_GET(self):
  if self.path.startswith('/pagead/'):
   Site.ads+=1;body=b'window.advertisementLoaded=true';kind='application/javascript'
  else:
   body=('''<!doctype html><meta charset=utf-8><title>Soulu fixture</title><style>html{color-scheme:light dark}body{margin:0;height:2400px}#box{height:100px;background:#4182e8}video{width:400px;height:225px}</style><div id=box>Gecko fixture</div><ins class=adsbygoogle data-ad-client=ca-test id=ad>Ad placeholder</ins><input id=input><video id=v muted autoplay></video><canvas id=c width=200 height=100 hidden></canvas><script src="http://pagead2.googlesyndication.com:%d/pagead/js/adsbygoogle.js"></script><script>const canvas=document.getElementById('c'),video=document.getElementById('v');let n=0;setInterval(()=>{const x=canvas.getContext('2d');x.fillStyle=++n%%2?'blue':'green';x.fillRect(0,0,200,100)},50);video.srcObject=canvas.captureStream(20);video.play().catch(()=>{});document.documentElement.dataset.identity=String(Math.random())</script>'''%self.server.server_port).encode();kind='text/html'
  self.send_response(200);self.send_header('Content-Type',kind);self.end_headers();self.wfile.write(body)
 def log_message(self,*_):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Site);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
log=open(out/'runtime.log','w',encoding='utf-8');proc=m=None

def check(name,value,detail=None):
 report['checks'][name]={'passed':bool(value),'detail':detail};print(name,bool(value),detail or '',flush=True)
 if not value:raise AssertionError(name+': '+str(detail))
def wait(fn,timeout=30):
 end=time.monotonic()+timeout;last=None
 while time.monotonic()<end:
  try:
   value=fn()
   if value:return value
  except Exception as e:last=e
  time.sleep(.15)
 raise AssertionError('Timeout: '+str(last))
def chrome(code):m.set_context('chrome');return m.execute_script(code)
def run(code):
 m.set_context('chrome');value=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{'+code+'})().then(done,e=>done({TEST_ERROR:String(e),stack:e.stack}));')
 if isinstance(value,dict) and 'TEST_ERROR' in value:raise AssertionError(value)
 return value
def ui(code,target='shell'):
 browser="gBrowser.selectedBrowser" if target=='page' else f'document.getElementById("soulu-{target}-frame")'
 return run('return await '+browser+'.browsingContext.currentWindowGlobal.getActor("SouluApp").sendQuery("testing",'+json.dumps(code)+');')
def call(action,payload=None):return run('return await Soulu.dispatch('+json.dumps(action)+','+json.dumps(payload)+');')
def content(code):m.set_context('content');return m.execute_script(code)
def select_latest():m.switch_to_window(m.window_handles[-1]);m.set_context('chrome')
def start(launcher=False):
 global proc,m
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 active=root/'launcher/SouluGecko/Profiles/launch-test' if launcher else profile;active.mkdir(parents=True,exist_ok=True)
 (active/'user.js').write_text('user_pref("marionette.port",'+str(port)+');\nuser_pref("network.dns.localDomains","pagead2.googlesyndication.com");\n',encoding='utf-8')
 env=dict(os.environ,MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1',SOULU_GECKO_TEST='1')
 headless=[]
 if os.name!='nt':headless=['-headless'];env['MOZ_DISABLE_CONTENT_SANDBOX']='1'
 if launcher:env['LOCALAPPDATA']=str(root/'launcher');command=[str(binary.parent.parent/'Soulu Gecko Preview 2.exe'),'--profile','launch-test',*headless,'-marionette']
 else:command=[str(binary),*headless,'-no-remote','-profile',str(active),'-marionette']
 proc=subprocess.Popen(command,stdout=log,stderr=log,env=env)
 def listening():
  try:
   with socket.create_connection(('127.0.0.1',port),timeout=.2):return True
  except OSError:
   if proc.poll() is not None:raise AssertionError('Browser exited')
 wait(listening,60);m=Marionette('127.0.0.1',port=port,socket_timeout=40);m.start_session();m.set_context('chrome');m.timeout.script=180
 wait(lambda:chrome('return !!window.Soulu?.ready'),30)
 wait(lambda:ui('return !!window.browserShell && document.body.dataset.layout==="adaptive" && document.querySelectorAll("#tabStrip .classic-tab").length===1'),30)
def stop():
 global proc,m
 if m:
  try:m.quit()
  except:pass
  m=None
 if proc:
  try:proc.wait(timeout=20)
  except:proc.kill();proc.wait()
  proc=None
try:
 start()
 check('original_soulu_toolbar_dom',ui('return !!document.getElementById("classicAddress") && !!document.getElementById("windowClose") && !!document.getElementById("vpnButton") && document.body.dataset.layout==="adaptive"'))
 check('home_frontend_and_bridge',wait(lambda:ui('return !!window.souluHomeApply && document.getElementById("providerIcon").naturalWidth>0 && document.getElementById("query").placeholder.length>0','page')))
 check('hardware_acceleration_and_security_preferences',chrome('return Services.prefs.getBoolPref("fission.autostart") && Services.prefs.getIntPref("security.sandbox.content.level")>0 && !Services.prefs.getBoolPref("layers.acceleration.disabled",false) && !Services.prefs.getBoolPref("gfx.webrender.force-disabled",false) && Services.prefs.getBoolPref("browser.safebrowsing.malware.enabled")'))
 first=call('browser.state.get')['activeTabId'];ui('document.getElementById("newTabButton").click();return true;');wait(lambda:len(call('browser.state.get')['tabs'])==2);time.sleep(.4)
 check('frontend_new_tab_and_adaptive_geometry',abs(chrome('return gBrowser.selectedBrowser.getBoundingClientRect().top')-88)<2)
 second=call('browser.state.get')['activeTabId'];ui('document.querySelector('+json.dumps('[data-close-tab="'+str(second)+'"]')+').click();return true;');wait(lambda:len(call('browser.state.get')['tabs'])==1);time.sleep(.4)
 check('frontend_close_tab_and_collapse',abs(chrome('return gBrowser.selectedBrowser.getBoundingClientRect().top')-68)<2)
 select_latest();ui('const i=document.getElementById("classicAddress");i.value='+json.dumps(url)+';document.getElementById("classicAddressForm").requestSubmit();return true;');m.set_context('content');wait(lambda:content('return !!document.getElementById("v") && document.getElementById("v").currentTime>.1'),30)
 check('address_form_performs_navigation',content('return location.href.startsWith("http://127.0.0.1:")'))
 check('website_has_no_application_bridge',content('return !window.cefQuery&&!window.browserShell&&!window.Soulu'))
 check('isolated_web_process',str(chrome('return gBrowser.selectedBrowser.remoteType')).startswith('webIsolated'))
 if not args.ui_only:
  status=chrome('return Soulu.adblock?.status(gBrowser.selectedBrowser.browsingContext.id)');check('own_rust_adblock_ready',status and status.get('ready') and status.get('networkRules',0)>10000,status)
  time.sleep(1);check('actual_ad_request_cancelled',Site.ads==0,{'adServerRequests':Site.ads})
  check('cosmetic_filter_hides_real_ad',wait(lambda:content('return getComputedStyle(document.getElementById("ad")).display==="none"'),15))
 # Verify no browsing rectangle or document identity changes during real toolbar activity.
 m.set_context('content');before=content('return {h:innerHeight,w:innerWidth,y:scrollY,top:document.getElementById("v").getBoundingClientRect().top,identity:document.documentElement.dataset.identity,time:document.getElementById("v").currentTime}')
 samples=[]
 for x in [60,140,260,410,600,800,1040,250]:
  if os.name=='nt':
   import ctypes
   left,top=chrome('return [window.mozInnerScreenX,window.mozInnerScreenY]');ctypes.windll.user32.SetCursorPos(round(left+x),round(top+24))
  else:ui('document.getElementById("vpnButton").dispatchEvent(new MouseEvent("mouseover",{bubbles:true}));return true;')
  time.sleep(.08);samples.append(content('return {h:innerHeight,w:innerWidth,y:scrollY,top:document.getElementById("v").getBoundingClientRect().top,identity:document.documentElement.dataset.identity,time:document.getElementById("v").currentTime}'))
 check('no_page_jitter_during_toolbar_hover',bool(before['identity']) and all(all(abs(s[k]-before[k])<1 for k in ['h','w','y','top']) and s['identity']==before['identity'] for s in samples),samples)
 check('playing_video_continues_during_hover',samples[-1]['time']>before['time'])
 check('bookmark_frontend_writes_places',ui('await browserShell.addBookmark();const rows=await browserShell.getBookmarks();return rows.some(r=>r.url==='+json.dumps(url)+');'))
 history=call('history.query',{'search':'127.0.0.1','offset':0});check('history_records_real_navigation',len(history['rows'])>0,{'visits':len(history['rows'])})
 ui('await browserShell.openHistory();return true;');select_latest();check('original_history_ui_reads_places',wait(lambda:ui('return document.querySelectorAll(".visit").length>0','page')))
 call('browser.closeTab',call('browser.state.get')['activeTabId']);m.switch_to_window(m.window_handles[0]);m.set_context('chrome')
 ui('await browserShell.openSettingsWindow();return true;');wait(lambda:call('browser.state.get')['settingsOverlayReady']);
 settings=ui('return {count:document.querySelectorAll("#homeCards button").length,text:document.body.innerText};','settings')
 check('all_original_settings_sections',settings['count']==12,{'count':settings['count']})
 change=ui('souluSettings.openSection("interface");const input=document.querySelector("input[name=settings-theme][value=dark]");input.click();await souluSettings.flush();return souluSettings.persisted.settings.theme;','settings');check('actual_settings_control_persists_theme',change=='dark')
 encrypted=run('const c=await Soulu.dispatch("settings.begin");c.vpn.profiles=[{id:"fixture",name:"Local fixture",link:"vless://12345678-1234-1234-1234-123456789abc@127.0.0.1:9?security=none&type=tcp",protocol:"vless",address:"127.0.0.1:9"}];c.vpn.defaultProfileId="fixture";const r=await Soulu.dispatch("settings.save",c);const text=await IOUtils.readUTF8(PathUtils.join(PathUtils.profileDir,"soulu-settings.json"));return {ok:r.ok,encrypted:!text.includes("vless://")&&text.includes("protected")};')
 check('vpn_keys_encrypted_by_nss',encrypted.get('ok') and encrypted.get('encrypted'))
 if os.name=='nt':
  check('vpn_frontend_starts_real_core',ui('await vpn.send("connect");return (await vpn.send("status")).connected;'))
  check('vpn_fail_closed_dns_and_webrtc',chrome('return Services.prefs.getIntPref("network.proxy.type")===1 && Services.prefs.getBoolPref("network.proxy.socks_remote_dns") && !Services.prefs.getBoolPref("network.proxy.failover_direct")&&!Services.prefs.getBoolPref("media.peerconnection.enabled")'))
  check('vpn_frontend_disconnects',ui('await vpn.send("disconnect");return !(await vpn.send("status")).connected;'))
 created=ui('return await browserShell.createProfile("Gecko 2 acceptance");');check('profile_created_from_frontend',created.get('id') in [x['id'] for x in call('browser.state.get')['profiles']])
 private=run('OpenBrowserWindow({private:true});for(let i=0;i<100;i++){const w=[...Services.wm.getEnumerator("navigator:browser")].find(w=>w!==window&&w.Soulu?.ready);if(w){const {PrivateBrowsingUtils}=ChromeUtils.importESModule("resource://gre/modules/PrivateBrowsingUtils.sys.mjs");const ok=PrivateBrowsingUtils.isWindowPrivate(w);w.close();return ok;}await new Promise(r=>setTimeout(r,100));}return false;');check('private_window_uses_native_private_context',private)
 chrome('Soulu.closeSettings()');
 if os.name=='nt' and not args.ui_only:
  call('browser.navigate','https://www.youtube.com/watch?v=aqz-KE-bpKQ');select_latest();m.set_context('content')
  def youtube_playing():
   return m.execute_async_script('const done=arguments[0],v=document.querySelector("video");if(!v){done(false);return;}v.muted=true;v.play().catch(()=>{});setTimeout(()=>done(v.readyState>=2&&v.currentTime>.1),1000)')
  check('youtube_public_video_playback',wait(youtube_playing,120))
  a=content('return {time:document.querySelector("video").currentTime,h:innerHeight,w:innerWidth}');time.sleep(2);b=content('return {time:document.querySelector("video").currentTime,h:innerHeight,w:innerWidth}');check('youtube_advances_with_stable_viewport',b['time']>a['time'] and a['h']==b['h'] and a['w']==b['w'],{'before':a,'after':b})
 stop();start();check('settings_and_encrypted_vpn_survive_restart',chrome('return Soulu.config.settings.theme==="dark" && Soulu.config.vpn.profiles[0].link.startsWith("vless://")'))
 if os.name=='nt':stop();start(True);check('portable_launcher_uses_isolated_data',chrome('return Soulu.config.profile==="launch-test"&&PathUtils.profileDir.includes("SouluGecko")'))
 report['passed']=True
finally:
 stop();server.shutdown();log.close();(out/'acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
