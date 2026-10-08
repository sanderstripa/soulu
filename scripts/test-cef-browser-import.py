"""Real CEF import bridge, synthetic Windows profiles and restart persistence."""
from contextlib import closing
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
    with closing(sqlite3.connect(path,isolation_level=None)) as c:c.executescript(sql)
def digest(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def main():
    exe=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    s.DEBUG_PORT=s.free_port();s.BASE=f'http://127.0.0.1:{s.DEBUG_PORT}'
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
        with closing(sqlite3.connect(source/'Login Data',isolation_level=None)) as c:c.execute('INSERT INTO logins VALUES(?,?,?,0)',(url,'fixture',ctypes.string_at(sealed.data,sealed.size)))
        ctypes.windll.kernel32.LocalFree(sealed.data)
        nav=struct.pack('<iii',10,0,len(url))+url.encode();nav+=b'\0'*(-len(nav)%4);nav+=struct.pack('<iii',0,0,0)
        command=lambda id,p:struct.pack('<HB',len(p)+1,id)+p
        session=b'SNSS'+struct.pack('<i',3)+command(0,struct.pack('<ii',1,10))+command(9,struct.pack('<ii',1,0))+command(6,struct.pack('<i',len(nav))+nav)+command(7,struct.pack('<ii',10,0))+command(255,b'')
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
            process=subprocess.Popen([str(exe),'--no-proxy-server'],env=env);shell=socket('/ui/index.html');wait(lambda:s.evaluate(shell,"typeof window.browserShell?.browserImport==='function'"))
            s.evaluate(shell,'browserShell.openSettingsWindow()');settings=socket('/ui/settings.html');wait(lambda:s.evaluate(settings,"document.body?.classList.contains('ready')"))
        def stop():
            nonlocal process
            for ws in connections:
                try:ws.close()
                except Exception:pass
            connections.clear()
            if process:
                if process.poll() is None:s.close_normally(process)
                process=None
        def call(action,value=None):return s.evaluate(settings,'browserShell.browserImport('+json.dumps(action)+(','+json.dumps(value) if value is not None else '')+')')
        payload={'source':'Chrome:Default','target':'personal','bookmarks':True,'history':True,'passwords':True,'consent':True,'autofill':True,'tabs':True}
        try:
            start();catalog=call('catalog');check(any(p['id']=='Chrome:Default' for b in catalog for p in b['profiles']),'native-discovery-and-profile-identity')
            caps=call('capabilities',{'source':'Chrome:Default'});print('Synthetic source capabilities:',caps,flush=True);check(all(caps[k]['status']=='available' for k in ('bookmarks','history','passwords','autofill','tabs')),'native-five-category-capabilities')
            check(digest(source)==before,'capability-probes-do-not-modify-source')
            kernel=ctypes.windll.kernel32
            kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];kernel.CreateFileW.restype=ctypes.c_void_p
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            locked=kernel.CreateFileW(str(source/'History'),0x80000000,0,None,3,0,None)
            check(locked not in (None,ctypes.c_void_p(-1).value),'fixture-exclusive-source-lock')
            try:check(call('capabilities',{'source':'Chrome:Default'})['history']['status']=='blocked','locked-source-has-actionable-unavailable-category')
            finally:kernel.CloseHandle(locked)
            profile=call('createProfile',{'name':'Import target fixture'});other=profile['id'];check(s.evaluate(shell,'browserShell.getState()')['activeProfileId']=='personal','inline-profile-creation-does-not-switch-profile')
            result=call('run',payload);check(result['status']=='ok' and all(result['categories'][k]['imported']>0 for k in ('bookmarks','history','passwords','autofill','tabs')),'all-five-categories-import-through-native-settings-bridge')
            again=call('run',payload);print('Repeat synthetic import:',again,flush=True);check(all(r.get('imported',0)==0 for r in again['categories'].values()),'repeat-import-deduplicates-all-categories')
            data=local/'Soulu/User Data';personal=data/'Profiles/personal';destination=data/'Profiles'/other
            check(not (destination/'soulu-autofill.json').exists() and not (destination/'soulu-passwords.json').exists(),'existing-target-profile-isolation')
            check(b'fixture@example.test' not in (personal/'soulu-autofill.json').read_bytes() and b'synthetic-import-only' not in (personal/'soulu-passwords.json').read_bytes(),'native-target-stores-encrypted')
            marks=s.evaluate(settings,'browserShell.getBookmarks()');check(any(r.get('parentId',0)>0 for r in marks) and len(marks)==3,'nested-bookmarks-visible-in-existing-bookmark-backend')
            check(digest(source)==before,'native-import-does-not-change-source-or-create-sidecars')
            original_web=(source/'Web Data').read_bytes();form_file=personal/'soulu-autofill.json';form_backup=form_file.with_suffix('.backup');encrypted_before=form_file.read_bytes()
            with closing(sqlite3.connect(source/'Web Data',isolation_level=None)) as c:c.execute("INSERT INTO autofill VALUES('email','second@example.test')")
            form_file.rename(form_backup);form_file.mkdir()
            try:
                failure=call('run',dict(payload,bookmarks=False,history=False,passwords=False,tabs=False))
                check(failure['categories']['autofill']['status']=='error' and failure['categories']['autofill']['imported']==0,'target-write-failure-is-reported-without-success-count')
                check(form_backup.read_bytes()==encrypted_before,'target-write-failure-preserves-existing-autofill')
            finally:
                form_file.rmdir();form_backup.rename(form_file);(source/'Web Data').write_bytes(original_web)
            # Drive the renderer's context menu and the real native saved-value menu.
            menu_spec=importlib.util.spec_from_file_location('access',Path(__file__).with_name('native-menu-accessibility.py'))
            access=importlib.util.module_from_spec(menu_spec);menu_spec.loader.exec_module(access)
            user=ctypes.windll.user32
            def menu_window():
                found=[]
                @ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
                def collect(hwnd,_):
                    pid=ctypes.c_ulong();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));name=ctypes.create_unicode_buffer(80);user.GetClassNameW(hwnd,name,80)
                    if pid.value==process.pid and name.value=='SouluMenuHost' and user.IsWindowVisible(hwnd):found.append(hwnd)
                    return True
                user.EnumWindows(collect,0);return found[0] if found else None
            tab=next(t for t in s.evaluate(shell,'browserShell.getState()')['tabs'] if t.get('url')==url);s.evaluate(shell,'browserShell.switchTab('+str(tab['id'])+')');content=socket('/fixture');s.command(content,'Page.bringToFront')
            def fill(selector,expected,label=None):
                box=s.evaluate(content,"(()=>{const e=document.querySelector("+json.dumps(selector)+");const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                for event in ('mouseMoved','mousePressed','mouseReleased'):
                    params=dict(type=event,**box)
                    if event!='mouseMoved':params.update(button='right',clickCount=1)
                    s.sequence+=1;content.send(json.dumps({'id':s.sequence,'method':'Input.dispatchMouseEvent','params':params}))
                hwnd=wait(menu_window);rows=access.rows(hwnd);item=next(r for r in rows if 'Soulu' in r['label'])
                # Confirm the command is exposed by the real native menu.
                assert item['label']
                # Host coordinates are screen-relative in accessibility, use keyboard
                # End because the Fill from Soulu command is the final editable row.
                user.PostMessageW(hwnd,0x100,0x23,0);user.PostMessageW(hwnd,0x100,0x0D,0)
                def choices_ready():
                    hwnd=menu_window()
                    if not hwnd:return False
                    try:return any(r['label']==(label or expected) for r in access.rows(hwnd))
                    except AssertionError:return False # Menu replacement can invalidate MSAA briefly.
                wait(choices_ready)
                hwnd=menu_window();user.PostMessageW(hwnd,0x100,0x24,0);user.PostMessageW(hwnd,0x100,0x0D,0)
                wait(lambda:s.evaluate(content,'document.querySelector('+json.dumps(selector)+').value')==expected)
            fill('input[name=email]','fixture@example.test');check(True,'native-imported-autofill-fills-page-field')
            fill('input[type=password]','synthetic-import-only','fixture');check(True,'native-imported-password-fills-same-origin-page-field')
            s.evaluate(settings,'souluBrowserImport.open()');wait(lambda:s.evaluate(settings,"!!document.querySelector('dialog[open] #importFrom')"));check(s.evaluate(settings,"document.querySelectorAll('dialog[open]').length")==1,'real-CEF-compact-import-dialog')
            screenshot=s.command(settings,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False});(output.parent/'browser-import-native-window.png').write_bytes(base64.b64decode(screenshot['data']))
            s.evaluate(settings,"document.getElementById('actionDialog').close()");stop();start()
            check(len(s.evaluate(settings,'browserShell.getBookmarks()'))==3,'imported-bookmarks-persist-after-browser-restart')
            check(call('run',payload)['categories']['passwords']['imported']==0,'imported-passwords-persist-after-restart')
            with closing(sqlite3.connect(source/'History',isolation_level=None)) as c:c.executemany('INSERT INTO visits VALUES(1,?)',[(13344473600123000+i*1000,) for i in range(1,6001)])
            cancellation=dict(payload,bookmarks=False,passwords=False,autofill=False,tabs=False)
            s.evaluate(settings,'window.__importResult=null;browserShell.browserImport("run",'+json.dumps(cancellation)+').then(r=>window.__importResult=r);true')
            call('cancel');cancelled=wait(lambda:s.evaluate(settings,'window.__importResult'));check(cancelled['status']=='cancelled','native-worker-cancellation-through-same-settings-window')
            rejected=s.evaluate(settings,'browserShell.browserImport("run",'+json.dumps(dict(payload,target='__incognito__'))+').then(()=>false,()=>true)');check(rejected,'native-rejects-incognito-import-target')
            output.write_text(json.dumps({'ok':True,'checks':checks,'personalDataUsed':False},indent=2),encoding='utf-8')
        finally:stop();server.shutdown()
if __name__=='__main__':main()
