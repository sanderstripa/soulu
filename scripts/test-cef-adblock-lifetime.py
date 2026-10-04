"""Multi-tab, repeated navigation/close, memory and engine-sharing smoke test."""
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
import psutil

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
ad_requests=0
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global ad_requests
        if self.path.startswith('/ad.js'):ad_requests+=1;body=b'window.adReached=true';kind='text/javascript'
        else:body=f'<title>Lifetime fixture</title><h1>Content</h1><script src="http://ad.doubleclick.net:{self.server.server_port}/ad.js"></script>'.encode();kind='text/html'
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.end_headers()
        try:self.wfile.write(body)
        except (ConnectionResetError,BrokenPipeError):pass
    def log_message(self,*args):pass
def wait(fn,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.1)
    raise AssertionError('Lifetime fixture timeout')
out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);evidence={}
with tempfile.TemporaryDirectory(prefix='soulu-adblock-lifetime-',ignore_cleanup_errors=True) as root:
    os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
    env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_ADBLOCK_NO_UPDATE='1',SOULU_REGRESSION_SKIP_FIRST_RUN='1')
    env.pop('SOULU_ADBLOCK_TEST_RULES',None)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    start=time.monotonic();process=subprocess.Popen([sys.argv[1],'--no-proxy-server','--host-resolver-rules=MAP ad.doubleclick.net 127.0.0.1'],env=env)
    def private_memory():
        total=0
        for p in [psutil.Process(process.pid),*psutil.Process(process.pid).children(recursive=True)]:
            try:total+=getattr(p.memory_info(),'private',p.memory_info().rss)
            except psutil.NoSuchProcess:pass
        return total
    try:
        target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None))
        shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
        wait(lambda:s.evaluate(shell,"typeof window.browserShell==='object'"));page=s.page_socket()
        evidence['startupSeconds']=round(time.monotonic()-start,3)
        def invoke(method,payload=None):return s.evaluate(shell,'window.browserShell.'+method+'('+('' if payload is None else json.dumps(payload))+')')
        invoke('setContentBlocking',{'domain':'','value':1});origin=f'http://127.0.0.1:{server.server_port}'
        s.navigate(page,origin+'/initial');base=invoke('getState')['activeTabId'];time.sleep(1)
        baseline=private_memory();counts=[];tabs=[]
        for i in range(8):
            s.evaluate(shell,'window.browserShell.openTab('+json.dumps(origin+f'/tab-{i}')+',false)')
            state=invoke('getState');tabs.append(state['activeTabId'])
            wait(lambda:invoke('getCurrentSite').get('adblock',{}).get('blockedRequests',0)>0)
            counts.append(invoke('getCurrentSite')['adblock'])
        peak=private_memory()
        assert all(c['networkRules']==counts[0]['networkRules'] for c in counts)
        for ident in tabs:invoke('closeTab',ident)
        invoke('switchTab',base);time.sleep(2);after_tabs=private_memory();durations=[];samples=[]
        for i in range(30):
            t=time.monotonic();s.navigate(page,origin+f'/rapid-{i}');durations.append(time.monotonic()-t)
            assert not s.evaluate(page,'window.adReached===true')
            if i%5==4:samples.append(private_memory())
        time.sleep(2);final=private_memory()
        assert ad_requests==0,'A background/new tab bypassed actual network blocking'
        assert final-after_tabs<160*1024*1024,'Repeated load memory growth needs investigation'
        evidence.update({'multiTab':True,'tabCount':8,'tabRuntimeCounters':counts,'serverAdRequests':ad_requests,
            'navigationCount':30,'meanNavigationSeconds':sum(durations)/len(durations),
            'memoryBytes':{'baseline':baseline,'eightTabs':peak,'afterClose':after_tabs,'samples':samples,'final':final},'passed':True})
        page.close();shell.close();s.close_normally(process)
    finally:
        if process.poll() is None:process.kill();process.wait()
        server.shutdown();out.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'evidence':str(out)}))
