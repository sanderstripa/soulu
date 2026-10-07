"""Native legacy Home migration preserves old choices and does not seed new profiles."""
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
os.environ.update(SOULU_REGRESSION_SKIP_FIRST_RUN='1',NO_PROXY='localhost,127.0.0.1,::1')
checks=[]
def wait(fn,timeout=30):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.1)
 raise AssertionError('Home migration timeout')
def main():
 exe=Path(sys.argv[1]).resolve();report=Path(sys.argv[2]).resolve();connections=[];process=None;shell=None
 with tempfile.TemporaryDirectory(prefix='soulu-home-migration-',ignore_cleanup_errors=True) as root:
  folder=Path(root)/'Soulu/User Data';folder.mkdir(parents=True)
  legacy={'layout':'compact','theme':'light','language':'ru','startupMode':'custom','startupUrl':'https://example.com/startup','newTabMode':'blank','homeMode':'custom','homeUrl':'https://example.com/home','homeWeatherCity':'Paris','homeShortcuts':[{'name':'Old favorite','url':'https://example.com/saved'},{'name':'Duplicate favorite','url':'https://example.com/saved'},{'name':'Другой сайт','url':'https://example.org/legacy'}]}
  (folder/'settings.json').write_text(json.dumps({'settings':legacy,'vpn':{}},ensure_ascii=False),encoding='utf-8')
  original={'id':44,'type':'url','title':'Preserved original title','url':'https://example.com/saved','favicon':'','profileId':'personal','parentId':0,'order':0}
  (folder/'bookmarks.json').write_text(json.dumps([original]),encoding='utf-8')
  env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT))
  def start():
   nonlocal process,shell
   process=subprocess.Popen([str(exe)],env=env)
   target=wait(lambda:next((t for t in s.targets() if '/ui/index.html' in t.get('url','')),None))
   shell=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=30,origin=s.BASE);connections.append(shell)
   wait(lambda:s.evaluate(shell,"typeof window.browserShell?.getSettings==='function'"))
  def check(ok,label):
   assert ok,label;checks.append(label);print('PASS:',label,flush=True)
  def stop():
   nonlocal process
   for ws in connections:
    try:ws.close()
    except Exception:pass
   connections.clear();s.close_normally(process);process=None
  try:
   start();prefs=s.evaluate(shell,'browserShell.getSettings()');marks=s.evaluate(shell,'browserShell.getBookmarks()')
   check(all(prefs[k]==legacy[k] for k in ('startupMode','startupUrl','newTabMode','homeMode','homeUrl')),'Legacy custom Startup Home and blank New Tab choices are preserved')
   check(prefs['homeWeatherMode']=='configured' and prefs['homeWeatherCity']=='Paris','Legacy selected weather city migrates without a silent replacement')
   check(prefs['homeFavoriteIds']==[44,45] and len(marks)==2,'Legacy shortcuts become ordered real favorites and deduplicate existing URLs')
   check(next(x for x in marks if x['id']==44)['title']==original['title'],'Migration preserves the original bookmark title')
   check(prefs['homeShortcuts']==legacy['homeShortcuts'],'Legacy shortcut source data is retained')
   stop();start();check(s.evaluate(shell,'browserShell.getSettings()')['homeFavoriteIds']==[44,45] and len(s.evaluate(shell,'browserShell.getBookmarks()'))==2,'Migration is idempotent after restart')
   s.evaluate(shell,"browserShell.createProfile('Fresh migration profile')")
   wait(lambda:s.evaluate(shell,'browserShell.getState()')['activeProfileId']!='personal');s.targets()
   prefs=s.evaluate(shell,'browserShell.getSettings()')
   check(prefs['startupMode']=='soulu' and prefs['newTabMode']=='soulu' and prefs['homeMode']=='soulu','A genuinely new profile uses Soulu page defaults after legacy migration')
   check(prefs['homeProvider']=='google' and prefs['homeFavoriteIds']==[] and prefs['homeWeatherCity']=='','New profile does not inherit migrated favorites provider or location')
   report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps({'passed':True,'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
  finally:
   if process and process.poll() is None:stop()
if __name__=='__main__':main()
