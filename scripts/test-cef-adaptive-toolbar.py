"""Native third layout: synchronized animation, live documents, profiles and resize."""
import base64
import ctypes as C
from ctypes import wintypes as W
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
u=C.windll.user32
u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
u.GetParent.argtypes=[W.HWND];u.GetParent.restype=W.HWND
u.GetDpiForWindow.argtypes=[W.HWND];u.GetDpiForWindow.restype=W.UINT
u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
u.MapWindowPoints.argtypes=[W.HWND,W.HWND,C.POINTER(W.POINT),W.UINT]

def wait(fn,timeout=40):
    end=time.monotonic()+timeout
    last=None
    while time.monotonic()<end:
        try:
            value=fn()
            if value:return value
        except Exception as error:last=repr(error)
        time.sleep(.08)
    raise AssertionError('Adaptive toolbar timeout; last error: '+str(last))

class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'<title>Adaptive live document</title><input id="draft"><div style="height:3500px"></div><script>window.identity=Math.random();window.ticks=0;setInterval(()=>ticks++,50)</script>'
        self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass

def main():
    exe=str(Path(sys.argv[1]).resolve());out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
    evidence={'checks':[]};process=None;shell=None;page=None
    server=ThreadingHTTPServer(('127.0.0.1',0),Fixture);threading.Thread(target=server.serve_forever,daemon=True).start()
    def check(value,label):
        assert value,label;evidence['checks'].append(label);print('PASS:',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='soulu-adaptive-',ignore_cleanup_errors=True) as root:
        profile=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal';profile.mkdir(parents=True)
        (profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'status':'skipped'},'layout':'adaptive','startupMode':'continue','newTabMode':'blank','bookmarksBarMode':'never','theme':'dark','mattePanel':False}),encoding='utf-8')
        env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT))
        def state():return s.evaluate(shell,'browserShell.getState()')
        def call(method,value=None):return s.evaluate(shell,'browserShell.'+method+'('+('' if value is None else json.dumps(value))+')')
        def start():
            nonlocal process,shell
            process=subprocess.Popen([exe,'--no-proxy-server'],env=env)
            target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None))
            shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
            wait(lambda:s.evaluate(shell,"!!window.browserShell&&!!window.souluAdaptiveToolbar"))
            wait(lambda:state().get('tabs'))
        def stop():
            nonlocal process,shell
            shell.close();shell=None;s.close_normally(process);process=None
        def settled(expanded):
            expected=88 if expanded else 68
            return wait(lambda:state()['adaptiveToolbar']['height']==expected and not state()['adaptiveToolbar']['running'] and s.evaluate(shell,"document.querySelector('.classic-toolbar').offsetHeight")==expected)
        def window():
            found=[]
            @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
            def visit(hwnd,_):
                pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));name=C.create_unicode_buffer(128);u.GetClassNameW(hwnd,name,128)
                if pid.value==process.pid and name.value=='SouluBrowserWindow':found.append(hwnd)
                return True
            u.EnumWindows(visit,0);return found[0]
        def native_inset(expected):
            hwnd=window();found=[]
            @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
            def visit(child,_):
                name=C.create_unicode_buffer(128);u.GetClassNameW(child,name,128)
                if u.GetParent(child)==hwnd and u.IsWindowVisible(child) and name.value in ('CefBrowserWindow','Chrome_WidgetWin_1'):
                    r=W.RECT();u.GetWindowRect(child,C.byref(r));point=W.POINT(r.left,r.top);u.MapWindowPoints(None,hwnd,C.byref(point),1);found.append(point.y)
                return True
            u.EnumChildWindows(hwnd,visit,0)
            return any(abs(y-expected*u.GetDpiForWindow(hwnd)/96)<=1 for y in found)
        def capture(name):
            rect=s.evaluate(shell,'({width:innerWidth,height:innerHeight})')
            shot=s.command(shell,'Page.captureScreenshot',{'format':'png','clip':{'x':0,'y':0,'width':rect['width'],'height':min(rect['height'],116),'scale':1}})
            (out.parent/('adaptive-'+name+'.png')).write_bytes(base64.b64decode(shot['data']))
        try:
            start();settled(False)
            u.SetWindowPos(window(),None,80,80,980,650,0x0004|0x0010)
            check(native_inset(68),'Single adaptive tab uses the native 68px content inset')
            check(s.evaluate(shell,"document.querySelector('.tabs-zone').inert&&getComputedStyle(document.querySelector('.tabs-zone')).opacity==='0'"),'One tab hides and disables the bottom row')
            capture('single')
            url=f'http://127.0.0.1:{server.server_port}/adaptive-fixture';call('navigate',url)
            target=wait(lambda:next((t for t in s.targets() if '/adaptive-fixture' in t.get('url','')),None));page=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
            wait(lambda:s.evaluate(page,'typeof identity==="number"'))
            original=s.evaluate(page,"document.querySelector('#draft').value='Unsent text';scrollTo(0,777);({identity,scrollY})")
            first=state()['tabs'][0]['id'];generation=state()['tabs'][0]['generation']
            frames=s.evaluate(shell,"""new Promise(resolve=>{const frames=[],begin=performance.now();function tick(){frames.push({time:performance.now()-begin,height:document.querySelector('.classic-toolbar').getBoundingClientRect().height,progress:parseFloat(getComputedStyle(document.body).getPropertyValue('--adaptive-progress'))});if(performance.now()-begin<450)requestAnimationFrame(tick);else resolve(frames)}requestAnimationFrame(tick);browserShell.newTab()})""")
            evidence['expansionFrames']=frames;settled(True)
            check(len({round(f['height'],1) for f in frames})>=3,'Expansion contains intermediate frames rather than one geometry jump')
            check(state()['adaptiveToolbar']['duration'] in (90,200),'Animation respects the 200ms duration or Windows reduced motion')
            check(native_inset(88),'Expanded DOM and native page inset agree at 88px')
            check(s.evaluate(shell,"!document.querySelector('.tabs-zone').inert&&getComputedStyle(document.querySelector('.tabs-zone')).opacity==='1'"),'Second tab reveals the shared bottom tab row')
            capture('two')
            second=next(t['id'] for t in state()['tabs'] if t['id']!=first)
            call('closeTab',second);settled(False)
            after=s.evaluate(page,"({identity,scrollY,draft:document.querySelector('#draft').value,ticks})")
            check(after['identity']==original['identity'] and after['draft']=='Unsent text' and after['scrollY']==777 and after['ticks']>0,'Page document, form, scrolling and running script survive expansion and collapse')
            check(state()['tabs'][0]['generation']==generation,'Existing tab generation is unchanged by the transition')
            call('pinTab',first);call('newTab');settled(True)
            check(any(t.get('pinned') for t in state()['tabs']),'Pinned tabs count towards adaptive expansion')
            for _ in range(13):call('newTab')
            u.SetWindowPos(window(),None,80,80,640,650,0x0004|0x0010)
            wait(lambda:s.evaluate(shell,"document.querySelector('#tabStrip').classList.contains('icons-only')"))
            check(s.evaluate(shell,"(()=>{const a=document.querySelector('.classic-tab.active');return a.offsetWidth>=160&&getComputedStyle(a.querySelector('strong')).display!=='none'&&getComputedStyle(a.querySelector('button')).visibility==='visible'})()"),'Narrow row preserves active favicon, title and close button')
            capture('many')
            call('createProfile','Adaptive isolated');call('setSettings',{'layout':'adaptive'});settled(False)
            check(len(state()['tabs'])==1,'Other profile tabs do not keep the row expanded')
            call('switchProfile','personal');settled(True)
            call('newIncognito');settled(False)
            check(state()['incognito'] and len(state()['tabs'])==1,'Incognito counts only its visible tabs')
            call('closeTab',state()['activeTabId']);settled(True)
            for tab in state()['tabs']:
                if tab['id']!=first:call('closeTab',tab['id'])
            wait(lambda:len(state()['tabs'])==1);settled(False)
            call('setSettings',{'bookmarksBarMode':'always','bookmarksBarPosition':'above'})
            check(bool(wait(lambda:native_inset(96))),'Bookmarks add their native inset to the collapsed panel')
            call('setSettings',{'bookmarksBarMode':'never'})
            call('setSettings',{'layout':'classic'})
            check(bool(wait(lambda:s.evaluate(shell,"document.querySelector('.classic-toolbar').offsetHeight===86"))),'Classic retains its existing 86px layout')
            call('setSettings',{'layout':'compact'})
            check(bool(wait(lambda:s.evaluate(shell,"document.querySelector('.compact-toolbar').offsetHeight===58"))),'Compact retains its existing 58px layout')
            call('setSettings',{'layout':'adaptive'});settled(False)
            page.close();page=None;stop();start();settled(False)
            check(state()['settings']['layout']=='adaptive','Adaptive selection persists after normal restart')
            stop();evidence['passed']=True
        finally:
            if page:
                try:page.close()
                except Exception:pass
            if shell:
                try:shell.close()
                except Exception:pass
            if process and process.poll() is None:process.kill();process.wait()
            out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
            server.shutdown()
if __name__=='__main__':main()
