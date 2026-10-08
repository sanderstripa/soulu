"""Exercise Settings through real CEF controls and canonical disk stores."""
import base64
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import winreg

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
checks=[]

def wait(fn,timeout=30):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.1)
    raise AssertionError('Settings state timeout')

def check(value,name):
    assert value,name
    checks.append(name);print('PASS:',name,flush=True)

def main():
    exe=str(Path(sys.argv[1]).resolve())
    output=Path(sys.argv[2]) if len(sys.argv)>2 else Path('settings-evidence.json')
    evidence=output.parent/'settings-visuals';evidence.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='soulu-settings-',ignore_cleanup_errors=True) as temp:
        root=Path(temp);local=root/'local';roaming=root/'roaming';local.mkdir();roaming.mkdir()
        data=local/'Soulu'/'User Data';profile=data/'Profiles'/'personal';profile.mkdir(parents=True)
        legacy={'theme':'dark','layout':'classic','mattePanel':False,'matteDefaultV15':True,
          'language':'ru','showBack':False,'showNewTab':False,'showDownloads':True,
          'vpnToolbarVisible':False,'addressPosition':'left','downloadsMode':'always',
          'searchEngine':'bing','startPageMode':'blank','startPageUrl':'',
          'newTabMode':'soulu','newTabUrl':'','homeMode':'custom','homeUrl':'https://example.com/home',
          'bookmarksBarMode':'never','bookmarksIconsOnly':True,'downloadPath':str(root),
          'askDownloadLocation':False,'homeShowSearch':False,'homeShowShortcuts':True,
          'homeShortcuts':[{'name':'Legacy shortcut','url':'https://example.com/legacy'}]}
        vpn={'protocol':'vless','link':'','address':'','region':'legacy marker','lastProfileId':''}
        (data/'settings.json').write_text(json.dumps({'settings':legacy,'vpn':vpn}),encoding='utf-8')
        reader={'theme':'sepia','font':'sans','size':21,'width':2,'spacing':0,'images':False}
        (profile/'soulu-reader.json').write_text(json.dumps(reader),encoding='utf-8')
        rules={'defaults':{'camera':2,'microphone':1,'geolocation':1,'notifications':2,'sound':1,'popups':1,'downloads':0},
          'sites':{'legacy.example':{'camera':0}},'blocking':{'enabled':True,'sites':{'ads.example':False}}}
        (profile/'soulu-site-rules.json').write_text(json.dumps(rules),encoding='utf-8')
        env=dict(os.environ,LOCALAPPDATA=str(local),APPDATA=str(roaming),SOULU_UI_TEST_PORT=str(s.DEBUG_PORT))
        process=None;connections=[];shell=None;settings=None
        def socket(fragment):
            def find():
                for target in s.targets():
                    if fragment not in target.get('url',''):continue
                    ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
                    if fragment=='/ui/settings.html':
                        try:
                            active=s.evaluate(shell,"window.browserShell.getState()")
                            if s.evaluate(ws,"window.souluSettings?.persisted?.profile")!=active["activeProfileId"]:
                                ws.close();continue
                        except Exception:ws.close();continue
                    connections.append(ws);return ws
                return None
            return wait(find)
        def evaluate(expression):return s.evaluate(settings,expression)
        def shellcall(method,value=None):return s.evaluate(shell,'browserShell.'+method+'('+('' if value is None else json.dumps(value))+')')
        def start():
            nonlocal process,shell,settings
            process=subprocess.Popen([exe,'--no-proxy-server'],env=env)
            shell=socket('/ui/index.html');wait(lambda:s.evaluate(shell,"typeof window.browserShell?.getState==='function'"))
            shellcall('openSettingsWindow');settings=socket('/ui/settings.html')
            wait(lambda:evaluate("document.body.classList.contains('ready')"))
        def stop():
            nonlocal process
            for ws in connections:
                try:ws.close()
                except Exception:pass
            connections.clear();s.close_normally(process);process=None
        def section(name):evaluate('souluSettings.openSection('+json.dumps(name)+')')
        def change(selector,value):
            evaluate("(()=>{const n=document.querySelector("+json.dumps(selector)+");if(!n)throw Error('Missing control');n.value="+json.dumps(value)+";n.dispatchEvent(new Event('input',{bubbles:true}));n.dispatchEvent(new Event('change',{bubbles:true}));return true;})()")
        def click(selector):evaluate('document.querySelector('+json.dumps(selector)+').click()')
        def saved():return json.loads((profile/'soulu-settings.json').read_text(encoding='utf-8'))
        def capture(name):
            result=s.command(settings,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})
            (evidence/(name+'.png')).write_bytes(base64.b64decode(result['data']))
        try:
            start()
            check(evaluate("!document.querySelector('#applySettings') && !document.querySelector('#cancelSettings') && !document.querySelector('#closeDialog')"),'No global Apply, Cancel or dirty-close dialog')
            check(evaluate('souluSettings.current.settings.startupMode')=='blank','Legacy startup migration survives redesign')
            check(evaluate('souluSettings.current.reader.size')==21,'Reader migration preserves canonical values')
            capture('cards-dark')
            sections=['general','interface','startup','search','privacy','vpn','reading','profiles','about']
            check(evaluate("[...document.querySelectorAll('#homeCards [data-section]')].map(n=>n.dataset.section)")==sections,'Exactly nine canonical Settings sections')
            for name in sections:
                section(name)
                check(evaluate("document.querySelector('.nav-item.active').dataset.section==="+json.dumps(name)),'Section navigation: '+name)
            section('');check(evaluate("document.querySelector('aside').hidden"),'Home hides section navigation')
            for query in ['камера','микрофон','новая вкладка','домашняя','пароль','Reader','закладки','загрузки','CEF']:
                change('#settingsSearch',query)
                check(evaluate("document.querySelectorAll('.result').length>0"),'Search indexes '+query)
            change('#settingsSearch','zz-no-such-setting');check(evaluate("document.querySelectorAll('.result').length===0"),'Unknown search has no false result')
            section('interface');click('[name="settings-theme"][value="light"]');evaluate('souluSettings.flush()')
            check(saved()['theme']=='light' and s.evaluate(shell,"document.body.dataset.theme==='light'"),'Theme applies and persists immediately')
            section('startup');change('#startupMode','custom');change('#startupUrl','javascript:alert(1)');evaluate('souluSettings.flush()')
            check(saved()['startupMode']=='blank' and evaluate("document.querySelector('#dataMessage').textContent.length>0"),'Invalid URL reports error and retains disk values')
            change('#startupMode','custom');change('#startupUrl','https://example.com/start');evaluate('souluSettings.flush()')
            change('#newTabMode','blank');evaluate('souluSettings.flush()')
            change('#homeUrl','https://example.com/home2');evaluate('souluSettings.flush()')
            check(saved()['startupUrl']=='https://example.com/start' and saved()['newTabMode']=='blank' and saved()['homeUrl']=='https://example.com/home2','Startup/New Tab/Home save independently')
            section('search');change('#searchEngine','google');evaluate('souluSettings.flush()')
            check(saved()['searchEngine']=='google','Select saves without global confirmation')
            section('privacy');change('#permissions-camera','1');evaluate('souluSettings.flush()')
            check(json.loads((profile/'soulu-site-rules.json').read_text())['defaults']['camera']==1,'Permission persists to canonical store')
            section('reading');change('#reader-theme','dark');evaluate('souluSettings.flush()')
            check(json.loads((profile/'soulu-reader.json').read_text())['theme']=='dark','Reader persists to independent store')
            rulesFile=profile/'soulu-site-rules.json';backup=profile/'rules.backup';rulesFile.rename(backup);rulesFile.mkdir()
            section('privacy');change('#permissions-microphone','2');evaluate('souluSettings.flush()')
            check(evaluate("document.querySelector('#dataMessage').textContent.length>0 && souluSettings.current.rules.defaults.microphone===1"),'Writer failure reports error and restores actual persisted controls')
            rulesFile.rmdir();backup.rename(rulesFile)
            change('#permissions-microphone','2');evaluate('souluSettings.flush()')
            check(json.loads(rulesFile.read_text())['defaults']['microphone']==2,'Recovery permits subsequent immediate save')
            section('vpn');beforeVpn=json.loads((data/'settings.json').read_text())['vpn'];change('#vpn-link','unsupported://invalid');evaluate('souluSettings.flush()')
            check(json.loads((data/'settings.json').read_text())['vpn']==beforeVpn,'Invalid VPN key does not overwrite global configuration')
            active=shellcall('getState')['activeTabId'];evaluate('souluSettingsRequestClose()');wait(lambda:not shellcall('getState')['settingsOverlayOpen'])
            check(shellcall('getState')['activeTabId']==active,'Close requires no dirty dialog and preserves active tab')
            stop();start()
            check(evaluate("souluSettings.current.settings.theme==='light' && souluSettings.current.settings.searchEngine==='google' && souluSettings.current.reader.theme==='dark'"),'Settings and reader survive real browser restart')
            section('general');change('#language','en');evaluate('souluSettings.flush()')
            change('#settingsSearch','камера');check(evaluate("document.querySelector('.result strong').textContent==='Camera'"),'Search retains bilingual synonyms after persisted language change')
            for scale in [1,1.25,1.5,1.75,2]:
                s.command(settings,'Emulation.setDeviceMetricsOverride',{'width':max(360,round(1000/scale)),'height':max(400,round(740/scale)),'deviceScaleFactor':scale,'mobile':False})
                section('');capture('cards-dpi-'+str(scale));check(evaluate('document.documentElement.scrollWidth<=innerWidth'),'Home has no horizontal overflow at DPI '+str(scale))
                section('privacy');capture('privacy-dpi-'+str(scale));check(evaluate('document.documentElement.scrollWidth<=innerWidth'),'Section has no horizontal overflow at DPI '+str(scale))
            s.command(settings,'Emulation.clearDeviceMetricsOverride',{})
            a=saved();shellcall('createProfile','Settings B');bId=shellcall('getState')['activeProfileId']
            wait(lambda:evaluate("document.body.classList.contains('ready') && souluSettings.persisted?.profile==="+json.dumps(bId)))
            check(evaluate('souluSettings.current.settings.searchEngine')==legacy['searchEngine'],'Profile B uses its independent legacy template')
            section('search');change('#searchEngine','duckduckgo');evaluate('souluSettings.flush()')
            shellcall('switchProfile','personal');wait(lambda:evaluate("souluSettings.persisted?.profile==='personal'"));check(saved()==a,'Profile B edits do not overwrite Profile A')
            evaluate('souluSettingsRequestClose()');wait(lambda:not shellcall('getState')['settingsOverlayOpen']);shellcall('newIncognito');wait(lambda:shellcall('getState')['incognito']);shellcall('openSettingsWindow');settings=socket('/ui/settings.html')
            wait(lambda:evaluate("document.body.classList.contains('ready')"));check(evaluate("souluSettings.persisted.profile==='personal'"),'Incognito Settings uses ordinary profile without creating another store')
            stop();output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps({'passed':True,'checks':checks,'baseline':'legacy settings fixture','visuals':str(evidence)},indent=2,ensure_ascii=False),encoding='utf-8')
        finally:
            if process and process.poll() is None:
                try:stop()
                except Exception:process.terminate();process.wait(timeout=20)

if __name__=='__main__':main()
