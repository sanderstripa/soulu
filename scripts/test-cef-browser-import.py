"""Real CEF import bridge, synthetic Windows profiles and restart persistence."""
import base64, ctypes, hashlib, http.server, importlib.util, json, os, sqlite3, struct, subprocess, sys, tempfile, threading, time
from pathlib import Path
spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['NO_PROXY']='localhost,127.0.0.1,::1';os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
checks=[]
def check(ok,name):
    if not ok:raise AssertionError(name)
    checks.append(name);print('PASS:',name,flush=True)
def wait(fn,timeout=35):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        result=fn()
        if result:return result
        time.sleep(.1)
    raise AssertionError('Import state timeout')
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'<title>Synthetic import page</title><form><input name=email autocomplete=email><input name=password type=password autocomplete=current-password></form>'
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
def db(path,sql):
    with sqlite3.connect(path) as c:c.executescript(sql)
def digest(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def main():
    exe=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='soulu-import-integration-',ignore_cleanup_errors=True) as temp:
        root=Path(temp);local=root/'local';roaming=root/'roaming';roaming.mkdir();source=local/'Google/Chrome/User Data/Default';source.mkdir(parents=True)
        url=f'http://127.0.0.1:{server.server_port}/fixture'
        (source/'Preferences').write_text('{}');(source.parent/'Local State').write_text('{"profile":{"info_cache":{"Default":{"name":"Synthetic import"}}}}')
        (source/'Bookmarks').write_text(json.dumps({'roots':{'bookmark_bar':{'type':'folder','name':'Toolbar','children':[{'type':'folder','name':'Work','children':[{'type':'url','name':'Fixture','url':url}]}]}}}))
        db(source/'History',f"CREATE TABLE urls(id INTEGER,url TEXT,title TEXT); CREATE TABLE visits(url INTEGER,visit_time INTEGER); INSERT INTO urls VALUES(1,'{url}','Fixture'); INSERT INTO visits VALUES(1,13344473600123000);")
        db(source/'Web Data',"CREATE TABLE autofill(name TEXT,value TEXT); INSERT INTO autofill VALUES('email','fixture@example.test'),('card-number','4111111111111111'); CREATE TABLE address_type_tokens(guid TEXT,type INTEGER,value TEXT); INSERT INTO address_type_tokens VALUES('fixture',3,'Synthetic name');")
        db(source/'Login Data',"CREATE TABLE logins(origin_url TEXT,username_value TEXT,password_value BLOB,blacklisted_by_user INTEGER);")
        class Blob(ctypes.Structure):_fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]
        secret=ctypes.create_string_buffer(b'synthetic-import-only');input=Blob(len(secret.value),ctypes.cast(secret,ctypes.POINTER(ctypes.c_ubyte)));sealed=Blob()
        check(ctypes.windll.crypt32.CryptProtectData(ctypes.byref(input),None,None,None,None,1,ctypes.byref(sealed)),'fixture-password-encryption')
        with sqlite3.connect(source/'Login Data') as c:c.execute('INSERT INTO logins VALUES(?,?,?,0)',(url,'fixture',ctypes.string_at(sealed.data,sealed.size)))
        ctypes.windll.kernel32.LocalFree(sealed.data)
        nav=struct.pack('<iii',10,0,len(url))+url.encode();nav+=b'\0'*(-len(nav)%4);nav+=struct.pack('<iii',0,0,0)
        command=lambda id,p:struct.pack('<HB',len(p)+1,id)+p
        session=b'SNSS'+struct.pack('<i',3)+command(0,struct.pack('<ii',10,1))+command(9,struct.pack('<ii',1,0))+command(6,struct.pack('<i',len(nav))+nav)+command(7,struct.pack('<ii',10,0))+command(255,b'')
        (source/'Sessions').mkdir();(source/'Sessions/Session_1').write_bytes(session);before=digest(source)
        env=dict(os.environ,LOCALAPPDATA=str(local),APPDATA=str(roaming),SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1')
        connections=[];process=None;shell=None;settings=None
        def socket(fragment):
            def find():
                for target in s.targets():
                    if fragment in target.get('url',''):
                        ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=35,origin=s.BASE);connections.append(ws);return ws
            return wait(find)
        def start():
            nonlocal process,shell,settings
            process=subprocess.Popen([str(exe),'--no-proxy-server'],env=env);shell=socket('/ui/index.html');wait(lambda:s.evaluate(shell,"typeof browserShell?.browserImport==='function'"))
            s.evaluate(shell,'browserShell.openSettingsWindow()');settings=socket('/ui/settings.html');wait(lambda:s.evaluate(settings,"document.body.classList.contains('ready')"))
        def stop():
            nonlocal process
            for ws in connections:
                try:ws.close()
                except Exception:pass
            connections.clear()
            if process:s.close_normally(process);process=None
        def call(action,value=None):return s.evaluate(settings,'browserShell.browserImport('+json.dumps(action)+(','+json.dumps(value) if value is not None else '')+')')
        payload={'source':'Chrome:Default','target':'personal','bookmarks':True,'history':True,'passwords':True,'consent':True,'autofill':True,'tabs':True}
        try:
            start();catalog=call('catalog');check(any(p['id']=='Chrome:Default' for b in catalog for p in b['profiles']),'native-discovery-and-profile-identity')
            caps=call('capabilities',{'source':'Chrome:Default'});check(all(caps[k]['status']=='available' for k in ('bookmarks','history','passwords','autofill','tabs')),'native-five-category-capabilities')
            check(digest(source)==before,'capability-probes-do-not-modify-source')
            profile=call('createProfile',{'name':'Import target fixture'});other=profile['id'];check(s.evaluate(shell,'browserShell.getState()')['activeProfileId']=='personal','inline-profile-creation-does-not-switch-profile')
            result=call('run',payload);check(result['status']=='ok' and all(result['categories'][k]['imported']>0 for k in ('bookmarks','history','passwords','autofill','tabs')),'all-five-categories-import-through-native-settings-bridge')
            again=call('run',payload);check(all(r['imported']==0 for r in again['categories'].values()),'repeat-import-deduplicates-all-categories')
            data=local/'Soulu/User Data';personal=data/'Profiles/personal';destination=data/'Profiles'/other
            check(not (destination/'soulu-autofill.json').exists() and not (destination/'soulu-passwords.json').exists(),'existing-target-profile-isolation')
            check(b'fixture@example.test' not in (personal/'soulu-autofill.json').read_bytes() and b'synthetic-import-only' not in (personal/'soulu-passwords.json').read_bytes(),'native-target-stores-encrypted')
            marks=s.evaluate(settings,'browserShell.getBookmarks()');check(any(r.get('parentId',0)>0 for r in marks) and len(marks)==3,'nested-bookmarks-visible-in-existing-bookmark-backend')
            check(digest(source)==before,'native-import-does-not-change-source-or-create-sidecars')
            s.evaluate(settings,'souluBrowserImport.open()');wait(lambda:s.evaluate(settings,"!!document.querySelector('dialog[open] #importFrom')"));check(s.evaluate(settings,"document.querySelectorAll('dialog[open]').length")==1,'real-CEF-compact-import-dialog')
            screenshot=s.command(settings,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(output.parent/'browser-import-native-window.png').write_bytes(base64.b64decode(screenshot['data']))
            s.evaluate(settings,"document.getElementById('actionDialog').close()");stop();start()
            check(len(s.evaluate(settings,'browserShell.getBookmarks()'))==3,'imported-bookmarks-persist-after-browser-restart')
            check(call('run',payload)['categories']['passwords']['imported']==0,'imported-passwords-persist-after-restart')
            with sqlite3.connect(source/'History') as c:c.executemany('INSERT INTO visits VALUES(1,?)',[(13344473600123000+i*1000,) for i in range(1,6001)])
            cancellation=dict(payload,bookmarks=False,passwords=False,autofill=False,tabs=False)
            s.evaluate(settings,'window.__importResult=null;browserShell.browserImport("run",'+json.dumps(cancellation)+').then(r=>window.__importResult=r);true')
            call('cancel');cancelled=wait(lambda:s.evaluate(settings,'window.__importResult'));check(cancelled['status']=='cancelled','native-worker-cancellation-through-same-settings-window')
            rejected=s.evaluate(settings,'browserShell.browserImport("run",'+json.dumps(dict(payload,target='__incognito__'))+').then(()=>false,()=>true)');check(rejected,'native-rejects-incognito-import-target')
            output.write_text(json.dumps({'ok':True,'checks':checks,'personalDataUsed':False},indent=2),encoding='utf-8')
        finally:stop();server.shutdown()
if __name__=='__main__':main()
