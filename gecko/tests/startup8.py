"""Launch the actual portable EXE, count native windows, and close using WM_CLOSE."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
import ctypes as C,psutil
from ctypes import wintypes as W
report={'passed':False,'checks':{},'windows':[]};u=C.windll.user32
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.IsWindowVisible.argtypes=[W.HWND];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM]
def inventory():
 rows=[];callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
 def visit(h,_):
  pid=W.DWORD();u.GetWindowThreadProcessId(h,C.byref(pid))
  try:
   p=psutil.Process(pid.value)
   if Path(p.exe()).resolve() not in [binary,binary.parent.parent/'Soulu.exe']:return True
   title=C.create_unicode_buffer(512);cls=C.create_unicode_buffer(128);u.GetWindowTextW(h,title,512);u.GetClassNameW(h,cls,128)
   if u.IsWindowVisible(h) and cls.value in ['MozillaWindowClass','Ghost']:rows.append({'hwnd':int(h),'pid':pid.value,'title':title.value,'class':cls.value})
  except psutil.Error:pass
  return True
 cb=callback(visit);u.EnumWindows(cb,0);return rows
try:
 original=subprocess.Popen
 def launch(command,*a,**kw):return original([str(binary.parent.parent/'Soulu.exe'),'-marionette'],*a,**kw)
 subprocess.Popen=launch
 try:start()
 finally:subprocess.Popen=original
 time.sleep(4);report['windows']=inventory();report['chromeWindows']=chrome('return [...Services.wm.getEnumerator(null)].map(w=>({uri:w.document.documentURI,title:w.document.title,type:w.document.documentElement.getAttribute("windowtype"),hasSoulu:!!w.Soulu,hidden:!!w.__souluStartupHidden}))')
 check('launcher_opens_exactly_one_native_browser_window',len(report['windows'])==1,report['windows'])
 (out/'startup8.png').write_bytes(base64.b64decode(m.screenshot()))
 u.PostMessageW(report['windows'][0]['hwnd'],0x0010,0,0)
 check('normal_close_removes_all_browser_windows',wait(lambda:not inventory(),15))
 check('launcher_exits_after_normal_close',proc.wait(timeout=15)==0)
 report['passed']=True
finally:
 try:stop()
 finally:(out/'startup8.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
