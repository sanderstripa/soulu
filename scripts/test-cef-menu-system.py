"""Real native context menus across themes, layouts, locales and four native scales."""
import base64, ctypes, http.server, importlib.util, json, os, pathlib, subprocess, sys, tempfile, threading, time
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,pathlib.Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
s=module('storage','test-cef-storage.py');access=module('accessibility','native-menu-accessibility.py')
os.environ['NO_PROXY']='127.0.0.1,localhost';os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
u=ctypes.windll.user32
u.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
class Rect(ctypes.Structure):_fields_=[(n,ctypes.c_long) for n in ['left','top','right','bottom']]
u.GetWindowRect.argtypes=[ctypes.c_void_p,ctypes.POINTER(Rect)]
class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/pixel.png':body=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aNGkAAAAASUVORK5CYII=');kind='image/png'
        else:
            body=b'<!doctype html><meta charset=utf-8><style>body{padding:20px}img{width:80px;height:80px}p{margin:25px}</style><p id="blank">Page background</p><p><a id="link" href="/target">Native link</a></p><img id="image" src="/pixel.png"><a href="/target"><img id="linked" src="/pixel.png"></a><p id="selection">Selected native menu text</p><p><input id="editable" value="Editable fixture"></p><p><input id="readonly" readonly value="Read only fixture"></p><video id="media" controls width="200" height="100" src="/missing.webm"></video>'
            kind='text/html;charset=utf-8'
        self.send_response(200);self.send_header('Content-Type',kind);self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Fixture);threading.Thread(target=server.serve_forever,daemon=True).start()
out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True);checks=[]
def wait(fn,timeout=25):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        result=fn()
        if result:return result
        time.sleep(.05)
    raise AssertionError('Native menu state timed out')
process=None
try:
    for dpi in [96,120,144,192]:
        with tempfile.TemporaryDirectory(prefix='soulu-menu-',ignore_cleanup_errors=True) as profile:
            env=dict(os.environ,LOCALAPPDATA=profile,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_MENU_TEST_DPI=str(dpi))
            process=subprocess.Popen([str(pathlib.Path(sys.argv[1]).resolve())],env=env)
            page=s.page_socket();target=next(t for t in s.targets() if '/ui/index.html' in t.get('url',''));shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
            s.navigate(page,f'http://127.0.0.1:{server.server_port}/fixture')
            def menus():
                result=[]
                @ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
                def visit(hwnd,_):
                    pid=ctypes.c_ulong();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));name=ctypes.create_unicode_buffer(80);u.GetClassNameW(ctypes.c_void_p(hwnd),name,80)
                    if pid.value==process.pid and name.value=='SouluMenuHost':result.append(hwnd)
                    return True
                u.EnumWindows(visit,0);return result
            for language in ['ru','en']:
                for layout in ['compact','classic']:
                    for theme in ['light','dark']:
                        s.evaluate(shell,'browserShell.setSettings('+json.dumps(dict(language=language,layout=layout,theme=theme))+')');time.sleep(.1)
                        for context in ['blank','link','image','linked','selection','editable','readonly','media']:
                            box=s.evaluate(page,"""(()=>{getSelection().removeAllRanges();const e=document.getElementById(%s);e.scrollIntoView({block:'center'});if(e.id==='selection'){const r=document.createRange();r.selectNodeContents(e);getSelection().addRange(r);}const r=e.getBoundingClientRect();return {x:r.x+Math.min(r.width/2,20),y:r.y+r.height/2}})()"""%json.dumps(context))
                            for event in ['mouseMoved','mousePressed','mouseReleased']:
                                params=dict(type=event,**box)
                                if event!='mouseMoved':params.update(button='right',clickCount=1)
                                s.sequence+=1;page.send(json.dumps(dict(id=s.sequence,method='Input.dispatchMouseEvent',params=params)))
                            hwnd=wait(lambda:next(iter(menus()),None));rows=access.rows(hwnd);labels=[r['label'] for r in rows if r['label']]
                            assert labels and all(r['role_result']==0 for r in rows),rows
                            expected={'blank':['QR','Перевести' if language=='ru' else 'Translate'],'link':['ссылк' if language=='ru' else 'link'],'image':['изображени' if language=='ru' else 'image'],'linked':['ссылк' if language=='ru' else 'link','изображени' if language=='ru' else 'image'],'selection':['Копировать' if language=='ru' else 'Copy'],'editable':['Вставить' if language=='ru' else 'Paste'],'readonly':['Копировать' if language=='ru' else 'Copy'],'media':['Повторять' if language=='ru' else 'Loop']}[context]
                            assert all(any(text in label for label in labels) for text in expected),(context,labels)
                            bounds=Rect();u.GetWindowRect(hwnd,ctypes.byref(bounds));assert bounds.right>bounds.left and bounds.bottom>bounds.top
                            u.PostMessageW(hwnd,0x100,0x24,0);u.PostMessageW(hwnd,0x100,0x23,0);u.PostMessageW(hwnd,0x100,0x26,0);u.PostMessageW(hwnd,0x100,0x28,0)
                            if context in ['blank','linked']:
                                from PIL import ImageGrab
                                time.sleep(.08);ImageGrab.grab(bbox=(bounds.left,bounds.top,bounds.right,bounds.bottom),all_screens=True).save(out/f'{dpi}-{language}-{layout}-{theme}-{context}.png')
                            u.PostMessageW(hwnd,0x100,0x1B,0);wait(lambda:not menus())
                            checks.append(dict(dpi=dpi,language=language,layout=layout,theme=theme,context=context,labels=labels,width=bounds.right-bounds.left,height=bounds.bottom-bounds.top))
            # Exercise recursive models and disabled-item skipping at a screen edge.
            model=[dict(command=1,label='Disabled',enabled=False),dict(type='submenu',label='R&D submenu',children=[dict(command=7,label='Nested action')]),dict(type='separator'),dict(type='check',command=4,label='Checked',checked=True),dict(type='radio',command=5,label='Radio',checked=True)]
            s.evaluate(shell,'window.nativeMenuResult=null;browserShell.showMenu('+json.dumps(model)+',10000,10000).then(v=>nativeMenuResult=v);void 0')
            root_menu=wait(lambda:next(iter(menus()),None));rows=access.rows(root_menu)
            assert rows[0]['state']&1 and rows[1]['label']=='R&D submenu',rows
            assert rows[3]['state']&16 and rows[4]['state']&16,rows
            u.PostMessageW(root_menu,0x100,0x24,0);u.PostMessageW(root_menu,0x100,0x27,0)
            child=wait(lambda:next((h for h in menus() if h!=root_menu),None))
            assert any(r['label']=='Nested action' for r in access.rows(child))
            u.PostMessageW(child,0x100,0x0D,0);wait(lambda:not menus())
            assert wait(lambda:s.evaluate(shell,'nativeMenuResult'))==7
            checks.append(dict(dpi=dpi,context='recursive',disabled_skipping=True,checked_radio=True,edge_placement=True,command=7))
            page.close();shell.close();s.close_normally(process);process=None
    (out/'menu-evidence.json').write_text(json.dumps(dict(passed=True,scale_mode='native layout/font DPI override in dedicated test process',checks=checks),ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PASS: {len(checks)} native context/locale/layout/theme/scale combinations; accessibility labels/roles, keyboard dismissal and screenshots',flush=True)
finally:
    if process and process.poll() is None:process.kill()
    server.shutdown()
