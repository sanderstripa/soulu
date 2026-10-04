"""Actual official HTTPS update, cache restart and failed-update fallback."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def wait(fn,timeout=150):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=fn()
        if value:return value
        time.sleep(.25)
    raise AssertionError('Filter update timeout')
out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True);evidence={}
with tempfile.TemporaryDirectory(prefix='soulu-adblock-update-',ignore_cleanup_errors=True) as root:
    os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
    env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1')
    env.pop('SOULU_ADBLOCK_NO_UPDATE',None);env.pop('SOULU_ADBLOCK_TEST_RULES',None)
    for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        env.pop(key,None)
    process=None;shell=None
    def start(environment):
        global process,shell
        process=subprocess.Popen([sys.argv[1],'--no-proxy-server'],env=environment)
        target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None),45)
        shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE)
        wait(lambda:s.evaluate(shell,"typeof window.browserShell==='object'"),20)
    def status():return s.evaluate(shell,'window.browserShell.getCurrentSite()')['adblock']
    def stop():shell.close();s.close_normally(process)
    try:
        start(env)
        def updated():
            r=status();evidence['lastStatus']=r
            if r.get('lastUpdateError'):raise AssertionError(r['lastUpdateError'])
            return r if r.get('lastSuccessfulUpdate',0)>0 else None
        completed=wait(updated)
        cache=Path(root)/'Soulu'/'User Data'/'AdBlock'/'filters-v1.json'
        assert cache.exists() and completed['ready'] and completed['source']=='cache'
        evidence['successful_https_update']=completed;stop()
        offline=dict(env,SOULU_ADBLOCK_NO_UPDATE='1');start(offline)
        restored=status();assert restored['lastSuccessfulUpdate']==completed['lastSuccessfulUpdate'] and restored['source']=='cache'
        evidence['restart_cached_offline']=restored;stop()
        # Make cache due, then use a closed local proxy to force a bounded network failure.
        data=json.loads(cache.read_text(encoding='utf-8'));data['updated']=0
        cache.write_text(json.dumps(data),encoding='utf-8')
        failed=dict(env,HTTPS_PROXY='http://127.0.0.1:1',HTTP_PROXY='http://127.0.0.1:1',ALL_PROXY='http://127.0.0.1:1')
        start(failed);retained=wait(lambda:(r if (r:=status()).get('lastUpdateError') else None),45)
        assert retained['ready'] and retained['source']=='cache' and retained['networkRules']==restored['networkRules']
        evidence['failed_update_retained_cache']=retained;stop();process=None
        evidence['passed']=True
    finally:
        if process and process.poll() is None:process.kill();process.wait()
        out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'passed':True,'evidence':str(out)}))
