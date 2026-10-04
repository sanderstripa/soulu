"""CEF acceptance: server-observed cancellation, cosmetics, persistence/isolation.

Test-only ABP rules are loaded through an explicitly gated native test process.
Real subscriptions are also active: ad.doubleclick.net is checked independently.
"""
import base64
import http.server
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import urlsplit

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
requests=[]
lock=threading.Lock()

def wait(fn,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=fn()
        if value:return value
        time.sleep(.1)
    raise AssertionError('AdBlock state timeout')

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        with lock:requests.append({'host':self.headers.get('Host',''),'path':self.path})
        path=urlsplit(self.path).path;port=self.server.server_port
        if path=='/redirect':
            self.send_response(302);self.send_header('Location',f'http://ads.fixture.test:{port}/redirect-ad.js');self.end_headers();return
        if path.endswith('.js'):
            body=b'window.fixtureLoads=(window.fixtureLoads||0)+1;';kind='text/javascript'
        elif path.endswith('.gif'):
            body=base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7');kind='image/gif'
        elif path=='/inner':
            body=b'<div class="soulu-ad-slot">Inner advertisement</div><p id="article">Inner content</p>';kind='text/html'
        else:
            body=f'''<!doctype html><meta charset="utf-8"><title>AdBlock controlled</title>
              <div class="soulu-ad-slot">Advertisement</div><div class="soulu-except">Excepted</div>
              <p id="article">Legitimate content</p><script src="/normal.js"></script>
              <script src="http://ads.fixture.test:{port}/advert.js"></script>
              <script src="http://ads.fixture.test:{port}/allow.js"></script>
              <script src="http://ad.doubleclick.net:{port}/baseline.js"></script>
              <img id="ad-image" src="http://ads.fixture.test:{port}/advert.gif">
              <img id="normal-image" src="/normal.gif">
              <iframe id="ad-frame" src="http://ads.fixture.test:{port}/advert-frame"></iframe>
              <iframe id="normal-frame" src="/inner"></iframe>
              <script src="/redirect"></script>'''.encode();kind='text/html'
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
        self.send_header('Access-Control-Allow-Origin','*')
        if path.startswith('/csp'):
            self.send_header('Content-Security-Policy',"style-src 'none'; script-src 'self' 'unsafe-inline' http:; img-src http:; frame-src http:")
        self.send_header('Content-Length',str(len(body)));self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,*args):pass

evidence={}
exe=str(Path(sys.argv[1]).resolve())
out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='soulu-adblock-',ignore_cleanup_errors=True) as root:
    rules=Path(root)/'fixture.txt'
    rules.write_text('''||ads.fixture.test^$script,image,subdocument,xmlhttprequest
@@||ads.fixture.test/allow.js$script
##.soulu-ad-slot
##.soulu-except
site-a.test#@#.soulu-except
''',encoding='utf-8')
    env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),
        SOULU_ADBLOCK_TEST_RULES=str(rules),SOULU_ADBLOCK_NO_UPDATE='1',SOULU_REGRESSION_SKIP_FIRST_RUN='1')
    os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
    server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    a=f'http://site-a.test:{server.server_port}';b=f'http://site-b.test:{server.server_port}'
    process=None;sockets=[]
    def start():
        global process,shell,page,sockets
        process=subprocess.Popen([exe,'--no-proxy-server',
          '--host-resolver-rules=MAP site-a.test 127.0.0.1, MAP site-b.test 127.0.0.1, MAP ads.fixture.test 127.0.0.1, MAP ad.doubleclick.net 127.0.0.1'],env=env)
        shell_target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None))
        shell=s.websocket.create_connection(shell_target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
        wait(lambda:s.evaluate(shell,"typeof window.browserShell==='object'"));page=s.page_socket();sockets=[shell,page]
    def stop():
        for ws in sockets:
            try:ws.close()
            except Exception:pass
        s.close_normally(process)
    def invoke(method,payload=None):
        return s.evaluate(shell,'window.browserShell.'+method+'('+('' if payload is None else json.dumps(payload))+')')
    def blocking(domain,value):return invoke('setContentBlocking',{'domain':domain,'value':value})
    def visit(ws,url):
        with lock:requests.clear()
        s.command(ws,'Network.enable');s.command(ws,'Network.setCacheDisabled',{'cacheDisabled':True})
        s.navigate(ws,url);time.sleep(.5)
    def visible(ws,selector):return s.evaluate(ws,"getComputedStyle(document.querySelector("+json.dumps(selector)+")).display!=='none'")
    def fetch_ad(ws):return s.evaluate(ws,f"fetch('http://ads.fixture.test:{server.server_port}/fetch-ad.js').then(()=>true,()=>false)")
    def actual_snapshot():return invoke('getCurrentSite')['adblock']
    def active_page(url):
        invoke('navigate',url)
        target=wait(lambda:next((t for t in s.targets() if t.get('url')==url),None))
        ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
        sockets.append(ws);return ws
    try:
        start();blocking('',0);visit(page,a+'/off')
        assert s.evaluate(page,'window.fixtureLoads===5'),'OFF baseline did not load all scripts'
        assert visible(page,'.soulu-ad-slot') and fetch_ad(page)
        with lock:off=list(requests)
        blocking('',1);visit(page,a+'/on')
        assert s.evaluate(page,'window.fixtureLoads===2'),'normal/exception scripts or cancellation incorrect'
        assert s.evaluate(page,"document.querySelector('#normal-image').naturalWidth===1&&document.querySelector('#ad-image').naturalWidth===0")
        assert not fetch_ad(page),'XHR/fetch bypassed request filtering'
        wait(lambda:not visible(page,'.soulu-ad-slot'));assert visible(page,'.soulu-except')
        with lock:on=list(requests)
        blocked_paths={'/advert.js','/advert.gif','/advert-frame','/baseline.js','/redirect-ad.js','/fetch-ad.js'}
        assert not any(urlsplit(r['path']).path in blocked_paths for r in on),'Blocked bytes reached the fixture server'
        snapshot=actual_snapshot();assert snapshot['ready'] and snapshot['blockedRequests']>=6 and snapshot['checkedRequests']>=6
        assert any('ad.doubleclick.net' in h['url'] for h in snapshot['hits']),'Official EasyList baseline did not hit'
        evidence['controlled']={'offServerRequests':off,'onServerRequests':on,'runtime':snapshot,
            'script':True,'image':True,'iframe':True,'xhr_fetch':True,'redirect':True,'exception':True,'cosmetic':True}
        s.evaluate(page,"history.pushState({},'', '/spa');const n=document.createElement('div');n.className='soulu-ad-slot';n.id='dynamic-ad';document.body.append(n)")
        wait(lambda:not visible(page,'#dynamic-ad'));evidence['spa_dynamic_cosmetic']=True
        visit(page,a+'/csp');wait(lambda:not visible(page,'.soulu-ad-slot'));evidence['strict_csp_cosmetic']=True
        # A runtime change must remove active cosmetic CSS without restarting.
        blocking('',0);wait(lambda:visible(page,'.soulu-ad-slot'));assert fetch_ad(page)
        blocking('',1);blocking('site-a.test',0);visit(page,a+'/allow');assert fetch_ad(page)
        visit(page,b+'/block');assert not fetch_ad(page)
        evidence['global_without_restart']=True;evidence['per_site']=True
        # Native contexts must keep independent settings; private changes stay in memory.
        state=invoke('createProfile','AdBlock second');profile=state['activeProfileId'];page=active_page(b+'/profile-b-initial')
        visit(page,b+'/profile-b');assert fetch_ad(page),'Profile B inherited Profile A settings'
        invoke('switchProfile','personal');page=active_page(b+'/profile-a-initial');visit(page,b+'/profile-a');assert not fetch_ad(page)
        invoke('newIncognito');private=active_page(b+'/private-initial');visit(private,b+'/private');assert not fetch_ad(private)
        blocking('site-b.test',0);visit(private,b+'/private-allow');assert fetch_ad(private)
        permanent=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal'/'soulu-site-rules.json'
        assert 'site-b.test' not in json.loads(permanent.read_text(encoding='utf-8'))['blocking']['sites']
        evidence['profile_isolation']=True;evidence['incognito_no_permanent_leak']=True
        stop();start();invoke('switchProfile','personal');page=active_page(b+'/restored-initial')
        visit(page,a+'/restart-a');assert fetch_ad(page)
        visit(page,b+'/restart-b');assert not fetch_ad(page)
        evidence['restart']=True
        # Simulate a corrupt persisted update; no network update can rescue this run.
        stop();cache=Path(root)/'Soulu'/'User Data'/'AdBlock'/'filters-v1.json';cache.parent.mkdir(parents=True,exist_ok=True)
        cache.write_text('<html>broken cache</html>',encoding='utf-8');start();invoke('switchProfile','personal');page=active_page(b+'/restored-initial')
        visit(page,b+'/corrupt-offline');status=actual_snapshot()
        assert status['ready'] and status['source']=='bundled' and status['lastUpdateError']
        assert not fetch_ad(page);evidence['corrupt_cache_offline_fallback']=status
        stop();process=None
        evidence['passed']=True
    finally:
        if process and process.poll() is None:process.kill();process.wait()
        server.shutdown();out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'evidence':str(out)}))
