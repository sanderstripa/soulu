"""Exercise real HWND, CEF viewport, taskbar hit testing and nested fullscreen.

Uses the actual runner monitors/work areas. Does not claim synthetic DPI
overrides are physical mixed-DPI monitor coverage or desktop mouse clicks.
"""
import ctypes as C
from ctypes import wintypes as W
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

spec = importlib.util.spec_from_file_location('storage', Path(__file__).with_name('test-cef-storage.py'))
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
u = C.WinDLL('user32', use_last_error=True)
u.SetProcessDpiAwarenessContext.argtypes = [C.c_void_p]
u.SetProcessDpiAwarenessContext(C.c_void_p(-4))
for name in ['GetWindowRect', 'GetClientRect']:
    getattr(u, name).argtypes = [W.HWND, C.POINTER(W.RECT)]
u.MonitorFromWindow.argtypes = [W.HWND, W.DWORD]
u.MonitorFromWindow.restype = W.HANDLE
u.GetMonitorInfoW.argtypes = [W.HANDLE, C.c_void_p]
u.GetAncestor.argtypes = [W.HWND, W.UINT]
u.GetAncestor.restype = W.HWND
u.WindowFromPoint.argtypes = [W.POINT]
u.WindowFromPoint.restype = W.HWND
u.IsZoomed.argtypes = [W.HWND]
u.GetDpiForWindow.argtypes = [W.HWND]
u.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
u.ShowWindow.argtypes = [W.HWND, C.c_int]
u.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
u.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
u.IsWindowVisible.argtypes = [W.HWND]
u.GetParent.argtypes = [W.HWND]
u.GetParent.restype = W.HWND
CALLBACK = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
u.EnumWindows.argtypes = [CALLBACK, W.LPARAM]
u.EnumChildWindows.argtypes = [W.HWND, CALLBACK, W.LPARAM]
class Monitor(C.Structure):
    _fields_ = [('size', W.DWORD), ('monitor', W.RECT), ('work', W.RECT), ('flags', W.DWORD)]
class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'''<!doctype html><style>html,body{margin:0;background:#46a6cf}video{width:300px}</style>
<canvas id=c width=160 height=90></canvas><video id=v muted autoplay></video>
<script>const ctx=c.getContext('2d');setInterval(()=>{ctx.fillStyle='#46a6cf';ctx.fillRect(0,0,160,90)},30);v.srcObject=c.captureStream(25);v.play();</script>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', s.free_port()), Fixture)
threading.Thread(target=server.serve_forever, daemon=True).start()
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
checks = []

def wait(fn, timeout=15):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        try:
            result = fn()
            if result: return result
        except (AssertionError, OSError) as e: last = str(e)
        time.sleep(.05)
    raise AssertionError(f'Window state timed out: {last}')
def rect(hwnd, client=False):
    r = W.RECT()
    assert (u.GetClientRect if client else u.GetWindowRect)(hwnd, C.byref(r))
    return [r.left, r.top, r.right, r.bottom]
def monitor(hwnd):
    m = Monitor()
    m.size = C.sizeof(m)
    assert u.GetMonitorInfoW(u.MonitorFromWindow(hwnd, 2), C.byref(m))
    return m
def coords(r): return [r.left, r.top, r.right, r.bottom]
def windows(pid):
    found = []
    @CALLBACK
    def visit(hwnd, _):
        ident = W.DWORD()
        name = C.create_unicode_buffer(100)
        u.GetWindowThreadProcessId(hwnd, C.byref(ident))
        u.GetClassNameW(hwnd, name, 100)
        if ident.value == pid and name.value == 'SouluBrowserWindow': found.append(hwnd)
        return True
    u.EnumWindows(visit, 0)
    return found
def key(ws, code):
    s.command(ws, 'Input.dispatchKeyEvent', dict(type='rawKeyDown', windowsVirtualKeyCode=code, nativeVirtualKeyCode=code))
    s.command(ws, 'Input.dispatchKeyEvent', dict(type='keyUp', windowsVirtualKeyCode=code, nativeVirtualKeyCode=code))
def viewport(page, hwnd, inset):
    def sample():
        r = rect(hwnd, True)
        actual = s.evaluate(page, '[innerWidth,innerHeight,devicePixelRatio]')
        assert abs(actual[0]*actual[2]-(r[2]-r[0])) <= actual[2]
        assert abs(actual[1]*actual[2]-(r[3]-r[1]-inset)) <= actual[2]
        return actual
    return wait(sample)
def taskbar_excluded(hwnd):
    m = monitor(hwnd)
    outer = rect(hwnd)
    work = coords(m.work)
    assert work[0] <= outer[0] < outer[2] <= work[2] and work[1] <= outer[1] < outer[3] <= work[3], (outer, work)
    # Verify real WindowFromPoint at every pixel grid sample outside rcWork.
    # A transparent top-level HWND is still an input hit: visual clipping fails.
    samples = []
    for x in range(m.monitor.left+2, m.monitor.right, max(1,(m.monitor.right-m.monitor.left)//24)):
        for y in [m.monitor.top+1, m.monitor.bottom-2]:
            if m.work.left <= x < m.work.right and m.work.top <= y < m.work.bottom: continue
            hit = u.WindowFromPoint(W.POINT(x,y))
            assert u.GetAncestor(hit,2) != hwnd, (x,y,hit)
            samples.append([x,y,int(hit or 0)])
    for y in range(m.monitor.top+2, m.monitor.bottom, max(1,(m.monitor.bottom-m.monitor.top)//24)):
        for x in [m.monitor.left+1,m.monitor.right-2]:
            if m.work.left <= x < m.work.right and m.work.top <= y < m.work.bottom: continue
            hit = u.WindowFromPoint(W.POINT(x,y))
            assert u.GetAncestor(hit,2) != hwnd, (x,y,hit)
            samples.append([x,y,int(hit or 0)])
    return dict(bounds=outer, work=work, taskbar_input_samples=samples)
def enter_video(page):
    result = s.command(page, 'Runtime.evaluate', dict(expression='v.requestFullscreen()', userGesture=True, awaitPromise=True, returnByValue=True))
    assert 'exceptionDetails' not in result, result
    wait(lambda:s.evaluate(page, 'document.fullscreenElement===v'))
def exit_video(page):
    s.evaluate(page, 'document.exitFullscreen()')
    wait(lambda:s.evaluate(page, '!document.fullscreenElement'))

process = None
try:
    with tempfile.TemporaryDirectory(prefix='soulu-window-', ignore_cleanup_errors=True) as profile:
        env = dict(os.environ, LOCALAPPDATA=profile, APPDATA=profile, SOULU_REGRESSION_SKIP_FIRST_RUN='1')
        process = subprocess.Popen([str(Path(sys.argv[1]).resolve())], env=env)
        page = s.page_socket()
        target = next(t for t in s.targets() if '/ui/index.html' in t.get('url',''))
        shell = s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
        hwnd = wait(lambda:next(iter(windows(process.pid)),None))
        s.navigate(page, f'http://127.0.0.1:{server.server_port}/')
        for layout in ['compact','classic']:
            for matte in [False,True]:
                for theme in ['light','dark','system']:
                    s.evaluate(shell, 'browserShell.setSettings('+json.dumps(dict(layout=layout,mattePanel=matte,theme=theme,bookmarksBarPosition='hidden'))+')')
                    u.ShowWindow(hwnd,9)
                    m = monitor(hwnd)
                    u.SetWindowPos(hwnd,None,m.work.left+30,m.work.top+30,900,640,0x14)
                    original = rect(hwnd)
                    inset = round((58 if layout=='compact' else 82)*u.GetDpiForWindow(hwnd)/96)
                    viewport(page,hwnd,inset)
                    for maximized in [False,True]:
                        if maximized:
                            u.ShowWindow(hwnd,3)
                            wait(lambda:u.IsZoomed(hwnd))
                            viewport(page,hwnd,inset)
                            evidence = taskbar_excluded(hwnd)
                        else: evidence = dict(bounds=original)
                        previous = rect(hwnd)
                        key(page,122)
                        wait(lambda:rect(hwnd)==coords(monitor(hwnd).monitor))
                        viewport(page,hwnd,0)
                        assert s.evaluate(shell,'browserShell.getState().then(s=>s.fullscreen)')
                        # F11 contains HTML5 fullscreen; HTML5 exit must retain F11.
                        enter_video(page)
                        exit_video(page)
                        wait(lambda:rect(hwnd)==coords(monitor(hwnd).monitor))
                        key(page,122)
                        wait(lambda:rect(hwnd)==previous and bool(u.IsZoomed(hwnd))==maximized)
                        viewport(page,hwnd,inset)
                        # HTML5 alone restores exactly the original normal/max state.
                        enter_video(page)
                        wait(lambda:rect(hwnd)==coords(monitor(hwnd).monitor))
                        viewport(page,hwnd,0)
                        key(page,27)
                        wait(lambda:not s.evaluate(page,'!!document.fullscreenElement'))
                        wait(lambda:rect(hwnd)==previous and bool(u.IsZoomed(hwnd))==maximized)
                        viewport(page,hwnd,inset)
                        evidence.update(layout=layout,matte=matte,theme=theme,maximized=maximized,dpi=u.GetDpiForWindow(hwnd),nested_fullscreen=True,video_playing=s.evaluate(page,'!v.paused'))
                        checks.append(evidence)
                    u.ShowWindow(hwnd,9)
                    wait(lambda:rect(hwnd)==original)
        shell.close();page.close();s.close_normally(process);process=None
    (out/'window-states.json').write_text(json.dumps(dict(passed=True,checks=checks,limits='Actual available monitor/DPI/taskbar configuration only; hit testing is not a manual Start/tray click check.'),indent=2),encoding='utf-8')
    print(f'PASS: {len(checks)} native states; F11, nested HTML5 video, exact restore, work-area/input exclusion and CEF viewport')
finally:
    if process and process.poll() is None:process.kill()
    server.shutdown()
