"""Native bridge, real WASM inference, isolated DOM and cached offline regression."""
import http.server, importlib.util, json, pathlib, sys, threading, time, os, subprocess, tempfile
spec=importlib.util.spec_from_file_location('storage',pathlib.Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'<!doctype html><meta charset=utf-8><html lang="ru"><body><h1 id="text">Hello world. This is a local translation test about the browser and its privacy.</h1><p id="paragraph">The browser translates this complete paragraph locally while preserving the document structure.</p><input id="input" value="Keep this value"><pre id="code">Keep this code</pre><div translate="no">Keep this block</div></body></html>'
        self.send_response(200);self.send_header('Content-Type','text/html;charset=utf-8');self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Fixture)
threading.Thread(target=server.serve_forever,daemon=True).start()
os.environ['NO_PROXY']='127.0.0.1,localhost'
os.environ['SOULU_ADBLOCK_NO_UPDATE']='1'
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
profile=tempfile.TemporaryDirectory(prefix='soulu-translation-',ignore_cleanup_errors=True)
os.environ['LOCALAPPDATA']=profile.name
out=pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else pathlib.Path('artifacts/translation-evidence')
out.mkdir(parents=True,exist_ok=True)
os.environ['SOULU_UI_TEST_PORT']=str(s.DEBUG_PORT)
process=subprocess.Popen([str(pathlib.Path(sys.argv[1]).resolve()),'--log-net-log='+str((out/'network.json').resolve())])
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
    wait(lambda:s.evaluate(shell,"Boolean(document.querySelector('.soulu-translate-button'))"))
    s.evaluate(shell,"document.querySelector('.soulu-translate-button').click()")
    wait(lambda:s.evaluate(shell,"!document.querySelector('.soulu-translation').hidden"))
    s.evaluate(shell,"[...document.querySelectorAll('.soulu-translation button')].find(b=>b.textContent==='Перевести').click()")
    wait(lambda:s.evaluate(page,'document.getElementById("text").textContent')!=original,150)
    wait(lambda:any('\u0400'<=c<='\u04ff' for c in s.evaluate(page,'document.getElementById("paragraph").textContent')),30)
    s.evaluate(shell,"[...document.querySelectorAll('.soulu-translation button')].find(b=>b.textContent==='Показать оригинал').click()")
    wait(lambda:s.evaluate(page,'document.getElementById("text").textContent')==original)
    s.evaluate(shell,"[...document.querySelectorAll('.soulu-translation button')].find(b=>b.textContent==='Закрыть').click()")

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
    s.evaluate(shell,'window.modelTransport=browserShell.translation;browserShell.translation=(action,payload)=>action==="model"?Promise.reject(Error("Offline model transport")):modelTransport(action,payload)')
    result=s.evaluate(shell,'translationEngine.translate("en","ru","This translation is performed locally using cached language models.")')
    assert any('\u0400'<=c<='\u04ff' for c in result),result
    s.evaluate(shell,'(async()=>{window.translationToken=(await browserShell.translation("begin",translationSnapshot)).token})()');assert batch(),'Repeated translation did not recollect original nodes'
    s.evaluate(shell,'browserShell.translation("restore",{...translationSnapshot,token:translationToken})')
    assert s.evaluate(page,'document.getElementById("text").textContent')==original
    s.evaluate(shell,'browserShell.translation=modelTransport')
    s.command(shell,'Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
    german=s.evaluate(shell,'translationEngine.translate("de","ru","Das ist eine deutsche Seite über den lokalen Übersetzer und den Browser.")')
    assert any('\u0400'<=c<='\u04ff' for c in german),german
    english=s.evaluate(shell,'translationEngine.translate("ru","en","Это русская страница о локальном переводе и настройках браузера.")')
    assert any('a'<=c.lower()<='z' for c in english),english
    assert s.evaluate(shell,'SouluTranslate.detect("Это русская страница о локальном переводе и настройках браузера.","en")')=='ru'
    assert s.evaluate(shell,'translationEngine.translate("ru","ru","Русская страница")')=='Русская страница'
    assert s.evaluate(shell,'translationEngine.translate("zh","ru","unsupported").then(()=>false,()=>true)')
    s.command(shell,'Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
    s.evaluate(page,"for(let i=0;i<200;i++){const p=document.createElement('p');p.className='long-fixture';p.textContent='This is a paragraph on a long page. The browser translates all paragraphs locally.';document.body.append(p)}")
    s.evaluate(shell,'(async()=>{window.translationToken=(await browserShell.translation("begin",translationSnapshot)).token;window.shellHeartbeat=0;window.heartbeatTimer=setInterval(()=>shellHeartbeat++,25)})()')
    translated=0
    for _ in range(20):
        rows=batch();translated+=len(rows)
        if translated>=203:break
    assert translated>=203,translated
    assert s.evaluate(page,"[...document.querySelectorAll('.long-fixture')].every(p=>/[\u0400-\u04ff]/.test(p.textContent))")
    assert s.evaluate(shell,'shellHeartbeat')>0,'The UI heartbeat stopped during long-page translation'
    s.evaluate(shell,'clearInterval(heartbeatTimer)')
    s.evaluate(page,"history.pushState({},'', '/spa')")
    wait(lambda:s.evaluate(page,'document.getElementById("text").textContent')==original)
    assert s.evaluate(shell,'browserShell.translation("apply",{...translationSnapshot,token:translationToken,rows:[]}).then(()=>false,()=>true)'),'SPA accepted a stale result'
    s.navigate(page,f'http://127.0.0.1:{server.server_port}/next');time.sleep(.3)
    assert s.evaluate(shell,'browserShell.translation("apply",{...translationSnapshot,token:translationToken,rows:[]}).then(()=>false,()=>true)'),'Stale result accepted'
    s.evaluate(shell,'translationEngine.delete()')
    cache_root=pathlib.Path(profile.name)/'Soulu/User Data/Translation/Models/v1'
    assert cache_root.is_dir() and list(cache_root.glob('*.model')),'Models were not cached outside profile storage'
    manifest=json.loads((pathlib.Path(__file__).resolve().parents[1]/'ui/translation-models.json').read_text(encoding='utf-8'))
    damaged=next(pair for pair in manifest['pairs'] if pair['from']=='ru' and pair['to']=='en')['files']['lexicalShortlist']['sha256']
    (cache_root/(damaged+'.model')).write_bytes(b'corrupt model fixture')
    assert s.evaluate(shell,'browserShell.translationCache("read",'+json.dumps(damaged)+').then(b=>b.byteLength===0)'),'Corrupted model cache was accepted'
    assert not (cache_root/(damaged+'.model')).exists(),'Corrupted model cache was retained'
    (cache_root/'stale-regression.model').write_bytes(b'old model fixture')
    s.evaluate(shell,'(async()=>{const snapshot=await browserShell.getCurrentSite();await browserShell.translation("preferences",{...snapshot,target:"ru",always:true,source:"en",never:true})})()')
    page.close();shell.close();s.close_normally(process)
    # A normal process restart must retain verified model buffers and preferences.
    network=json.loads((out/'network.json').read_text(encoding='utf-8'))
    model_requests=[event['params'] for event in network['events'] if 'method' in event.get('params',{}) and 'storage.googleapis.com/moz-fx-translations-data' in event.get('params',{}).get('url','')]
    assert model_requests and all(request['method']=='GET' for request in model_requests),model_requests
    assert not any('translate.google' in json.dumps(event) or 'deepl.com' in json.dumps(event) for event in network['events'])
    process=s.launch(sys.argv[1]);page=s.page_socket();target=next(t for t in s.targets() if '/ui/index.html' in t.get('url',''));shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=180,origin=s.BASE)
    wait(lambda:s.evaluate(shell,'typeof SouluTranslate!=="undefined"'))
    s.navigate(page,f'http://127.0.0.1:{server.server_port}/restart');time.sleep(.3)
    s.evaluate(shell,'(async()=>{window.restartSnapshot=await browserShell.getCurrentSite()})()')
    preferences=s.evaluate(shell,'browserShell.translation("preferences",restartSnapshot)')
    assert 'en' in preferences['always'] and f'http://127.0.0.1:{server.server_port}' in preferences['never'],preferences
    s.command(shell,'Network.enable');s.command(shell,'Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':0,'uploadThroughput':0})
    result=s.evaluate(shell,'window.modelTransport=browserShell.translation;browserShell.translation=(a,p)=>a==="model"?Promise.reject(Error("Offline model transport")):modelTransport(a,p);window.translationEngine=new SouluTranslate.LocalTranslator();translationEngine.translate("en","ru","The local translator works offline after a complete browser restart.")')
    assert any('\u0400'<=c<='\u04ff' for c in result),result
    assert not (cache_root/'stale-regression.model').exists(),'Stale model cache was retained'
    s.evaluate(shell,'browserShell.translation=modelTransport;translationEngine.delete()')
    s.command(shell,'Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
    base_profile=s.evaluate(shell,'browserShell.getState()')['activeProfileId']
    created=s.evaluate(shell,'browserShell.createProfile("Translation regression profile")')['activeProfileId']
    s.evaluate(shell,'browserShell.navigate('+json.dumps(f'http://127.0.0.1:{server.server_port}/second-profile')+')')
    wait(lambda:s.evaluate(shell,"browserShell.getCurrentSite().then(s=>s.url.endsWith('/second-profile')&&!s.mainLoading)"))
    other=s.evaluate(shell,'(async()=>{const snapshot=await browserShell.getCurrentSite();return browserShell.translation("preferences",snapshot)})()')
    assert not other['always'] and not other['never'],other
    s.evaluate(shell,'browserShell.switchProfile('+json.dumps(base_profile)+')')
    for first in [True,False]:
        s.evaluate(shell,'browserShell.newIncognito()')
        s.evaluate(shell,'browserShell.navigate('+json.dumps(f'http://127.0.0.1:{server.server_port}/private')+')')
        wait(lambda:s.evaluate(shell,"browserShell.getCurrentSite().then(s=>s.url.endsWith('/private')&&!s.mainLoading)"))
        s.evaluate(shell,'(async()=>{window.privateSnapshot=await browserShell.getCurrentSite()})()')
        private=s.evaluate(shell,'browserShell.translation("preferences",privateSnapshot)')
        assert not private['always'] and not private['never'],private
        if first:s.evaluate(shell,'browserShell.translation("preferences",{...privateSnapshot,target:"en",always:true,source:"de",never:true})')
        s.evaluate(shell,'browserShell.closeTab(privateSnapshot.tabId)')
    report={'native_bridge':'passed','toolbar_full_page':'passed','real_wasm_translation':'passed','german_pivot':'passed','russian_same_language':'passed','unsupported_language':'passed','wrong_html_language':'passed','forms_code':'passed','dynamic_content':'passed','long_page':'passed','restore_repeat':'passed','cached_offline_worker':'passed','cached_offline_restart':'passed','preferences_restart':'passed','stale_navigation':'passed','spa_restore':'passed','model_http_requests':len(model_requests),'model_http_methods':'GET only'}
    report.update(profile_preferences='isolated',incognito_preferences='discarded',russian_to_english='passed',stale_model_cleanup='passed',damaged_model_cleanup='passed',model_storage='shared native cache outside profiles')
    (out/'translation-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
    page.close();shell.close();s.close_normally(process)
finally:
    if process.poll() is None:process.kill()
    server.shutdown()
    assert pathlib.Path(profile.name).resolve().is_relative_to(pathlib.Path(tempfile.gettempdir()).resolve())
    profile.cleanup()
