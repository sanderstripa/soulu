"""Install an unpacked MV3 fixture through the real Chromium folder picker.

Verifies the Settings host, persistence and content scripts in normal Soulu tabs.
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
from pywinauto.controls.win32_controls import EditWrapper, ButtonWrapper


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

s = module('storage', 'test-cef-storage.py')
p = module('platform', 'test-cef-platform.py')
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN'] = '1'
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
    report = {'passed': False, 'checks': [], 'limitations': ['Store installation and Bitwarden account flows require separate acceptance.']}
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
                if fragment in target.get('url', ''):
                    ws = s.websocket.create_connection(target['webSocketDebuggerUrl'], timeout=35, origin=s.BASE)
                    connections.append(ws)
                    return ws
        return wait(find)

    def stop():
        nonlocal process
        for ws in connections:
            ws.close()
        connections.clear()
        if process:
            s.close_normally(process)
            process = None

    try:
        with tempfile.TemporaryDirectory(prefix='soulu-extensions-', ignore_cleanup_errors=True) as temporary:
            root = Path(temporary)
            extension = root / 'fixture'
            extension.mkdir()
            (extension / 'manifest.json').write_text(json.dumps({
                'manifest_version': 3, 'name': 'Soulu extension acceptance', 'version': '1.0',
                'permissions': ['storage'],
                'content_scripts': [{'matches': ['http://127.0.0.1/*'], 'js': ['content.js'], 'run_at': 'document_idle'}]
            }), encoding='utf-8')
            (extension / 'content.js').write_text("chrome.storage.local.set({verified:true});document.documentElement.dataset.souluExtensionFixture='active';", encoding='utf-8')
            env = dict(os.environ, LOCALAPPDATA=str(root / 'local'), APPDATA=str(root / 'roaming'),
                       SOULU_UI_TEST_PORT=str(s.DEBUG_PORT), SOULU_REGRESSION_SKIP_FIRST_RUN='1')

            def start():
                nonlocal process
                process = subprocess.Popen([executable, '--no-proxy-server'], env=env)
                shell = socket('/ui/index.html')
                wait(lambda: s.evaluate(shell, "typeof browserShell?.openSettingsWindow==='function'"))
                s.evaluate(shell, 'browserShell.openSettingsWindow()')
                settings = socket('/ui/settings.html')
                wait(lambda: s.evaluate(settings, "document.body.classList.contains('ready')"))
                s.evaluate(settings, "souluSettings.openSection('extensions')")
                manager = socket('chrome://extensions')
                wait(lambda: s.evaluate(manager, "typeof chrome.developerPrivate?.getExtensionsInfo==='function'"))
                return shell, settings, manager

            shell, settings, manager = start()
            check(s.evaluate(manager, 'typeof window.cefQuery') == 'undefined', 'Chrome surface has no Soulu bridge')
            s.evaluate(manager, 'chrome.developerPrivate.updateProfileConfiguration({inDeveloperMode:true})')
            # Do not await a promise while the native file picker blocks the UI.
            s.sequence += 1
            manager.send(json.dumps({'id': s.sequence, 'method': 'Runtime.evaluate', 'params': {
                'expression': "window.__loadResult=null;chrome.developerPrivate.loadUnpacked({failQuietly:true,populateError:true}).then(r=>window.__loadResult={result:r},e=>window.__loadResult={error:String(e)});true"}}))
            controls = wait(lambda: p.dialog_controls(process.pid))
            edits = [c for c in controls if c[1] == 'Edit']
            edit = next((e for e in edits if e[3] in (1001, 1148, 1152)), edits[-1])
            button = next(c for c in controls if c[1] == 'Button' and c[3] == 1)
            user = ctypes.windll.user32
            user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            user.GetAncestor.restype = ctypes.c_void_p
            user.SetForegroundWindow(user.GetAncestor(button[0], 2))
            EditWrapper(edit[0]).set_edit_text(str(extension.resolve()))
            ButtonWrapper(button[0]).click_input()
            result = wait(lambda: s.evaluate(manager, 'window.__loadResult'))
            check(not result.get('error') and result.get('result') is None, 'Unpacked MV3 installation through native picker')
            expression = "chrome.developerPrivate.getExtensionsInfo({includeDisabled:true,includeTerminated:true}).then(rows=>rows.find(r=>r.name==='Soulu extension acceptance')||null)"
            installed = wait(lambda: s.evaluate(manager, expression))
            report['extensionId'] = installed['id']
            s.evaluate(settings, 'souluSettingsRequestClose()')
            wait(lambda: not any('/ui/settings.html' in t.get('url', '') for t in s.targets()))
            s.evaluate(shell, 'browserShell.openTab(' + json.dumps(url) + ')')
            content = socket(url)
            check(wait(lambda: s.evaluate(content, "document.documentElement.dataset.souluExtensionFixture==='active'")), 'Content script runs in an ordinary Alloy Soulu tab')
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
            report['passed'] = True
            stop()
    finally:
        stop()
        server.shutdown()
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
