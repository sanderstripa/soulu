"""Exercise real CEF tab collapse, pinning, profile isolation and restart."""
import ctypes as C
from ctypes import wintypes as W
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
u=C.windll.user32
u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]

def wait(fn,timeout=35):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try:
            result=fn()
            if result:return result
        except Exception:
            pass
        time.sleep(.1)
    raise AssertionError('Timed out waiting for classic tab state')

def main():
    executable=str(Path(sys.argv[1]).resolve());out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
    checks=[]
    def check(value,label):
        assert value,label;checks.append(label);print('PASS:',label,flush=True)
    with tempfile.TemporaryDirectory(prefix='soulu-classic-',ignore_cleanup_errors=True) as root:
        env=dict(os.environ,LOCALAPPDATA=root,APPDATA=str(Path(root)/'roaming'),SOULU_UI_TEST_PORT=str(s.DEBUG_PORT))
        process=None;shell=None
        def state():return s.evaluate(shell,'browserShell.getState()')
        def call(method,value=None):return s.evaluate(shell,'browserShell.'+method+'('+('' if value is None else json.dumps(value))+')')
        def start():
            nonlocal process,shell
            process=subprocess.Popen([executable,'--no-proxy-server'],env=env)
            target=wait(lambda:next((x for x in s.targets() if '/ui/index.html' in x.get('url','')),None))
            shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
            wait(lambda:s.evaluate(shell,'!!window.browserShell && !!document.querySelector("#classicPinnedTabs")'))
            wait(lambda:state().get('tabs'))
        def stop():
            nonlocal process,shell
            if shell:
                shell.close();shell=None
            if process:
                s.close_normally(process);process=None
        def resize(width):
            handles=[]
            @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
            def visit(hwnd,_):
                pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));name=C.create_unicode_buffer(128);u.GetClassNameW(hwnd,name,128)
                if pid.value==process.pid and name.value=='SouluBrowserWindow':handles.append(hwnd)
                return True
            u.EnumWindows(visit,0)
            if not handles:raise AssertionError('Native browser window missing')
            u.SetWindowPos(handles[0],None,80,80,width,650,0x0004|0x0010)
        def sample():
            return s.evaluate(shell,'''(()=>{const strip=document.querySelector('#tabStrip'),a=strip.querySelector('.classic-tab.active');if(!a)return null;
              const r=strip.getBoundingClientRect(),b=a.getBoundingClientRect();return {compact:strip.classList.contains('icons-only'),
              activeWidth:b.width,visible:b.left>=r.left-1&&b.right<=r.right+1,
              title:getComputedStyle(a.querySelector('strong')).display!=='none',
              close:getComputedStyle(a.querySelector('[data-close-tab]')).visibility==='visible',
              inactive:[...strip.querySelectorAll('.classic-tab:not(.active)')].map(x=>x.getBoundingClientRect().width)};})()''')
        try:
            start();call('setSettings',{'layout':'classic','startupMode':'continue'})
            wait(lambda:s.evaluate(shell,"document.body.dataset.layout==='classic'"))
            for _ in range(9):call('newTab')
            wait(lambda:len(state()['tabs'])==10)
            resize(640);narrow=wait(lambda:(v if v['compact'] and v['visible'] else None) if (v:=sample()) else None)
            check(narrow['activeWidth']==160 and narrow['title'] and narrow['close'] and all(w==30 for w in narrow['inactive']),'Narrow row keeps active title and close; other tabs become icons')
            normal=state()['tabs'];pinned_id=normal[0]['id'];call('pinTab',pinned_id)
            wait(lambda:any(t['id']==pinned_id and t.get('pinned') for t in state()['tabs']))
            check(s.evaluate(shell,"document.querySelector('#classicPinnedTabs .pinned')?.getBoundingClientRect().width===30"),'Pinned tab is a separate circle')
            call('switchTab',pinned_id)
            check(bool(wait(lambda:s.evaluate(shell,"(()=>{const p=document.querySelector('#classicPinnedTabs .pinned.active');return p&&p.getBoundingClientRect().width===160&&getComputedStyle(p.querySelector('strong')).display!=='none'&&getComputedStyle(p.querySelector('[data-close-tab]')).visibility==='visible'})()"))),'Active pinned tab keeps title and close when compressed')
            active_id=next(t['id'] for t in state()['tabs'] if not t['pinned'] and not t['active']);call('switchTab',active_id)
            check(bool(wait(lambda:(v if v['visible'] and v['title'] and v['close'] else None) if (v:=sample()) else None)),'Switching reveals the active expanded tab')
            resize(1600)
            expanded=wait(lambda:(v if not v['compact'] else None) if (v:=sample()) else None)
            check(all(w>=112 for w in expanded['inactive']),'Wider window expands the other tabs again')
            call('createProfile','Classic isolation');other=state()['activeProfileId']
            check(other!='personal' and all(not t.get('pinned') for t in state()['tabs']),'Pinned tabs do not leak into another profile')
            call('switchProfile','personal');wait(lambda:state()['activeProfileId']=='personal')
            check(any(t.get('pinned') for t in state()['tabs']),'Pinned tab returns with its own profile')
            stop();start();wait(lambda:any(t.get('pinned') for t in state()['tabs']))
            check(sum(bool(t.get('pinned')) for t in state()['tabs'])==1,'Pinned tab survives normal restart')
            call('setSettings',{'layout':'compact'});wait(lambda:s.evaluate(shell,"document.body.dataset.layout==='compact'"))
            check(bool(state()['tabs']),'Compact layout remains usable')
            stop();out.write_text(json.dumps({'passed':True,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
        finally:
            if shell:
                try:shell.close()
                except Exception:pass
            if process and process.poll() is None:process.kill();process.wait()

if __name__=='__main__':main()
