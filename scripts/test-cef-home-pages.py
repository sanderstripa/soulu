"""Real native CEF checks for page intents, offline home, persistence and privacy."""
import base64
import http.server
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
checks=[]
os.environ["NO_PROXY"]="localhost,127.0.0.1,::1"


def wait(fn,timeout=30):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        result=fn()
        if result:return result
        time.sleep(.1)
    raise AssertionError('Home state timeout')

def check(value,name):
    assert value,name
    checks.append(name)
    print('PASS:',name,flush=True)

class Site(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'<!doctype html><title>Page intent fixture</title><a href="/two" target="_blank">Open</a>'
        self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass

def socket(target):return s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)

def main():
    exe=os.path.abspath(sys.argv[1]);output=Path(sys.argv[2]) if len(sys.argv)>2 else None
    server=http.server.ThreadingHTTPServer(('127.0.0.1',s.free_port()),Site)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    with tempfile.TemporaryDirectory(prefix='soulu-home-',ignore_cleanup_errors=True) as root:
        os.environ['LOCALAPPDATA']=root
        env=dict(os.environ,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT))
        process=None;shell=None;connections=[]
        profile=Path(root)/'Soulu'/'User Data'/'Profiles'/'personal'
        def start():
            nonlocal process,shell
            process=subprocess.Popen([exe,'--no-proxy-server'],env=env)
            shell=socket(wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None)))
            connections.append(shell)
            wait(lambda:s.evaluate(shell,"typeof window.browserShell?.getState==='function'"))
            wait(lambda:state().get('tabs'))
        def state():return s.evaluate(shell,'browserShell.getState()')
        def call(method,payload=None):return s.evaluate(shell,'browserShell.'+method+'('+('' if payload is None else json.dumps(payload))+')')
        def page(fragment='/ui/home.html'):
            diagnostics=[]
            def find():
                for target in s.targets():
                    if fragment not in target.get('url',''):continue
                    ws=socket(target)
                    try:
                        # The target URL changes before the new document/context is ready.
                        # Do not await a bridge promise from the departing context:
                        # navigation cancels that query without settling its JS promise.
                        if not s.evaluate(ws,"document.readyState==='complete'"+ (" && typeof window.souluHomeApply==='function'" if fragment=='/ui/home.html' else '')):
                            ws.close();continue
                        if fragment=='/ui/home.html' and home(ws,'home.get')['tabId']!=state()['activeTabId']:
                            ws.close();continue
                        connections.append(ws);return ws
                    except Exception as error:
                        diagnostics.append(str(error)[:500]);ws.close();continue
                return None
            try:return wait(find)
            except AssertionError:
                print('PAGE TIMEOUT DIAGNOSTICS:',json.dumps({'state':state(),'targets':[{'url':t.get('url'),'type':t.get('type')} for t in s.targets()],'errors':diagnostics[-5:]},ensure_ascii=False),flush=True)
                raise
        def home(ws,action,payload=None):
            if action=='home.navigate':
                s.command(ws,'Runtime.evaluate',{'expression':"cefQuery({request:"+json.dumps(json.dumps({'action':action,'payload':payload}))+",onSuccess:()=>{},onFailure:()=>{}})",'awaitPromise':False})
                return None
            return s.evaluate(ws,"new Promise((resolve,reject)=>cefQuery({request:"+json.dumps(json.dumps({'action':action,'payload':payload}))+",onSuccess:v=>resolve(v?JSON.parse(v):null),onFailure:(_,m)=>reject(Error(m))}))")
        def stop():
            nonlocal process
            for ws in connections:
                try:ws.close()
                except Exception:pass
            connections.clear();s.close_normally(process);process=None
        def current_url():
            data=state();return next(t['url'] for t in data['tabs'] if t['active'])
        def one_tab():
            data=state();keep=data['activeTabId']
            for tab in data['tabs']:
                if tab['id']!=keep:call('closeTab',tab['id'])
            wait(lambda:len(state()['tabs'])==1)
        try:
            start();h=page()
            check(current_url()=='soulu://home' and len(state()['tabs'])==1,'Fresh startup is one offline local Soulu page')
            for layout in ('compact','classic'):
                call('setSettings',{'layout':layout})
                selector='#compactAddress' if layout=='compact' else '#classicAddress'
                wait(lambda:s.evaluate(shell,'document.body.dataset.layout')==layout)
                check(s.evaluate(shell,'document.querySelector('+json.dumps(selector)+').value')=='','Home omnibox is empty: '+layout)
                check(s.evaluate(shell,'document.querySelector('+json.dumps(selector)+').placeholder')=='','Home omnibox has no hint: '+layout)
                s.evaluate(shell,'document.querySelector('+json.dumps(selector)+').focus();document.querySelector('+json.dumps(selector)+').blur()')
                time.sleep(.2)
                check(s.evaluate(shell,'document.querySelector('+json.dumps(selector)+').value')=='','Home blur keeps the address empty: '+layout)
            call('setSettings',{'layout':'compact'})
            s.evaluate(h,"document.querySelector('#query').focus()")
            check(s.evaluate(h,"document.querySelector('#logo').getAttribute('src')==='browser-icon.png' && typeof window.souluHomeApply==='function'"),'Bundled logo and internal shell rendered')
            wait(lambda:s.evaluate(h,"document.activeElement?.id==='query'"))
            check(home(h,'home.get')['homeProvider']=='google','Fresh Home provider is Google')
            check(home(h,'home.get')['favorites']==[],'Fresh favorites are not seeded with marketing links')
            check(s.evaluate(h,"!document.querySelector('#customize,#shortcuts,#add,#editor,dialog')"),'Home has no editor, customization or dashboard blocks')
            check(s.evaluate(h,"performance.getEntriesByType('resource').every(r=>r.name.startsWith('file:'))"),'Shell assets have no external dependencies')
            s.command(h,'Network.enable');s.command(h,'Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':0,'uploadThroughput':0})
            s.command(h,'Page.reload');wait(lambda:s.evaluate(h,"typeof window.souluHomeApply==='function'"))
            check(home(h,'home.weather')['status']=='unavailable','Unpermitted location fails calmly without blocking Home')
            for panel in ('provider','weather','favorites'):
                s.evaluate(h,"document.querySelector('#"+panel+"Toggle').click()")
                check(s.evaluate(h,"!document.querySelector('#"+panel+"Panel').hidden"),panel+' panel opens')
                s.command(h,'Input.dispatchKeyEvent',{'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27})
                check(s.evaluate(h,"document.querySelector('#"+panel+"Panel').hidden && document.activeElement.id==='"+panel+"Toggle'"),panel+' Escape restores trigger focus')
            s.command(h,'Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
            check(s.evaluate(h,"new Promise(resolve=>cefQuery({request:JSON.stringify({action:'home.set',payload:{homeShortcuts:[]}}),onSuccess:()=>resolve(false),onFailure:()=>resolve(true)}))"),'Home bridge cannot edit favorites or settings')
            check(s.evaluate(h,"new Promise(resolve=>cefQuery({request:JSON.stringify({action:'browser.passwords.get'}),onSuccess:()=>resolve(false),onFailure:()=>resolve(true)}))"),'Home cannot invoke privileged shell actions')
            check(s.evaluate(h,"new Promise(resolve=>cefQuery({request:JSON.stringify({action:'home.navigate',payload:'javascript://example.com/alert(1)'}),onSuccess:()=>resolve(false),onFailure:()=>resolve(true)}))"),'Executable navigation is rejected')
            rows=[{'id':7001,'type':'url','title':'<img src=x onerror=alert(1)>','url':origin+'/one','favicon':'','parentId':0,'order':0},{'id':7002,'type':'url','title':'Second','url':origin+'/two','favicon':'','parentId':0,'order':1}]
            call('replaceBookmarks',rows);call('setSettings',{'homeFavoriteIds':[7002,7001]})
            wait(lambda:len(home(h,'home.get')['favorites'])==2)
            check([x['id'] for x in home(h,'home.get')['favorites']]==[7002,7001],'Favorites reference real ordered bookmark IDs')
            wait(lambda:s.evaluate(h,"document.querySelectorAll('.favorite').length===2"))
            check(s.evaluate(h,"!document.querySelector('#favoritesGrid [onerror]') && document.querySelectorAll('.favorite span:last-child')[1].textContent.includes('<img')"),'Bookmark text cannot inject HTML')
            s.evaluate(h,"document.querySelector('#favoritesToggle').click();document.querySelector('.favorite').click()")
            wait(lambda:current_url()==origin+'/two');check(len(state()['tabs'])==1,'Favorite opens inside current Soulu tab')
            call('home');h=page()
            s.evaluate(h,"document.querySelector('#favoritesToggle').click()")
            s.command(h,'Input.dispatchKeyEvent',{'type':'keyDown','key':' ','code':'Space','windowsVirtualKeyCode':32})
            wait(lambda:current_url()==origin+'/two');check(len(state()['tabs'])==1,'Space activates the focused real favorite inside Soulu')
            call('home');h=page()
            for theme in ('light','dark','system'):
                call('setSettings',{'theme':theme});wait(lambda:home(h,'home.get')['theme']==theme)
                check(s.evaluate(h,"['light','dark'].includes(document.body.dataset.theme)"),'Resolved '+theme+' theme')
            s.evaluate(h,"document.querySelector('#query').focus()")
            s.command(h,'Input.dispatchKeyEvent',{'type':'keyDown','key':'Tab','code':'Tab','windowsVirtualKeyCode':9})
            check(s.evaluate(h,"document.activeElement.id==='voice'"),'Tab reaches microphone')
            s.command(h,'Input.dispatchKeyEvent',{'type':'keyDown','key':'Tab','code':'Tab','windowsVirtualKeyCode':9,'modifiers':8})
            check(s.evaluate(h,"document.activeElement.id==='query'"),'Shift+Tab returns to input')
            for provider in ('google','perplexity'):
                home(h,'home.set',{'homeProvider':provider});call('setSettings',{'searchEngine':'bing'})
                query='погода екатеринбург';home(h,'home.navigate',query)
                from urllib.parse import parse_qs,urlparse
                host='www.google.com' if provider=='google' else 'www.perplexity.ai'
                # Perplexity currently redirects its official OpenSearch URL to /search/new.
                def routed():
                    parsed=urlparse(current_url())
                    return parsed.scheme=='https' and parsed.netloc==host and parsed.path in ('/search','/search/new') and parse_qs(parsed.query).get('q')==[query]
                wait(routed)
                check(True,provider+' native query encoding and search route')
                check(call('getSettings')['searchEngine']=='bing','Home choice preserves omnibox engine')
                call('home');h=page()
            for value in ('openai.com','https://github.com',origin+'/enter'):
                home(h,'home.navigate',value);wait(lambda:current_url().startswith(value if value.startswith('http') else 'https://'+value))
                check(True,'URL takes precedence over provider: '+value);call('home');h=page()
            call('setSettings',{'startupMode':'custom','startupUrl':origin+'/startup','newTabMode':'blank','homeMode':'soulu'})
            s.evaluate(shell,"document.querySelector('#compactNewTabButton').click()");wait(lambda:current_url()=='');check(True,'Plus button uses blank New Tab independently of custom Startup')
            call('home');wait(lambda:current_url()=='soulu://home');check(True,'Home Soulu is independent of New Tab blank')
            call('setSettings',{'newTabMode':'custom','newTabUrl':origin+'/new','homeMode':'custom','homeUrl':origin+'/home'})
            call('newTab');wait(lambda:current_url()==origin+'/new');call('home');wait(lambda:current_url()==origin+'/home')
            check(call('getSettings')['startupUrl']==origin+'/startup','Three custom intent URLs remain independent')
            check(s.evaluate(shell,"browserShell.setSettings({newTabUrl:'file:///C:/Windows/win.ini'}).then(()=>false,()=>true)"),'Custom file URL is rejected')
            check(s.evaluate(shell,"browserShell.setSettings({startupUrl:'javascript:alert(1)'}).then(()=>false,()=>true)"),'Invalid startup URL is rejected')
            call('setSettings',{'newTabMode':'soulu','homeMode':'soulu','startupMode':'soulu'})
            before=len(state()['tabs']);s.evaluate(shell,"Promise.all(Array.from({length:8},()=>browserShell.newTab()))")
            wait(lambda:len(state()['tabs'])==before+8);check(True,'Eight rapid new tabs produce exactly eight tabs')
            h=page();wait(lambda:s.evaluate(h,"document.activeElement?.id==='query'"));check(True,'New tab focuses Home input')
            s.command(h,'Input.insertText',{'text':'openai.com'});check(s.evaluate(h,"document.querySelector('#query').value==='openai.com'"),'Immediate typing reaches Home input')
            h=page();s.evaluate(shell,"new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'browser.test.pageShortcut',payload:84}),onSuccess:resolve,onFailure:reject}))")
            wait(lambda:len(state()['tabs'])==before+9);check(True,'Native Ctrl+T creates one foreground tab')
            s.evaluate(shell,"new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'browser.test.pageShortcut',payload:76}),onSuccess:resolve,onFailure:reject}))")
            wait(lambda:s.evaluate(shell,"['compactAddress','classicAddress'].includes(document.activeElement?.id)"));check(True,'Native Ctrl+L focuses omnibox')
            call('setSettings',{'homeMode':'blank'})
            s.evaluate(shell,"new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'browser.test.pageShortcut',payload:36}),onSuccess:resolve,onFailure:reject}))")
            wait(lambda:current_url()=='');check(True,'Native Alt+Home opens configured blank Home')
            call('setSettings',{'homeMode':'soulu'})
            ids=[t['id'] for t in state()['tabs']]
            s.evaluate(shell,'Promise.all('+json.dumps(ids)+'.map(id=>browserShell.closeTab(id)))')
            wait(lambda:len(state()['tabs'])==1)
            check(True,'Rapid closing all tabs creates one replacement without a loop')
            one_tab();call('setSettings',{'openStartPageAfterLastTab':True,'startupMode':'custom','startupUrl':origin+'/startup','newTabMode':'soulu'})
            call('closeTab',state()['activeTabId']);wait(lambda:len(state()['tabs'])==1 and current_url()==origin+'/startup')
            check(True,'Last-tab ON uses Startup custom and creates one tab')
            call('setSettings',{'startupMode':'soulu'});call('closeTab',state()['activeTabId']);wait(lambda:len(state()['tabs'])==1 and current_url()=='soulu://home')
            check(True,'Last-tab ON uses Startup Soulu')
            call('setSettings',{'openStartPageAfterLastTab':False});call('closeTab',state()['activeTabId']);wait(lambda:len(state()['tabs'])==1 and current_url()=='')
            check(True,'Last-tab OFF retains legacy blank replacement')
            call('home');h=page();marker='private-home-marker'
            call('newIncognito');wait(lambda:state()['incognito']);h=page();
            # Select the private target by reading its scoped state, not global active state.
            for target in s.targets():
                if '/ui/home.html' not in target.get('url',''):continue
                candidate=socket(target);connections.append(candidate)
                if home(candidate,'home.get')['incognito']:h=candidate;break
            home(h,'home.set',{'homeProvider':'google'})
            check(home(h,'home.get')['incognito'],'Incognito home uses temporary state')
            call('closeTab',state()['activeTabId']);wait(lambda:not state()['incognito'])
            check(json.loads((profile/'soulu-settings.json').read_text(encoding='utf-8'))['homeProvider']=='perplexity','Incognito provider never writes normal settings')
            call('createProfile','Home B');b=state()['activeProfileId'];h=page()
            for target in s.targets():
                if '/ui/home.html' in target.get('url',''):
                    candidate=socket(target);connections.append(candidate)
                    if home(candidate,'home.get')['homeProvider']=='google':h=candidate;break
            check(home(h,'home.get')['favorites']==[] and home(h,'home.get')['homeProvider']=='google','Profile B isolates Favorites and provider')
            home(h,'home.set',{'homeProvider':'perplexity'})
            call('setSettings',{'startupMode':'blank','newTabMode':'blank','homeMode':'blank'})
            call('switchProfile','personal');call('home');h=page()
            check(call('getSettings')['newTabMode']=='soulu','Page modes are isolated by profile')
            # Save ordered ordinary URLs and an active index, excluding every incognito tab.
            one_tab();call('navigate',origin+'/first');wait(lambda:current_url()==origin+'/first')
            call('newTab');call('navigate',origin+'/second');wait(lambda:current_url()==origin+'/second')
            normal=state()['tabs'];call('setSettings',{'startupMode':'continue'})
            call('newIncognito');wait(lambda:state()['incognito']);call('navigate',origin+'/private-session')
            stop();saved=json.loads((profile/'soulu-session.json').read_text(encoding='utf-8'))
            check(saved['tabs']==[origin+'/first',origin+'/second'],'Saved session order excludes incognito')
            start();wait(lambda:len(state()['tabs'])==2)
            check([t['url'] for t in state()['tabs']]==saved['tabs'] and current_url()==origin+'/second','Startup restores ordered session without an extra home tab')
            check(call('getSettings')['homeFavoriteIds']==[7002,7001] and call('getSettings')['homeProvider']=='perplexity','Favorites and provider persist after restart')
            call('newIncognito');wait(lambda:state()['incognito']);call('closeTab',state()['activeTabId']);wait(lambda:not state()['incognito'])
            selected=current_url();stop();start()
            check(current_url()==selected,'Restore retains actual normal selection after incognito closes')
            stop()
            # Explicit startup modes are tested at full launch, rather than as Ctrl+T.
            for mode,expected in [('blank',''),('custom',origin+'/startup'),('soulu','soulu://home')]:
                data=json.loads((profile/'soulu-settings.json').read_text(encoding='utf-8'));data.update(startupMode=mode,startupUrl=origin+'/startup')
                (profile/'soulu-settings.json').write_text(json.dumps(data),encoding='utf-8')
                start();wait(lambda:current_url()==expected);check(len(state()['tabs'])==1,'Full launch startup '+mode);stop()
            report={'passed':True,'checks':checks,'count':len(checks),'weather':'unpermitted location gracefully unavailable','session':'ordered URL restore after normal shutdown'}
            if output:output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report,ensure_ascii=False))
        finally:
            if process and process.poll() is None:
                try:stop()
                except Exception:process.terminate();process.wait(timeout=20)
            server.shutdown()

if __name__=='__main__':main()
