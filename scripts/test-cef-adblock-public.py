"""Real Soulu OFF/ON network and visual evidence, never synthetic site hits."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
events=[]
def command(ws,method,params=None):
    s.sequence+=1;ident=s.sequence
    ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
    while True:
        row=json.loads(ws.recv())
        if row.get('method','').startswith('Network.'):
            p=row.get('params',{})
            if row['method']=='Network.requestWillBeSent':
                events.append({'event':'request','id':p['requestId'],'url':p['request']['url'],'type':p.get('type')})
            elif row['method']=='Network.loadingFailed':events.append({'event':'failed','id':p['requestId'],'error':p.get('errorText')})
        if row.get('id')==ident:
            if 'error' in row:raise AssertionError(row['error'])
            return row.get('result',{})
s.command=command
def wait(fn,timeout=40):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        result=fn()
        if result:return result
        time.sleep(.2)
    raise AssertionError('Public browser state timeout')
urls=['https://e1.ru','https://lenta.ru','https://ria.ru','https://www.theguardian.com/international',
      'https://github.com','https://www.google.com','https://www.youtube.com',
      'https://www.facebook.com','https://www.ozon.ru','https://sanderstripa.com','https://apps.sanderstripa.com']
if '--e1-only' in sys.argv:urls=urls[:1]
legacy='--legacy' in sys.argv
out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
result=[]
with tempfile.TemporaryDirectory(prefix='soulu-public-adblock-',ignore_cleanup_errors=True) as root:
    env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),
        SOULU_REGRESSION_SKIP_FIRST_RUN='1',SOULU_ADBLOCK_NO_UPDATE='1')
    env.pop('SOULU_ADBLOCK_TEST_RULES',None)
    os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
    process=subprocess.Popen([sys.argv[1],'--no-proxy-server'],env=env)
    try:
        target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None))
        shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=45,origin=s.BASE)
        wait(lambda:s.evaluate(shell,"typeof window.browserShell==='object'"));page=s.page_socket()
        s.command(page,'Network.enable');s.command(page,'Network.setCacheDisabled',{'cacheDisabled':True})
        for url in urls:
            entry={'url':url,'runs':{}}
            for enabled in (False,True):
                label='on' if enabled else 'off';events.clear()
                s.evaluate(shell,'window.browserShell.setContentBlocking('+json.dumps({'domain':'','value':int(enabled)})+')')
                start=time.monotonic();s.command(page,'Page.navigate',{'url':url})
                # Let asynchronous auctions and lazy initial containers settle.
                deadline=time.monotonic()+18
                while time.monotonic()<deadline:
                    s.evaluate(page,'document.readyState');time.sleep(.5)
                snapshot=s.evaluate(shell,'window.browserShell.getCurrentSite()')
                dom=s.evaluate(page,"""(()=>{const s=window.__souluCosmetic;return {
                    title:document.title,url:location.href,textLength:document.body?.innerText.length||0,
                    links:document.querySelectorAll('a[href]').length,images:document.images.length,
                    cosmeticSelectors:s?.selectors.size||0,
                    hiddenContainers:s?[...s.selectors].reduce((n,q)=>{try{return n+[...document.querySelectorAll(q)].filter(e=>getComputedStyle(e).display==='none').length}catch(e){return n}},0):0,
                    ready:document.readyState};})()""")
                screenshot=s.command(page,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
                filename=urlsplit(url).hostname+'-'+label+'.png';(out/filename).write_bytes(base64.b64decode(screenshot['data']))
                entry['runs'][label]={'runtime':snapshot.get('adblock'), 'dom':dom,
                    'elapsedSeconds':round(time.monotonic()-start,2),'requestCount':sum(e['event']=='request' for e in events),
                    'networkEvents':list(events),'screenshot':filename}
                print(json.dumps({'url':url,'state':label,'blocked':snapshot.get('adblock',{}).get('blockedRequests'),'cosmetic':dom['cosmeticSelectors'],'title':dom['title']},ensure_ascii=False),flush=True)
            result.append(entry);(out/'adblock-public.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        if not legacy:
            assert result[0]['runs']['on']['runtime']['blockedRequests']>0,'E1 produced no real blocked requests'
            assert result[0]['runs']['on']['dom']['textLength']>1000,'E1 main content unavailable'
            assert result[0]['runs']['on']['dom']['cosmeticSelectors']>0,'E1 cosmetic rules not applied'
        page.close();shell.close();s.close_normally(process)
    finally:
        if process.poll() is None:process.kill();process.wait()
