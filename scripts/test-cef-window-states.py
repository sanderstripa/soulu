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
u.SendMessageW.argtypes = [W.HWND,W.UINT,W.WPARAM,W.LPARAM]
u.SendMessageW.restype = C.c_ssize_t
u.ClientToScreen.argtypes = [W.HWND,C.POINTER(W.POINT)]
u.SetForegroundWindow.argtypes = [W.HWND]
u.GetForegroundWindow.restype = W.HWND
u.BringWindowToTop.argtypes = [W.HWND]
u.AttachThreadInput.argtypes = [W.DWORD,W.DWORD,W.BOOL]
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
class Titlebar(C.Structure):
    _fields_ = [('size', W.DWORD), ('bounds', W.RECT), ('states', W.DWORD*6), ('buttons', W.RECT*6)]
class FocusInfo(C.Structure):
    _fields_ = [('size',W.DWORD),('flags',W.DWORD),('active',W.HWND),('focus',W.HWND),('capture',W.HWND),('menu',W.HWND),('move',W.HWND),('caret',W.HWND),('caret_rect',W.RECT)]
u.GetGUIThreadInfo.argtypes=[W.DWORD,C.POINTER(FocusInfo)]
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

def available_monitors():
    found = []
    callback_type = C.WINFUNCTYPE(W.BOOL,W.HANDLE,W.HDC,C.POINTER(W.RECT),W.LPARAM)
    @callback_type
    def visit(handle,dc,r,param):
        m=Monitor();m.size=C.sizeof(m)
        assert u.GetMonitorInfoW(handle,C.byref(m))
        found.append(m)
        return True
    u.EnumDisplayMonitors(None,None,visit,0)
    return found

def caption_point(shell,hwnd,selector):
    box=s.evaluate(shell,'(()=>{const r=document.querySelector('+json.dumps(selector)+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()')
    point=W.POINT(round(box['x']*u.GetDpiForWindow(hwnd)/96),round(box['y']*u.GetDpiForWindow(hwnd)/96))
    u.ClientToScreen(hwnd,C.byref(point))
    return point

def native_caption_click(shell,hwnd,selector,cancel=False):
    # Native IsZoomed changes before CEF has published its resized caption.
    # Every click, including Restore, must use matching DOM/native hit bounds.
    point=wait(lambda:ready_caption(shell,hwnd,selector))
    foreground(hwnd)
    assert u.SetCursorPos(point.x,point.y)
    u.mouse_event(2,0,0,0,0)
    wait(lambda:s.evaluate(shell,"document.body.dataset.nativeCaptionPressed==='true'"))
    if cancel:assert u.SetCursorPos(point.x-180,point.y+140)
    u.mouse_event(4,0,0,0,0)
    wait(lambda:s.evaluate(shell,"!document.body.dataset.nativeCaptionPressed"))

def foreground(hwnd):
    u.SetForegroundWindow(hwnd)
    previous=u.GetForegroundWindow()
    if previous!=hwnd:
        thread=u.GetWindowThreadProcessId(previous,None)
        current=C.windll.kernel32.GetCurrentThreadId()
        u.AttachThreadInput(current,thread,True)
        try:u.BringWindowToTop(hwnd);u.SetForegroundWindow(hwnd)
        finally:u.AttachThreadInput(current,thread,False)
    assert u.GetForegroundWindow()==hwnd,'Only isolated Soulu may receive native test input'

def page_focus_ready(page,hwnd):
    info=FocusInfo();info.size=C.sizeof(info)
    assert u.GetGUIThreadInfo(u.GetWindowThreadProcessId(hwnd,None),C.byref(info))
    assert info.focus!=hwnd and u.GetAncestor(info.focus,2)==hwnd,('CEF native focus not yet restored',info.focus,hwnd)
    assert s.evaluate(page,'document.hasFocus()'),'CEF renderer focus not yet restored'
    return True

def ready_caption(shell,hwnd,selector):
    # CEF publishes the new DOM geometry asynchronously after native resize.
    # Re-read the point while waiting; a point from the previous size is stale.
    point=caption_point(shell,hwnd,selector)
    titlebar=Titlebar();titlebar.size=C.sizeof(titlebar)
    u.SendMessageW(hwnd,0x33f,0,C.addressof(titlebar))
    caption=titlebar.buttons[3]
    expected=round((48 if selector=='#windowMaximize' else 58)*u.GetDpiForWindow(hwnd)/96)
    assert abs(caption.bottom-caption.top-expected)<=1,('Caption layout not yet synchronized',caption.bottom-caption.top,expected)
    assert caption.left<=point.x<caption.right and caption.top<=point.y<caption.bottom,('Caption DOM/native bounds not yet synchronized',point.x,point.y)
    assert u.SendMessageW(hwnd,0x84,0,((point.y&0xffff)<<16)|(point.x&0xffff))==9,'Native maximize hit target not yet synchronized'
    return point

def address_ready(shell,hwnd,address):
    actual=s.evaluate(shell,'document.activeElement?.id')
    if actual==address:return True
    info=FocusInfo();info.size=C.sizeof(info)
    u.GetGUIThreadInfo(u.GetWindowThreadProcessId(hwnd,None),C.byref(info))
    name=C.create_unicode_buffer(100);u.GetClassNameW(info.focus,name,100)
    raise AssertionError(('Address did not receive focus',actual,address,'native focus',name.value,'active',info.active))

process = None
try:
    with tempfile.TemporaryDirectory(prefix='soulu-window-', ignore_cleanup_errors=True) as profile:
        env = dict(os.environ, LOCALAPPDATA=profile, APPDATA=profile, SOULU_REGRESSION_SKIP_FIRST_RUN='1')
        process = subprocess.Popen([str(Path(sys.argv[1]).resolve())], env=env)
        page = s.page_socket()
        target = next(t for t in s.targets() if '/ui/index.html' in t.get('url',''))
        shell = s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
        try:
            wait(lambda:s.evaluate(shell,"document.readyState==='complete' && !!window.browserShell?.setSettings"),timeout=45)
        except AssertionError:
            print('Shell startup diagnostics:',json.dumps(s.evaluate(shell,"({url:location.href,ready:document.readyState,title:document.title,cefQuery:typeof window.cefQuery,browserShell:typeof window.browserShell,scripts:[...document.scripts].map(n=>n.src),body:document.body?.innerText.slice(0,600)})")),flush=True)
            print('CEF targets:',json.dumps([{k:t.get(k) for k in ('url','title','type')} for t in s.targets()]),flush=True)
            raise
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
                    selector = '#windowMaximize' if layout=='classic' else '#compactWindowMaximize'
                    point=wait(lambda:ready_caption(shell,hwnd,selector))
                    titlebar=Titlebar();titlebar.size=C.sizeof(titlebar)
                    u.SendMessageW(hwnd,0x33f,0,C.addressof(titlebar))
                    caption=titlebar.buttons[3]
                    assert caption.left<=point.x<caption.right and caption.top<=point.y<caption.bottom
                    assert abs((caption.right-caption.left)-round(42*u.GetDpiForWindow(hwnd)/96))<=1
                    assert abs((caption.bottom-caption.top)-round((58 if layout=='compact' else 48)*u.GetDpiForWindow(hwnd)/96))<=1

                    if not matte and theme=='light':
                        native_caption_click(shell,hwnd,selector,cancel=True)
                        assert not u.IsZoomed(hwnd) and rect(hwnd)==original
                        native_caption_click(shell,hwnd,selector)
                        wait(lambda:u.IsZoomed(hwnd) and s.evaluate(shell,'(async()=> (await browserShell.getState()).maximized)()'))
                        taskbar_excluded(hwnd)
                        native_caption_click(shell,hwnd,selector)
                        wait(lambda:not u.IsZoomed(hwnd) and rect(hwnd)==original)
                        # Restoring root focus must route normal browser keys
                        # back to CEF, rather than leaving a keyboard dead end.
                        foreground(hwnd)
                        u.SendMessageW(hwnd,0x7,0,0)
                        wait(lambda:page_focus_ready(page,hwnd))
                        u.keybd_event(17,29,0,0);time.sleep(.1)
                        u.keybd_event(76,38,0,0);time.sleep(.1)
                        u.keybd_event(76,38,2,0);u.keybd_event(17,29,2,0)
                        address='classicAddress' if layout=='classic' else 'compactAddress'
                        wait(lambda:address_ready(shell,hwnd,address))
                        # Caption/Snap can focus the root instead of a CEF child.
                        # Exercise its native key route, including held-key repeat.
                        u.SendMessageW(hwnd,0x100,122,1)
                        wait(lambda:rect(hwnd)==coords(monitor(hwnd).monitor))
                        u.SendMessageW(hwnd,0x100,122,(1<<30)|1)
                        assert rect(hwnd)==coords(monitor(hwnd).monitor)
                        u.SendMessageW(hwnd,0x100,27,1)
                        wait(lambda:rect(hwnd)==original)
                        checks.append(dict(layout=layout,native_caption_click=True,pressed_cancel=True,root_fullscreen_keys=True,root_focus_ctrl_l=True))
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
        # Move a restored window to every actual monitor, then verify native
        # maximize/F11/current-monitor selection and exact restore at its DPI.
        displays = available_monitors()
        for display in displays:
            u.ShowWindow(hwnd,9)
            width=min(900,display.work.right-display.work.left-40)
            height=min(640,display.work.bottom-display.work.top-40)
            u.SetWindowPos(hwnd,None,display.work.left+20,display.work.top+20,width,height,0x14)
            wait(lambda:coords(monitor(hwnd).monitor)==coords(display.monitor))
            original=rect(hwnd)
            for maximized in [False,True]:
                if maximized:
                    u.ShowWindow(hwnd,3);wait(lambda:u.IsZoomed(hwnd))
                    taskbar_excluded(hwnd)
                previous=rect(hwnd)
                key(page,122)
                wait(lambda:rect(hwnd)==coords(display.monitor))
                viewport(page,hwnd,0)
                key(page,122)
                wait(lambda:rect(hwnd)==previous and bool(u.IsZoomed(hwnd))==maximized)
            u.ShowWindow(hwnd,9);wait(lambda:rect(hwnd)==original)
            checks.append(dict(monitor=coords(display.monitor),work=coords(display.work),primary=bool(display.flags&1),dpi=u.GetDpiForWindow(hwnd),monitor_transfer=True))
        shell.close();page.close();s.close_normally(process);process=None
    (out/'window-states.json').write_text(json.dumps(dict(passed=True,checks=checks,limits='Actual available monitor/DPI/taskbar configuration only; hit testing is not a manual Start/tray click check.'),indent=2),encoding='utf-8')
    print(f'PASS: {len(checks)} native states; F11, nested HTML5 video, exact restore, work-area/input exclusion and CEF viewport')
finally:
    if process and process.poll() is None:process.kill()
    server.shutdown()
