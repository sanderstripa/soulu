"""Reproduce the user's exact dialog with the real published Preview 16 launcher."""
from pathlib import Path
prefix=Path(__file__).with_name('restart17.py').read_text().split('\ntry:\n for cycle',1)[0]
exec(compile(prefix,str(Path(__file__).with_name('restart17.py')),'exec'),globals())
try:
 p=subprocess.Popen([str(base/'Soulu.exe')],env=env)
 def busy_dialog():
  result=[]
  @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
  def child(hwnd,_):
   text=C.create_unicode_buffer(2048);user.GetWindowTextW(hwnd,text,2048)
   if 'The profile is starting or busy. Try again shortly.' in text.value:result.append(text.value)
   return True
  @C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
  def top(hwnd,_):
   pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,C.byref(pid))
   if pid.value==p.pid and user.IsWindowVisible(hwnd):user.EnumChildWindows(hwnd,child,0)
   return True
  user.EnumWindows(top,0);return result
 message=wait(busy_dialog,25)
 check('preview16_reproduces_exact_busy_dialog_with_unowned_mutex',bool(message),message)
 check('preview16_did_not_start_engine',not any(x.name().lower()=='souluengine.exe' for x in processes()))
 ImageGrab.grab().save(out/'preview16-busy-dialog.png');report['passed']=True
finally:
 C.windll.kernel32.CloseHandle(retained)
 (out/'busy17.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));server.shutdown()
 for p in processes():
  try:p.kill()
  except psutil.Error:pass
