import ctypes,importlib.util,pathlib,tempfile,os,sys,threading,time,json,http.server,base64
root=pathlib.Path(__file__).resolve().parent
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,root/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
s=module('storage','test-cef-storage.py');access=module('access','native-menu-accessibility.py');u=ctypes.windll.user32
u.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/pixel.png':body=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aNGkAAAAASUVORK5CYII=');kind='image/png'
        else:body=b'<!doctype html><meta charset=utf-8><p id=blank>Page menu fixture</p><input id=edit value="Editable fixture"><input id=readonly readonly value="Read only fixture"><p><img id=image width=80 height=80 src=/pixel.png></p><canvas id=c width=128 height=128 hidden></canvas><video id=media muted controls width=320 height=200></video><script>const dc=c.getContext("2d");setInterval(()=>{dc.fillStyle="blue";dc.fillRect(0,0,128,128)},40);media.srcObject=c.captureStream(25);</script>';kind='text/html;charset=utf-8'
        self.send_response(200);self.send_header('Content-Type',kind);self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Fixture);threading.Thread(target=server.serve_forever,daemon=True).start();process=None
def wait(fn,timeout=20):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.05)
    raise AssertionError('Menu command result timed out')
with tempfile.TemporaryDirectory(prefix='soulu-menu-actions-',ignore_cleanup_errors=True) as profile:
    os.environ.update(LOCALAPPDATA=profile,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1',SOULU_ADBLOCK_NO_UPDATE='1',NO_PROXY='127.0.0.1,localhost')
    process=s.launch(str(pathlib.Path(sys.argv[1]).resolve()));report={}
    try:
        page=s.page_socket();target=next(t for t in s.targets() if '/ui/index.html' in t.get('url',''));shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],origin=s.BASE)
        s.navigate(page,f'http://127.0.0.1:{server.server_port}/fixture');time.sleep(.2)
        def menus():
            result=[]
            @ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
            def visit(hwnd,_):
                pid=ctypes.c_ulong();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid));name=ctypes.create_unicode_buffer(80);u.GetClassNameW(ctypes.c_void_p(hwnd),name,80)
                if pid.value==process.pid and name.value=='SouluMenuHost':result.append(hwnd)
                return True
            u.EnumWindows(visit,0);return result
        def choose(selector,text):
            box=s.evaluate(page,"(()=>{const e=document.querySelector("+json.dumps(selector)+");e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+12,y:r.y+12}})()")
            for kind in ['mouseMoved','mousePressed','mouseReleased']:
                params=dict(type=kind,**box)
                if kind!='mouseMoved':params.update(button='right',clickCount=1)
                s.sequence+=1;page.send(json.dumps(dict(id=s.sequence,method='Input.dispatchMouseEvent',params=params)))
            hwnd=wait(lambda:next(iter(menus()),None));rows=access.rows(hwnd)
            selected=next(i for i,r in enumerate(rows) if text in r['label']);assert not rows[selected]['state']&1,rows[selected]
            active=[i for i,r in enumerate(rows) if r['role']!=21 and not r['state']&1]
            u.PostMessageW(hwnd,0x100,0x24,0)
            for _ in range(active.index(selected)):u.PostMessageW(hwnd,0x100,0x28,0)
            u.PostMessageW(hwnd,0x100,0x0D,0);wait(lambda:not menus());time.sleep(.15)
        s.evaluate(page,'document.querySelector("#readonly").select()');choose('#readonly','Копировать');report['readonly_copy']='native command invoked'
        choose('#edit','Выделить всё');assert s.evaluate(page,'edit.selectionStart===0&&edit.selectionEnd===edit.value.length');report['select_all']='passed'
        choose('#image','Копировать изображение');wait(lambda:u.IsClipboardFormatAvailable(8));report['copy_image']='CF_DIB available'
        choose('#media','Воспроизвести');wait(lambda:s.evaluate(page,'!media.paused&&media.currentTime>0'));report['media_play']='passed'
        choose('#media','Пауза');assert s.evaluate(page,'media.paused');report['media_pause']='passed'
        choose('#media','Повторять');assert s.evaluate(page,'media.loop');report['media_loop']='passed'
        choose('#media','Показывать элементы управления');assert s.evaluate(page,'!media.controls');report['media_controls']='passed'
        choose('#blank','QR');wait(lambda:s.evaluate(shell,'!!document.querySelector(".soulu-qr canvas")'))
        assert s.evaluate(shell,'document.querySelector(".soulu-qr canvas").width>0');report['local_qr']='native menu produced canvas'
        print(json.dumps(report),flush=True);output=pathlib.Path(sys.argv[2]);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        page.close();shell.close();s.close_normally(process)
    finally:
        if process.poll() is None:process.kill()
        server.shutdown()
