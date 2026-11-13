"""Launch the actual portable EXE after extracting the final ZIP into a spaced path."""
import json,os,pathlib,socket,subprocess,sys,tempfile,time,zipfile
from marionette_driver.marionette import Marionette
archive=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);result={'passed':False};out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='Sona ZIP extraction ') as tmp:
 root=pathlib.Path(tmp);package=root/'Sona Portable Browser';package.mkdir()
 with zipfile.ZipFile(archive) as z:z.extractall(package)
 profile=root/'userdata/SonaGecko/Profiles/default';profile.mkdir(parents=True)
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 (profile/'user.js').write_text('user_pref("remote.prefs.recommended",false);user_pref("marionette.port",'+str(port)+');',encoding='utf-8')
 launcher=package/'Sona.exe' if (package/'Sona.exe').exists() else package/'Sona Gecko Preview 4.exe'
 process=subprocess.Popen([str(launcher),'-marionette'],env=dict(os.environ,LOCALAPPDATA=str(root/'userdata'),MOZ_REMOTE_ALLOW_SYSTEM_ACCESS='1',SONA_GECKO_TEST='1',PATH=os.path.join(os.environ['SystemRoot'],'System32')))
 m=None
 try:
  deadline=time.time()+60
  while True:
   try:
    with socket.create_connection(('127.0.0.1',port),timeout=.2):break
   except OSError:
    if time.time()>deadline or process.poll() is not None:raise RuntimeError('Extracted launcher failed')
    time.sleep(.2)
  m=Marionette('127.0.0.1',port=port);m.start_session();m.set_context('chrome');deadline=time.time()+45
  while not m.execute_script('return !!window.Sona?.ready&&document.documentElement.hasAttribute("sona-ui-ready")'):
   if time.time()>deadline:raise RuntimeError('Sona did not initialize')
   time.sleep(.2)
  result.update(passed=True,profile=m.execute_script('return PathUtils.profileDir'),runtime=m.execute_script('return Services.dirsvc.get("GreD",Ci.nsIFile).path'))
  assert result['runtime'].startswith(str(package)) and result['profile']==str(profile)
 finally:
  if m:
   try:m._request_in_app_shutdown()
   except Exception:pass
  try:process.wait(timeout=20)
  except subprocess.TimeoutExpired:process.kill();process.wait()
  (out/'zip-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Extracted ZIP launcher passed')
