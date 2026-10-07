"""Physical Windows plus/Ctrl+T immediate typing and Ctrl+L focus acceptance."""
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
os.environ.update(SOULU_REGRESSION_SKIP_FIRST_RUN='1',NO_PROXY='localhost,127.0.0.1,::1')
u=C.windll.user32
u.SetProcessDPIAware()
u.GetForegroundWindow.restype=W.HWND
u.SetForegroundWindow.argtypes=[W.HWND]
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
u.ClientToScreen.argtypes=[W.HWND,C.POINTER(W.POINT)]
u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
u.IsWindowVisible.argtypes=[W.HWND]
u.BringWindowToTop.argtypes=[W.HWND]
class Keyboard(C.Structure):
 _fields_=[('vk',W.WORD),('scan',W.WORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
class Mouse(C.Structure):
 _fields_=[('x',W.LONG),('y',W.LONG),('data',W.DWORD),('flags',W.DWORD),('time',W.DWORD),('extra',C.c_size_t)]
class Payload(C.Union):
 _fields_=[('keyboard',Keyboard),('mouse',Mouse)]
class Input(C.Structure):
 _fields_=[('kind',W.DWORD),('payload',Payload)]
u.SendInput.argtypes=[W.UINT,C.POINTER(Input),C.c_int]
checks=[]

def wait(fn,timeout=30):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.03)
 raise AssertionError('Physical Home focus timeout')

def native_window(pid):
 handles=[];callback_type=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
 @callback_type
 def visit(hwnd,_):
  owner=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(owner));name=C.create_unicode_buffer(256);u.GetClassNameW(hwnd,name,len(name))
  if owner.value==pid and name.value=='SouluBrowserWindow' and u.IsWindowVisible(hwnd):handles.append(hwnd)
  return True
 u.EnumWindows(visit,0);return handles[0] if handles else None

def foreground(hwnd):
 u.SetForegroundWindow(hwnd)
 previous=u.GetForegroundWindow()
 if previous!=hwnd:
  thread=u.GetWindowThreadProcessId(previous,None);current=C.windll.kernel32.GetCurrentThreadId()
  u.AttachThreadInput(current,thread,True);u.BringWindowToTop(hwnd);u.SetForegroundWindow(hwnd);u.AttachThreadInput(current,thread,False)
 assert u.GetForegroundWindow()==hwnd,'Only the isolated Soulu window may receive native test input'

def text(value):
 events=[]
 raw=value.encode('utf-16-le')
 for i in range(0,len(raw),2):
  code=int.from_bytes(raw[i:i+2],'little')
  for flags in (4,6):
   event=Input();event.kind=1;event.payload.keyboard=Keyboard(0,code,flags,0,0);events.append(event)
 batch=(Input*len(events))(*events)
 assert u.SendInput(len(events),batch,C.sizeof(Input))==len(events),'Windows rejected native Unicode input'

def shortcut(key):
 u.keybd_event(17,0,0,0);u.keybd_event(ord(key),0,0,0);u.keybd_event(ord(key),0,2,0);u.keybd_event(17,0,2,0)

def main():
 exe=Path(sys.argv[1]).resolve();report=Path(sys.argv[2]).resolve();sockets=[]
 with tempfile.TemporaryDirectory(prefix='soulu-home-focus-',ignore_cleanup_errors=True) as root:
  process=subprocess.Popen([str(exe)],env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT)))
  def link(target):
   ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE);sockets.append(ws);return ws
  def home():
   active=s.evaluate(shell,'browserShell.getState()')['activeTabId']
   for target in s.targets():
    if '/ui/home.html' not in target.get('url',''):continue
    candidate=link(target)
    try:
     data=s.evaluate(candidate,"new Promise(resolve=>cefQuery({request:JSON.stringify({action:'home.get'}),onSuccess:v=>resolve(JSON.parse(v)),onFailure:()=>resolve({})}))")
     if data.get('tabId')==active and s.evaluate(candidate,"typeof window.souluHomeFocus==='function'"):return candidate
    except AssertionError:pass
   return None
  def check(ok,label):
   assert ok,label;checks.append(label);print('PASS:',label,flush=True)
  try:
   shell=link(wait(lambda:next((target for target in s.targets() if '/ui/index.html' in target.get('url','')),None)))
   wait(lambda:s.evaluate(shell,"typeof window.browserShell?.getState==='function'"));hwnd=wait(lambda:native_window(process.pid));foreground(hwnd)
   s.evaluate(shell,"browserShell.setSettings({layout:'compact',newTabMode:'soulu',homeMode:'soulu'})")
   wait(lambda:s.evaluate(shell,"document.querySelector('#compactNewTabButton').getBoundingClientRect().width>0"))
   # Finish the initial onboarding transition before starting the input test.
   initial=wait(home)
   wait(lambda:s.evaluate(initial,"document.readyState==='complete'"))
   s.evaluate(shell,"Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{})))")
   for action in ('plus','Ctrl+T'):
    before=len(s.evaluate(shell,'browserShell.getState()')['tabs']);foreground(hwnd)
    if action=='plus':
     point=s.evaluate(shell,"(()=>{const r=document.querySelector('#compactNewTabButton').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
     screen=W.POINT(round(point['x']),round(point['y']));u.ClientToScreen(hwnd,C.byref(screen));u.SetCursorPos(screen.x,screen.y);time.sleep(.15);u.mouse_event(2,0,0,0,0);time.sleep(.05);u.mouse_event(4,0,0,0,0)
    else:shortcut('T')
    # No DOM wait, click, focus call or navigation bridge between creation and input.
    print('INPUT',action,'tabs before',before,'window',hwnd,'point',point if action=='plus' else None,flush=True);text('openai.com')
    wait(lambda:len(s.evaluate(shell,'browserShell.getState()')['tabs'])==before+1);page=wait(home)
    wait(lambda:s.evaluate(page,"document.querySelector('#query').value==='openai.com'"))
    check(s.evaluate(page,"document.activeElement.id==='query'&&document.hasFocus()"),action+' immediately retains all native typed characters in Home')
   shortcut('L');wait(lambda:s.evaluate(shell,"['compactAddress','classicAddress'].includes(document.activeElement?.id)"));text('github.com')
   wait(lambda:s.evaluate(shell,"document.activeElement.value==='github.com'"));check(True,'Native Ctrl+L sends following typing to the omnibox')
   shortcut('T');shortcut('L');wait(lambda:s.evaluate(shell,"['compactAddress','classicAddress'].includes(document.activeElement?.id)"));page=wait(home)
   wait(lambda:s.evaluate(page,"document.readyState==='complete'"));time.sleep(.2)
   check(s.evaluate(shell,"['compactAddress','classicAddress'].includes(document.activeElement?.id)&&document.hasFocus()"),'A late Home load does not steal native Ctrl+L focus')
   report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps({'passed':True,'checks':checks,'input':'Real Windows pointer and Unicode keyboard input; no programmatic Home focus.'},ensure_ascii=False,indent=2),encoding='utf-8')
  except Exception:
   print('PROCESS EXIT',process.poll(),flush=True)
   raise
  finally:
   for ws in sockets:
    try:ws.close()
    except Exception:pass
   if process.poll() is None:s.close_normally(process)

if __name__=='__main__':main()
