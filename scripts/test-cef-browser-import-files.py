"""Native Windows pickers and real HTML/CSV/portable import using synthetic data."""
import ctypes,importlib.util,json,os,site,subprocess,sys,tempfile
from pathlib import Path
repo=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('test',repo/'scripts/test-cef-browser-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);s=m.s
spec=importlib.util.spec_from_file_location('platform',repo/'scripts/test-cef-platform.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
from pywinauto.controls.win32_controls import EditWrapper,ButtonWrapper
exe=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();s.DEBUG_PORT=s.free_port();s.BASE=f'http://127.0.0.1:{s.DEBUG_PORT}';checks=[]
with tempfile.TemporaryDirectory(prefix='soulu-import-pickers-',ignore_cleanup_errors=True) as tmp:
 root=Path(tmp);local=root/'local';roaming=root/'roaming';local.mkdir();roaming.mkdir();portable=root/'portable';portable.mkdir();(portable/'Preferences').write_text('{}');(portable/'Bookmarks').write_text('{"roots":{"bookmark_bar":{"type":"folder","name":"Fixture","children":[]}}}')
 html=root/'bookmarks.html';html.write_text('<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><DT><A HREF="https://example.test/picker">Synthetic bookmark</A></DL>');csv=root/'passwords.csv';csv.write_text('url,username,password\nhttps://example.test/,fixture,synthetic-picker-only\n')
 env=dict(os.environ,LOCALAPPDATA=str(local),APPDATA=str(roaming),SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1');process=subprocess.Popen([str(exe),'--no-proxy-server'],env=env);sockets=[]
 def socket(fragment):
  def find():
   for row in s.targets():
    if fragment in row.get('url',''):
     ws=s.websocket.create_connection(row['webSocketDebuggerUrl'],timeout=40,origin=s.BASE);sockets.append(ws);return ws
  return m.wait(find)
 try:
  shell=socket('/ui/index.html');m.wait(lambda:s.evaluate(shell,"typeof window.browserShell?.browserImport==='function'"));s.evaluate(shell,'browserShell.openSettingsWindow()');settings=socket('/ui/settings.html');m.wait(lambda:s.evaluate(settings,"document.body?.classList.contains('ready')"))
  def pick(action,kind=None,path=None):
   expression='window.__pickerResult=null;browserShell.browserImport('+json.dumps(action)+(','+json.dumps({'kind':kind}) if kind else '')+').then(r=>window.__pickerResult=r,e=>window.__pickerResult={error:String(e)});true'
   s.sequence+=1;settings.send(json.dumps({'id':s.sequence,'method':'Runtime.evaluate','params':{'expression':expression}}));controls=m.wait(lambda:p.dialog_controls(process.pid));u=ctypes.windll.user32;u.GetAncestor.argtypes=[ctypes.c_void_p,ctypes.c_uint];u.GetAncestor.restype=ctypes.c_void_p
   if path:
    edits=[c for c in controls if c[1]=='Edit'];print('Picker edit control IDs:',[e[3] for e in edits],flush=True);edit=next((e for e in edits if e[3] in (1001,1148,1152)),edits[-1]);button=next(c for c in controls if c[1]=='Button' and c[3]==1);u.SetForegroundWindow(u.GetAncestor(button[0],2));EditWrapper(edit[0]).set_edit_text(str(path.resolve()));ButtonWrapper(button[0]).click_input()
   else:
    button=next(c for c in controls if c[1]=='Button' and c[3]==2);u.SetForegroundWindow(u.GetAncestor(button[0],2));ButtonWrapper(button[0]).click_input()
   result=m.wait(lambda:(r,) if (r:=s.evaluate(settings,'window.__pickerResult')) is not None else None)[0];assert 'error' not in result,result;return result
  assert pick('file','bookmarks')=={};checks.append('cancelled-native-picker-does-not-start-import')
  h=pick('file','bookmarks',html);assert h['kind']=='bookmarks' and 'text' in h;checks.append('native-HTML-file-picker')
  c=pick('file','passwords',csv);assert c['kind']=='passwords' and 'text' not in c and 'synthetic-picker-only' not in json.dumps(c);checks.append('native-CSV-picker-does-not-send-passwords-to-renderer')
  f=pick('portable',path=portable);assert f['family']=='chromium' and f['id'].startswith('portable:');checks.append('native-portable-profile-folder-picker')
  def run(payload):return s.evaluate(settings,'browserShell.browserImport("run",'+json.dumps(payload)+')')
  nodes=s.evaluate(settings,'souluBrowserImport.parseHtml('+json.dumps(h['text'])+')')
  payload={'source':h['id'],'target':'personal','bookmarks':True,'nodes':nodes}
  assert run(payload)['categories']['bookmarks']['imported']==1;checks.append('native-HTML-bookmark-import')
  assert run(payload)['categories']['bookmarks']['imported']==0;checks.append('native-HTML-repeat-deduplication')
  rejected=s.evaluate(settings,'browserShell.browserImport("run",'+json.dumps({'source':c['id'],'target':'personal','passwords':True})+').then(()=>false,()=>true)')
  assert rejected;checks.append('native-CSV-requires-explicit-password-consent')
  assert run({'source':c['id'],'target':'personal','passwords':True,'consent':True})['categories']['passwords']['imported']==1;checks.append('native-CSV-password-import')
  assert run({'source':h['id'],'target':'personal','tabs':True,'nodes':nodes})['categories']['tabs']['imported']==1;checks.append('native-HTML-open-tab-import')
  assert run({'source':f['id'],'target':'personal','bookmarks':True})['categories']['bookmarks']['imported']==1;checks.append('native-portable-profile-import')
  output.write_text(json.dumps({'ok':True,'checks':checks,'personalDataUsed':False},indent=2),encoding='utf-8');print('PASS:',checks,flush=True)
 finally:
  for ws in sockets:ws.close()
  if process.poll() is None:s.close_normally(process)
