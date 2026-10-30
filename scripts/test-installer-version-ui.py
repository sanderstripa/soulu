"""Read the actual packaged installer's WebView footer; no mocked product config."""
import base64,importlib.util,json,os,re,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
exe=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();output.parent.mkdir(parents=True,exist_ok=True)
header=(Path(__file__).resolve().parents[1]/'cef/soulu/app_version.h').read_text()
expected=re.findall(r'kSouluVersion\s*=\s*"([^"]+)"',header);assert len(expected)==1;expected=expected[0]
with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
with tempfile.TemporaryDirectory(prefix='soulu-installer-version-') as temporary:
 env=dict(os.environ,WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f'--remote-debugging-port={port} --remote-allow-origins=*',WEBVIEW2_USER_DATA_FOLDER=temporary)
 process=subprocess.Popen([str(exe)],env=env);ws=None;last_error="";last_targets=[]
 try:
  end=time.monotonic()+60
  while time.monotonic()<end:
   try:
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f'http://127.0.0.1:{port}/json/list',timeout=2) as response:targets=json.load(response)
    last_targets=[{k:t.get(k) for k in ('type','title','url')} for t in targets]
    for target in targets:
     if target.get('type')!='page' or not target.get('webSocketDebuggerUrl'):continue
     candidate=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=15,suppress_origin=True)
     result=s.evaluate(candidate,"document.getElementById('version')?.textContent||''")
     if result:ws=candidate;break
     candidate.close()
    if ws:break
   except Exception as error:last_error=repr(error)
   time.sleep(.2)
  if ws is None:from PIL import ImageGrab
   ImageGrab.grab().save(output.with_suffix('.failure.png'))
   diagnostic=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'WebView|Soulu|Setup' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Depth 3"],capture_output=True,text=True)
   print('INSTALLER_PROCESSES',diagnostic.stdout,flush=True)
   print('INSTALLER_DIAGNOSTICS',json.dumps({'exit':process.poll(),'targets':last_targets,'error':last_error}),flush=True)
  assert ws is not None,'Actual installer WebView footer not found'
  footer=s.evaluate(ws,"document.getElementById('version').textContent")
  assert expected in footer,{'expected':expected,'actualFooter':footer}
  shot=s.command(ws,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
  output.with_suffix('.png').write_bytes(base64.b64decode(shot['data']))
  output.write_text(json.dumps({'passed':True,'expected':expected,'actualFooter':footer,'binary':exe.name,'scope':'Actual packaged installer welcome window; does not simulate installation.'},ensure_ascii=False,indent=2))
  print('PASS: actual installer footer',repr(footer),'matches browser',expected,flush=True)
 finally:
  if ws:
   try:s.command(ws,'Page.close')
   except Exception:pass
   ws.close()
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
