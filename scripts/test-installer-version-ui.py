"""Read the packaged installer's actual WebView footer, without mocking config."""
import base64
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import winreg

spec = importlib.util.spec_from_file_location('storage', Path(__file__).with_name('test-cef-storage.py'))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

@contextlib.contextmanager
def debug_policy(exe, arguments):
    # WebView2 ignores environment/HKCU overrides for elevated hosts. Scope the
    # documented HKLM override to this EXE on an ephemeral Actions VM only.
    assert os.environ.get('GITHUB_ACTIONS') == 'true', 'Run this acceptance test on its isolated Windows Actions VM'
    path = r'SOFTWARE\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments'
    access = winreg.KEY_READ | winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
    with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, access) as key:
        try:
            previous = winreg.QueryValueEx(key, exe.name)
        except FileNotFoundError:
            previous = None
        try:
            winreg.SetValueEx(key, exe.name, 0, winreg.REG_SZ, arguments)
            yield
        finally:
            if previous is None:
                winreg.DeleteValue(key, exe.name)
            else:
                winreg.SetValueEx(key, exe.name, 0, previous[1], previous[0])

exe = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).resolve()
output.parent.mkdir(parents=True, exist_ok=True)
header = (Path(__file__).resolve().parents[1] / 'cef/soulu/app_version.h').read_text()
versions = re.findall(r'kSouluVersion\s*=\s*"([^"]+)"', header)
assert len(versions) == 1
expected = versions[0]
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
arguments = f'--remote-debugging-port={port} --remote-allow-origins=*'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with tempfile.TemporaryDirectory(prefix='soulu-installer-version-') as temporary, debug_policy(exe, arguments):
    env = dict(os.environ, WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=arguments, WEBVIEW2_USER_DATA_FOLDER=temporary)
    process = subprocess.Popen([str(exe)], env=env)
    ws = None
    error = ''
    targets = []
    try:
        end = time.monotonic() + 60
        while time.monotonic() < end:
            try:
                with opener.open(f'http://127.0.0.1:{port}/json/list', timeout=2) as response:
                    targets = json.load(response)
                for target in targets:
                    if target.get('type') != 'page' or not target.get('webSocketDebuggerUrl'):
                        continue
                    candidate = s.websocket.create_connection(target['webSocketDebuggerUrl'], timeout=10, suppress_origin=True)
                    if s.evaluate(candidate, "document.getElementById('version')?.textContent||''"):
                        ws = candidate
                        break
                    candidate.close()
                if ws:
                    break
            except Exception as exception:
                error = repr(exception)
            time.sleep(.2)
        if ws is None:
            from PIL import ImageGrab
            ImageGrab.grab().save(output.with_suffix('.failure.png'))
            print('INSTALLER_DIAGNOSTICS', json.dumps({'exit': process.poll(), 'targets': [{'type': t.get('type'), 'url': t.get('url')} for t in targets], 'error': error}), flush=True)
        assert ws is not None, 'Actual installer WebView footer not found'
        footer = s.evaluate(ws, "document.getElementById('version').textContent")
        shot = s.command(ws, 'Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
        output.with_suffix('.png').write_bytes(base64.b64decode(shot['data']))
        passed = bool(re.search(r'(?<![\w.-])' + re.escape(expected) + r'(?![\w.-])', footer))
        output.write_text(json.dumps({'passed': passed, 'expected': expected, 'actualFooter': footer, 'binary': exe.name, 'scope': 'Actual packaged installer welcome window; does not simulate installation.'}, ensure_ascii=False, indent=2), encoding='utf-8')
        assert passed, {'expected': expected, 'actualFooter': footer}
        print('PASS: actual installer footer', repr(footer), 'matches browser', expected, flush=True)
    finally:
        if ws:
            try:
                s.command(ws, 'Page.close')
            except Exception:
                pass
            ws.close()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
