"""Native bridge, real WASM inference, isolated DOM and cached offline regression."""
import http.server, importlib.util, json, pathlib, sys, threading, time
spec=importlib.util.spec_from_file_location('storage',pathlib.Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'<!doctype html><meta charset=utf-8><html lang="ru"><body><h1 id="text">Hello world. This is a local translation test about the browser and its privacy.</h1><input id="input" value="Keep this value"><pre id="code">Keep this code</pre><div translate="no">Keep this block</div></body></html>'
        self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Fixture)
threading.Thread(target=server.serve_forever,daemon=True).start()
process=s.launch(sys.argv[1])
def wait(fn,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.15)
    raise AssertionError('Translation state timed out')
try:
    page=s.page_socket();shell_target=next(t for t in s.targets() if '/ui/index.html' in t.get('url',''))
    shell=s.websocket.create_connection(shell_target['webSocketDebuggerUrl'],timeout=180,origin=s.BASE)
    wait(lambda:s.evaluate(shell,'typeof SouluTranslate!=="undefined"'))
    s.navigate(page,f'http://127.0.0.1:{server.server_port}/article');time.sleep(.5)
    original=s.evaluate(page,'document.getElementById("text").textContent')
    assert s.evaluate(page,'typeof __souluTranslate')=='undefined','Isolated world leaked into page'
    s.evaluate(shell,'(async()=>{window.translationSnapshot=await browserShell.getCurrentSite()})()')
    probe=s.evaluate(shell,"browserShell.translation('probe',translationSnapshot)")
    assert s.evaluate(shell,'SouluTranslate.detect('+json.dumps(probe['sample'])+',"ru")')=='en'
    s.evaluate(shell,'(async()=>{window.translationEngine=new SouluTranslate.LocalTranslator();window.translationToken=(await browserShell.translation("begin",translationSnapshot)).token})()')
    def batch():
        return s.evaluate(shell,"""(async()=>{const snapshot={...translationSnapshot,token:translationToken};const batch=await browserShell.translation('collect',snapshot);const rows=await Promise.all(batch.nodes.map(async row=>({id:row.id,text:await translationEngine.translate('en','ru',row.text)})));await browserShell.translation('apply',{...snapshot,rows});return rows;})()""")
    rows=batch();assert rows and any('\u0400'<=c<='\u04ff' for c in rows[0]['text']),rows
    assert s.evaluate(page,'document.getElementById("input").value')=='Keep this value'
    assert s.evaluate(page,'document.getElementById("code").textContent')=='Keep this code'
    s.evaluate(page,"const p=document.createElement('p');p.id='dynamic';p.textContent='This paragraph was added dynamically after translation.';document.body.append(p)")
    time.sleep(.1);assert batch(),'Dynamic content was not collected'
    s.evaluate(shell,'browserShell.translation("restore",{...translationSnapshot,token:translationToken})')
    assert s.evaluate(page,'document.getElementById("text").textContent')==original
    s.evaluate(shell,'translationEngine.delete();window.translationEngine=new SouluTranslate.LocalTranslator()')
    s.command(shell,'Network.enable');s.command(shell,'Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':0,'uploadThroughput':0})
    result=s.evaluate(shell,'translationEngine.translate("en","ru","This translation is performed locally using cached language models.")')
    assert any('\u0400'<=c<='\u04ff' for c in result),result
    s.evaluate(shell,'(async()=>{window.translationToken=(await browserShell.translation("begin",translationSnapshot)).token})()');assert batch(),'Repeated translation did not recollect original nodes'
    s.evaluate(shell,'browserShell.translation("restore",{...translationSnapshot,token:translationToken})')
    assert s.evaluate(page,'document.getElementById("text").textContent')==original
    s.command(shell,'Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
    s.navigate(page,f'http://127.0.0.1:{server.server_port}/next');time.sleep(.3)
    assert s.evaluate(shell,'browserShell.translation("apply",{...translationSnapshot,token:translationToken,rows:[]}).then(()=>false,()=>true)'),'Stale result accepted'
    s.evaluate(shell,'translationEngine.delete()')
    print(json.dumps({'native_bridge':'passed','real_wasm_translation':'passed','wrong_html_language':'passed','forms_code':'passed','dynamic_content':'passed','restore_repeat':'passed','cached_offline_worker':'passed','stale_navigation':'passed'}),flush=True)
    page.close();shell.close();s.close_normally(process)
finally:
    if process.poll() is None:process.kill()
    server.shutdown()
