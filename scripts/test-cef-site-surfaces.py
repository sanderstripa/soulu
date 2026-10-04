"""Controlled real CEF permission callbacks, persistent policy and visual surfaces."""
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
import base64

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'

def wait(fn,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.1)
    raise AssertionError('Site surface state timeout')

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        paragraphs=''.join('<p>'+('A careful report about browsers and reading preferences. '*14)+'</p>' for _ in range(8))
        body=('<!doctype html><meta charset="utf-8"><title>Permission and reading fixture</title><article><h1>Browser reading report</h1>'+paragraphs+'</article>').encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass

def main():
    out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
    visuals=out.parent/'site-surfaces-visuals';visuals.mkdir(exist_ok=True)
    report={'passed':False,'checks':[],'geometry':[],'dpiMethod':'CEF deviceScaleFactor emulation; physical monitor DPI still needs human review'}
    def check(value,name):
        assert value,name
        report['checks'].append(name);print('PASS:',name,flush=True)
    with tempfile.TemporaryDirectory(prefix='soulu-site-surfaces-',ignore_cleanup_errors=True) as root:
        os.environ['LOCALAPPDATA']=root
        env=dict(os.environ,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT))
        server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        origin=f'http://127.0.0.1:{server.server_port}'
        process=shell=page=None
        def start():
            p=subprocess.Popen([sys.argv[1],'--no-proxy-server','--use-fake-device-for-media-stream'],env=env)
            target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None))
            ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
            wait(lambda:s.evaluate(ws,"typeof browserShell.respondPermission==='function'&&!!document.querySelector('.site-popover')"))
            return p,ws,s.page_socket()
        def E(script):return s.evaluate(shell,script)
        def current():return E('browserShell.getCurrentSite()')
        def action(name,values=None):
            site=current();args={k:site[k] for k in ('tabId','url','generation')};args.update(values or {})
            return E('browserShell.siteAction('+json.dumps(name)+','+json.dumps(args)+')')
        def trigger(script):
            return s.command(page,'Runtime.evaluate',{'expression':script,'userGesture':True,'returnByValue':True})
        def prompt():return E('browserShell.getState().then(s=>s.permissionPrompt||null)')
        def reply(decision):
            item=wait(prompt);return E('browserShell.respondPermission('+json.dumps({'id':item['id'],'decision':decision})+')')
        def bounds(selector):
            return E('(()=>{const n=document.querySelector('+json.dumps(selector)+');const r=n.getBoundingClientRect();return {hidden:n.hidden,x:r.x,y:r.y,w:r.width,h:r.height,viewport:innerHeight,scroll:n.scrollHeight>n.clientHeight+1,font:getComputedStyle(n).fontFamily}})()')
        def capture(name):
            data=s.command(shell,'Page.captureScreenshot',{'format':'png'})['data']
            (visuals/(name+'.png')).write_bytes(base64.b64decode(data))
        try:
            process,shell,page=start();s.navigate(page,origin+'/article')
            wait(lambda:not current()['mainLoading'])
            # SetContentSetting must affect the actual Notifications API.
            for value,expected in [(2,'denied'),(0,'granted'),(-1,'default')]:
                action('permission',{'permission':'notifications','value':value})
                wait(lambda:s.evaluate(page,'Notification.permission')==expected)
                check(True,'Notification API site value '+str(value))
            trigger("window.notificationResult=null;Notification.requestPermission().then(v=>window.notificationResult=v)")
            item=wait(prompt);check(item['origin']==origin and item['permissions']==['notifications'],'real notification callback names exact origin')
            wait(lambda:not bounds('.soulu-permission-prompt')['hidden'])
            r=bounds('.soulu-permission-prompt');check(r['x']==12 and r['y']>=48 and r['y']<150 and r['h']<280 and 'Onest' in r['font'],'compact upper left Onest prompt')
            capture('notification-prompt');reply('block')
            wait(lambda:s.evaluate(page,'window.notificationResult')=='denied')
            check(current()['rules']['sites']['127.0.0.1']['notifications']==2,'prompt Block persists canonical override')
            action('permission',{'permission':'notifications','value':-1})
            trigger("window.notificationResult=null;Notification.requestPermission().then(v=>window.notificationResult=v)")
            wait(prompt);reply('allow');wait(lambda:s.evaluate(page,'window.notificationResult')=='granted')
            check(s.evaluate(page,"(()=>{try{const n=new Notification('Soulu controlled test',{silent:true});n.close();return true}catch{return false}})()"),'allowed Notification constructor accepted')
            # Camera/microphone use fake devices, never fake permission UI.
            trigger("window.mediaResult=null;navigator.mediaDevices.getUserMedia({video:true,audio:true}).then(v=>{v.getTracks().forEach(t=>t.stop());window.mediaResult='allowed'},()=>window.mediaResult='blocked')")
            item=wait(prompt);check(set(item['permissions'])=={'camera','microphone'},'combined media callback')
            reply('block');wait(lambda:s.evaluate(page,'window.mediaResult')=='blocked')
            check(current()['rules']['sites']['127.0.0.1']['camera']==2 and current()['rules']['sites']['127.0.0.1']['microphone']==2,'combined media decision saved')
            # Dismissal and navigation must not persist a grant or orphan the card.
            action('permission',{'permission':'camera','value':-1});action('permission',{'permission':'microphone','value':-1})
            trigger("navigator.mediaDevices.getUserMedia({video:true}).then(v=>v.getTracks().forEach(t=>t.stop()),()=>{})")
            item=wait(prompt);reply('dismiss');wait(lambda:not prompt())
            check('camera' not in current()['rules']['sites']['127.0.0.1'],'dismiss leaves Ask unchanged')
            trigger("navigator.mediaDevices.getUserMedia({video:true}).then(v=>v.getTracks().forEach(t=>t.stop()),()=>{})")
            item=wait(prompt);s.navigate(page,origin+'/other');wait(lambda:not prompt())
            stale=E('browserShell.respondPermission('+json.dumps({'id':item['id'],'decision':'allow'})+').then(()=>false,()=>true)')
            check(stale,'navigation rejects stale consent')
            action('permission',{'permission':'notifications','value':0})
            # Exercise actual UI in both layouts and every browser theme.
            for layout in ('compact','classic'):
                for theme in ('light','dark','system'):
                    E('browserShell.setSettings('+json.dumps({'layout':layout,'theme':theme})+')')
                    wait(lambda:E('document.body.dataset.layout')==layout and E('document.body.dataset.theme')==theme)
                    E('browserShell.pageMenu()');wait(lambda:not bounds('.site-popover')['hidden'])
                    wait(lambda:current()['readerAvailable'])
                    r=bounds('.site-popover');check(not r['scroll'] and r['h']<440 and r['y']+r['h']<=r['viewport'] and 'Onest' in r['font'],layout+'/'+theme+' compact main bounds')
                    check(E("!document.querySelector('.site-popover details,.site-popover select')"),'main has no permissions form '+layout+'/'+theme)
                    report['geometry'].append({'layout':layout,'theme':theme,'main':r});capture(layout+'-'+theme+'-main')
                    E("document.querySelector('[aria-label=\"Настройки сайта…\"]').click()")
                    check(E("document.querySelectorAll('[data-permission]').length===7"),'seven compact supported permissions '+layout+'/'+theme)
                    r=bounds('.site-popover');check(not r['scroll'] and r['y']+r['h']<=r['viewport'],'nested settings bounds '+layout+'/'+theme);capture(layout+'-'+theme+'-settings')
                    E("document.querySelector('[data-permission=notifications]').click()")
                    E("document.querySelector('.site-choice[data-value=\"2\"]').click()")
                    wait(lambda:E("document.querySelector('.site-popover').dataset.level==='settings'"))
                    check(s.evaluate(page,'Notification.permission')=='denied','picker changes Notifications API '+layout+'/'+theme)
                    E("document.querySelector('.site-back').click()")
                    E("document.querySelector('[data-reader-action]').click()")
                    wait(lambda:current()['readerActive']);E("document.querySelector('.reader-toolbar button:last-child').click()")
                    check(E("document.querySelectorAll('.reader-swatch').length===4&&document.querySelectorAll('.reader-settings select').length===1&&document.querySelectorAll('.reader-settings [role=switch]').length===1"),'visual palette controls '+layout+'/'+theme)
                    for article_theme in ('light','sepia','gray','dark'):
                        E("document.querySelector('.reader-swatch[data-theme="+article_theme+"]').click()")
                        wait(lambda:current()['preferences']['theme']==article_theme)
                        check('Onest' in bounds('.reader-settings')['font'],'palette remains Onest '+article_theme)
                    capture(layout+'-'+theme+'-reader');action('reader.exit')
            # Reset must delete both dictionaries, preserve storage and survive restart.
            s.evaluate(page,"localStorage.setItem('reset-survives','yes')")
            action('permission',{'permission':'geolocation','value':2});action('blocking',{'value':1})
            wait(lambda:not current()['mainLoading']);action('reset');wait(lambda:not current()['mainLoading'])
            rules=current()['rules'];check('127.0.0.1' not in rules['sites'] and '127.0.0.1' not in rules['blocking']['sites'],'reset removes permissions and adblock')
            check(s.evaluate(page,"localStorage.getItem('reset-survives')==='yes'"),'reset retains storage')
            action('permission',{'permission':'notifications','value':0})
            shell.close();page.close();s.close_normally(process);process=None
            process,shell,page=start();s.navigate(page,origin+'/article');wait(lambda:not current()['mainLoading'])
            check(s.evaluate(page,'Notification.permission')=='granted','notification allow survives restart')
            check('geolocation' not in current()['rules']['sites']['127.0.0.1'] and '127.0.0.1' not in current()['rules']['blocking']['sites'],'reset survives restart')
            for scale in (1,1.25,1.5,2):
                s.command(shell,'Emulation.setDeviceMetricsOverride',{'width':1200,'height':900,'deviceScaleFactor':scale,'mobile':False})
                E('browserShell.pageMenu()');wait(lambda:not bounds('.site-popover')['hidden'])
                r=bounds('.site-popover');check(r['y']+r['h']<=r['viewport'],'DPI emulation bounded '+str(scale));capture('scale-'+str(scale))
                E("document.querySelector('.site-shield').dispatchEvent(new PointerEvent('pointerdown'))")
            s.command(shell,'Emulation.clearDeviceMetricsOverride')
            report['passed']=True
        finally:
            for ws in (shell,page):
                if ws:
                    try:ws.close()
                    except Exception:pass
            if process and process.poll() is None:
                try:s.close_normally(process)
                except Exception:process.kill()
            server.shutdown();out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
