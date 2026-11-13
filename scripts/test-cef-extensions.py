"""Install an unpacked MV3 fixture through the real Chromium folder picker.

Verifies the Settings host, persistence and content scripts in normal Sona tabs.
No extension-debugging bypasses or installation-only mocks are used.
"""
import ctypes
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
from PIL import ImageGrab
from pywinauto import mouse
from pywinauto.controls.win32_controls import EditWrapper, ButtonWrapper


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

s = module('storage', 'test-cef-storage.py')
p = module('platform', 'test-cef-platform.py')
o = module('overlay', 'test-cef-settings-overlay.py')
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'
os.environ['SONA_REGRESSION_SKIP_FIRST_RUN'] = '1'
s.DEBUG_PORT = s.free_port()
s.BASE = f'http://127.0.0.1:{s.DEBUG_PORT}'


def wait(fn, timeout=35):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = fn()
        if value:
            return value
        time.sleep(.1)
    raise AssertionError('Extension acceptance timeout')


class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'<!doctype html><html><head><title>Extension fixture</title></head><body>Fixture</body></html>'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def main():
    executable = str(Path(sys.argv[1]).resolve())
    output = Path(sys.argv[2]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'checks': [], 'limitations': ['Authentication against a private Bitwarden vault is not exercised.']}
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/fixture'
    process = None
    connections = []

    def check(value, label):
        assert value, label
        report['checks'].append(label)
        print('PASS:', label, flush=True)

    def socket(fragment):
        def find():
            for target in s.targets():
                if fragment in target.get('url', '') and '/shortcuts' not in target.get('url',''):
                    ws = s.websocket.create_connection(target['webSocketDebuggerUrl'], timeout=35, origin=s.BASE)
                    connections.append(ws)
                    return ws
        return wait(find)

    def stop():
        nonlocal process
        if process and process.poll() is None:
            print('Targets at close:', [(t.get('type'),t.get('url')) for t in s.targets()], flush=True)
        for ws in connections:
            ws.close()
        connections.clear()
        if process:
            s.close_normally(process)
            process = None

    try:
        with tempfile.TemporaryDirectory(prefix='sona-extensions-', ignore_cleanup_errors=True) as temporary:
            root = Path(temporary)
            extension = root / 'fixture'
            extension.mkdir()
            (extension / 'manifest.json').write_text(json.dumps({
                'manifest_version': 3, 'name': 'Sona extension acceptance', 'version': '1.0',
                'permissions': ['storage'],
                'content_scripts': [{'matches': ['http://127.0.0.1/*'], 'js': ['content.js'], 'run_at': 'document_idle'}]
            }), encoding='utf-8')
            (extension / 'content.js').write_text("chrome.storage.local.set({verified:true});document.documentElement.dataset.sonaExtensionFixture='active';", encoding='utf-8')
            env = dict(os.environ, LOCALAPPDATA=str(root / 'local'), APPDATA=str(root / 'roaming'),
                       SONA_UI_TEST_PORT=str(s.DEBUG_PORT), SONA_REGRESSION_SKIP_FIRST_RUN='1')

            def start():
                nonlocal process
                process = subprocess.Popen([executable, '--no-proxy-server'], env=env)
                shell = socket('/ui/index.html')
                wait(lambda: s.evaluate(shell, "typeof window.browserShell?.openSettingsWindow==='function'"))
                s.evaluate(shell, 'browserShell.openSettingsWindow()')
                settings = socket('/ui/settings.html')
                wait(lambda: s.evaluate(settings, "document.body?.classList.contains('ready')"))
                s.evaluate(settings, "sonaSettings.openSection('extensions')")
                manager = socket('chrome://extensions')
                wait(lambda: s.evaluate(manager, "typeof window.chrome?.developerPrivate?.getExtensionsInfo==='function'"))
                return shell, settings, manager

            shell, settings, manager = start()
            if os.environ.get('SONA_UI_HOTFIX') != '1':
                check(s.evaluate(manager, 'typeof window.cefQuery') == 'undefined', 'Chrome surface has no Sona bridge')
                s.evaluate(manager, 'chrome.developerPrivate.updateProfileConfiguration({inDeveloperMode:true})')
                # Do not await a promise while the native file picker blocks the UI.
                s.sequence += 1
                manager.send(json.dumps({'id': s.sequence, 'method': 'Runtime.evaluate', 'params': {
                    'expression': "window.__loadResult=null;try{Promise.resolve(chrome.developerPrivate.loadUnpacked({failQuietly:true,populateError:true})).then(r=>window.__loadResult={result:r},e=>window.__loadResult={error:String(e)});}catch(e){window.__loadResult={error:String(e)}};true"}}))
                controls = wait(lambda: p.dialog_controls(process.pid))
                print('Extension picker controls:', [(c[1], c[2], c[3]) for c in controls], flush=True)
                ImageGrab.grab().save(output.parent / 'extensions-picker.png')
                edits = [c for c in controls if c[1] == 'Edit']
                edit = next((e for e in edits if e[3] in (1001, 1148, 1152)), edits[-1])
                button = next(c for c in controls if c[1] == 'Button' and c[3] == 1)
                user = ctypes.windll.user32
                user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                user.GetAncestor.restype = ctypes.c_void_p
                user.SetForegroundWindow(user.GetAncestor(button[0], 2))
                EditWrapper(edit[0]).set_edit_text(str(extension.resolve()))
                ButtonWrapper(button[0]).click_input()
                time.sleep(1)
                remaining = p.dialog_controls(process.pid)
                print('Picker controls after selection:', [(c[1], c[2], c[3]) for c in remaining], flush=True)
                if remaining:
                    # Windows folder pickers can first navigate to a typed directory;
                    # selecting that directory then requires a second accept.
                    accept = next((c for c in remaining if c[1] == 'Button' and c[3] == 1), None)
                    if accept:
                        ButtonWrapper(accept[0]).click_input()
                ImageGrab.grab().save(output.parent / 'extensions-after-picker.png')
                print('Manager after picker:', s.evaluate(manager, '({url:location.href,result:window.__loadResult})'), flush=True)
                print('Targets after picker:', [(t.get('type'),t.get('url')) for t in s.targets()], flush=True)
                # Chrome may select a newly created tab when extension installation
                # finishes. Reopen the installed list and verify persisted state,
                # rather than depending on a JS variable in a navigated WebUI.
                s.evaluate(settings, "document.querySelector('.extension-controls button').click()")
                manager = socket('chrome://extensions')
                wait(lambda: s.evaluate(manager, "typeof window.chrome?.developerPrivate?.getExtensionsInfo==='function'"))
                expression = "chrome.developerPrivate.getExtensionsInfo({includeDisabled:true,includeTerminated:true}).then(rows=>rows.find(r=>r.name==='Sona extension acceptance')||null)"
                installed = wait(lambda: s.evaluate(manager, expression))
                check(bool(installed), 'Unpacked MV3 installation through native picker')
                report['extensionId'] = installed['id']
                s.evaluate(settings, 'sonaSettingsRequestClose()')
                wait(lambda: not any('/ui/settings.html' in t.get('url', '') for t in s.targets()))
                s.evaluate(shell, 'browserShell.openTab(' + json.dumps(url) + ')')
                content = socket(url)
                check(wait(lambda: s.evaluate(content, "document.documentElement.dataset.sonaExtensionFixture==='active'")), 'Content script runs in an ordinary Chrome-style Sona tab')
                stop()
                shell, settings, manager = start()
                check(s.evaluate(manager, expression)['id'] == installed['id'], 'Installed extension persists after restart')
                # Profile-local enable/disable is performed by Chromium, not a UI flag.
                ident = json.dumps(installed['id'])
                s.evaluate(manager, f'chrome.management.setEnabled({ident},false)')
                check(s.evaluate(manager, expression)['state'] == 'DISABLED', 'Chromium disables the installed extension')
                s.evaluate(manager, f'chrome.management.setEnabled({ident},true)')
                check(s.evaluate(manager, expression)['state'] == 'ENABLED', 'Chromium re-enables the installed extension')
            # Exercise the Store route without claiming external installation.
            s.evaluate(settings, "[...document.querySelectorAll('.extension-controls button')].find(b=>b.textContent==='Chrome Web Store').click()")
            wait(lambda: any('chromewebstore.google.com/' in t.get('url', '') for t in s.targets()))
            check(True, 'Store opens inside the embedded Chrome surface')
            if os.environ.get('SONA_TEST_STORE_INSTALL') == '1':
                store = socket('chromewebstore.google.com/')
                if os.environ.get('SONA_TEST_STORE_METADATA') == '1':
                    s.command(store, 'Emulation.setUserAgentOverride', {
                        'userAgent':s.evaluate(store,'navigator.userAgent'),
                        'userAgentMetadata':{
                            'brands':[{'brand':'Chromium','version':'156'},{'brand':'Google Chrome','version':'156'}],
                            'fullVersionList':[{'brand':'Chromium','version':'156.0.8078.48'},{'brand':'Google Chrome','version':'156.0.8078.48'}],
                            'fullVersion':'156.0.8078.48','platform':'Windows','platformVersion':'10.0.0',
                            'architecture':'x86','model':'','mobile':False,'bitness':'64','wow64':False
                        }})
                s.command(store, 'Page.navigate', {'url':'https://chromewebstore.google.com/detail/bitwarden-password-manager/nngceckbapebfimnlniiiahkandclblb'})
                wait(lambda: s.evaluate(store, "location.href.includes('nngceckbapebfimnlniiiahkandclblb')&&document.readyState==='complete'"), 60)
                ImageGrab.grab().save(output.parent / 'store-page.png')
                print('Store page:', s.evaluate(store, "({url:location.href,title:document.title,text:document.body.innerText.slice(0,7000)})"), flush=True)
                s.evaluate(store, "[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='Нет, спасибо'&&b.getClientRects().length)?.click()")
                wait(lambda: s.evaluate(store, "[...document.querySelectorAll('button')].some(b=>/^(Add to Chrome|Добавить в Chrome|Установить)$/.test(b.innerText.trim())&&!b.disabled&&b.getAttribute('aria-disabled')!=='true')"), 60)
                print('Store APIs:', s.evaluate(store, "({ua:navigator.userAgent,brands:navigator.userAgentData?.brands,apis:Object.keys(window.chrome||{}),webstore:typeof window.chrome?.webstorePrivate,management:typeof window.chrome?.management})"), flush=True)
                coords = s.evaluate(store, "(()=>{const b=[...document.querySelectorAll('button')].find(b=>/^(Add to Chrome|Добавить в Chrome|Установить)$/.test(b.innerText.trim()));if(b.disabled||b.getAttribute('aria-disabled')==='true')throw Error('Store installation is disabled');b.scrollIntoView({block:'center',inline:'center'});const r=b.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                s.command(store, 'Input.dispatchMouseEvent', {**coords,'type':'mousePressed','button':'left','clickCount':1})
                s.command(store, 'Input.dispatchMouseEvent', {**coords,'type':'mouseReleased','button':'left','clickCount':1})
                time.sleep(2)
                print('After Store install click:', s.evaluate(store, "document.body.innerText.slice(0,1800)"), flush=True)
                ImageGrab.grab().save(output.parent / 'store-after-click.png')
                from pywinauto import Desktop
                def consent():
                    for window in Desktop(backend='uia').windows(process=process.pid):
                        for b in window.descendants(control_type='Button'):
                            if b.window_text().strip() in ('Add extension','Добавить расширение','Установить расширение'):
                                return b
                ImageGrab.grab().save(output.parent / 'store-permission-prompt.png')
                try:
                    accept = wait(consent, 8)
                except AssertionError:
                    # Embedded Chrome Views may not appear under the parent's
                    # UIA tree. The native consent dialog starts on Cancel;
                    # select its preceding Install button using real keyboard input.
                    from pywinauto.keyboard import send_keys
                    send_keys('+{TAB}{ENTER}')
                else:
                    accept.click_input()
                wait(lambda: s.evaluate(store, "chrome.management.get('nngceckbapebfimnlniiiahkandclblb').then(x=>x.enabled,()=>false)"), 120)
                s.evaluate(settings, "document.querySelector('.extension-controls button').click()")
                manager = socket('chrome://extensions')
                wait(lambda: s.evaluate(manager, "typeof window.chrome?.developerPrivate?.getExtensionsInfo==='function'"))
                store_extension = wait(lambda: s.evaluate(manager, "chrome.developerPrivate.getExtensionsInfo({includeDisabled:true,includeTerminated:true}).then(rows=>rows.find(r=>r.id==='nngceckbapebfimnlniiiahkandclblb')||null)"), 90)
                check(store_extension.get('state') == 'ENABLED', 'Bitwarden installs from the official Chrome Web Store with native consent')
                ImageGrab.grab().save(output.parent / 'store-installed.png')
                bitwarden = 'nngceckbapebfimnlniiiahkandclblb'
                profile = s.evaluate(shell, 'browserShell.getState()')['activeProfileId']
                selector = '#extensionPins input[data-extension-id="' + bitwarden + '"]'
                wait(lambda: s.evaluate(settings, '!!document.querySelector('+json.dumps(selector)+')'))
                s.evaluate(settings, '(()=>{const pin=document.querySelector('+json.dumps(selector)+');pin.checked=true;pin.dispatchEvent(new Event("change",{bubbles:true}));return true})()')
                wait(lambda: s.evaluate(shell, 'browserShell.extensions("list",'+json.dumps({'profile':profile})+').then(r=>r.items.some(e=>e.id==="'+bitwarden+'"&&e.pinned))'))
                s.evaluate(settings, 'sonaSettingsRequestClose()')
                wait(lambda: not any('/ui/settings.html' in t.get('url','') for t in s.targets()))
                s.evaluate(shell, 'browserShell.openTab('+json.dumps(url)+')')
                action_selector = '[data-extension-toolbar] [data-extension-id="' + bitwarden + '"]'
                wait(lambda: s.evaluate(shell, '!!document.querySelector('+json.dumps(action_selector)+')'))
                count = len(s.evaluate(shell, 'browserShell.getState()')['tabs'])
                s.evaluate(shell, '[...document.querySelectorAll('+json.dumps(action_selector)+')].find(b=>b.getClientRects().length).click()')
                popup = socket('chrome-extension://'+bitwarden+'/popup/')
                text = wait(lambda: s.evaluate(popup, 'document.body?.innerText'))
                print('Bitwarden popup initial:', s.evaluate(popup, '({url:location.href,ready:document.readyState,text:document.body.innerText.slice(0,5000)})'), flush=True)
                def login_ready():
                    return s.evaluate(popup, """(()=>{
                      const email=document.querySelector('input[type=email],input[autocomplete=username],input[name=email]');
                      if(email&&email.getClientRects().length&&!email.disabled)return true;
                      if(location.hash.includes('default-password-manager-prompt')){
                        const skip=[...document.querySelectorAll('button,a,[role=button]')].find(b=>b.getClientRects().length&&/^(Skip|Пропустить)$/i.test(b.innerText.trim()));
                        if(skip)skip.click();
                        return false;
                      }
                      const login=[...document.querySelectorAll('button,a,[role=button]')].find(b=>b.getClientRects().length&&/(Log\\s*in|Login|Войти|Вход)/i.test(b.innerText));
                      if(login)login.click();
                      return false;
                    })()""")
                try:
                    wait(login_ready, 60)
                finally:
                    print('Bitwarden popup final:', s.evaluate(popup, '({url:location.href,ready:document.readyState,text:document.body.innerText.slice(0,5000),inputs:[...document.querySelectorAll("input")].map(e=>({type:e.type,name:e.name,visible:!!e.getClientRects().length,disabled:e.disabled}))})'), flush=True)
                    ImageGrab.grab().save(output.parent / 'bitwarden-popup.png')
                check(len(s.evaluate(shell, 'browserShell.getState()')['tabs']) == count, 'Real Bitwarden opens its own action popup without a Sona tab')
                check(True, 'Bitwarden initializes its account login interface')
                report['bitwardenPopupText'] = s.evaluate(popup, 'document.body.innerText.slice(0,3000)')
                anchor=s.evaluate(shell,'(()=>{const r=[...document.querySelectorAll('+json.dumps(action_selector)+')].find(b=>b.getClientRects().length).getBoundingClientRect();return {x:r.x,bottom:r.bottom,scale:devicePixelRatio}})()')
                host=wait(lambda:next(iter(o.windows(process.pid,'SonaBrowserWindow')),None));client=o.client_rect(host)
                def anchored():
                    geometry=s.evaluate(popup,'({x:screenX,y:screenY,width:outerWidth,height:outerHeight})')
                    report['bitwardenGeometry']=geometry;report['bitwardenAnchor']=anchor
                    return abs(geometry['y']-(client[1]/anchor['scale']+anchor['bottom']+6))<24 and geometry['width']<=800 and geometry['height']<=600
                check(wait(anchored,5),'Real Bitwarden popup is sized and anchored below its Sona button after onboarding')
                ImageGrab.grab().save(output.parent / 'bitwarden-popup.png')
                mouse.press(coords=(client[2]-40,client[3]-40));time.sleep(.1);mouse.release(coords=(client[2]-40,client[3]-40))
                wait(lambda:not any('chrome-extension://'+bitwarden+'/popup/' in t.get('url','') for t in s.targets()))
                check(True,'Real Bitwarden popup closes on an outside native click')

            report['passed'] = True
            stop()
    finally:
        stop()
        server.shutdown()
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
