"""Native Home geometry, popovers, permissions, offline shell and weather service."""
import base64
import ctypes
from ctypes import wintypes as W
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from PIL import ImageGrab

spec=importlib.util.spec_from_file_location('storage',Path(__file__).with_name('test-cef-storage.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
u=ctypes.windll.user32
u.SetForegroundWindow.argtypes=[W.HWND];u.GetWindowRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
u.ShowWindow.argtypes=[W.HWND,ctypes.c_int]
def find_window(pid):
 handles=[]
 callback_type=ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
 u.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
 @callback_type
 def visit(hwnd,_):
  owner=W.DWORD();u.GetWindowThreadProcessId(hwnd,ctypes.byref(owner));name=ctypes.create_unicode_buffer(256)
  u.GetClassNameW(hwnd,name,len(name))
  if owner.value==pid and name.value=='SouluBrowserWindow':handles.append(hwnd)
  return True
 u.EnumWindows(visit,0)
 return handles[0] if handles else None
os.environ['SOULU_REGRESSION_SKIP_FIRST_RUN']='1'
os.environ['NO_PROXY']='localhost,127.0.0.1,::1'
checks=[]
def wait(fn,timeout=30):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  value=fn()
  if value:return value
  time.sleep(.1)
 raise AssertionError('Home design timeout')
def check(value,name):
 assert value,name
 checks.append(name);print('PASS:',name,flush=True)
def main():
 exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='soulu-home-design-',ignore_cleanup_errors=True) as root:
  env=dict(os.environ,LOCALAPPDATA=root,SOULU_UI_TEST_PORT=str(s.DEBUG_PORT),SOULU_REGRESSION_SKIP_FIRST_RUN='1')
  process=subprocess.Popen([str(exe),'--no-proxy-server'],env=env);sockets=[]
  def connect(fragment):
   target=wait(lambda:next((x for x in s.targets() if fragment in x.get('url','')),None))
   ws=s.websocket.create_connection(target['webSocketDebuggerUrl'],timeout=40,origin=s.BASE);sockets.append(ws);return ws
  try:
   shell=connect('/ui/index.html');home=connect('/ui/home.html');wait(lambda:s.evaluate(home,"typeof window.souluHomeApply==='function' && document.fonts.check('400 14px Onest')"))
   def bridge(ws,action,payload=None):return s.evaluate(ws,"new Promise((resolve,reject)=>cefQuery({request:"+json.dumps(json.dumps({'action':action,'payload':payload}))+",onSuccess:v=>resolve(v?JSON.parse(v):null),onFailure:(_,m)=>reject(Error(m))}))")
   def settings(patch):return s.evaluate(shell,'browserShell.setSettings('+json.dumps(patch)+')')
   def capture(name,native=False):
    s.evaluate(home,'new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    if native:
     hwnd=wait(lambda:find_window(process.pid));u.SetForegroundWindow(hwnd);ctypes.windll.dwmapi.DwmFlush();r=W.RECT();u.GetWindowRect(hwnd,ctypes.byref(r));ImageGrab.grab(bbox=(r.left,r.top,r.right,r.bottom),include_layered_windows=True,all_screens=True).save(out/(name+'.png'))
    else:(out/(name+'.png')).write_bytes(base64.b64decode(s.command(home,'Page.captureScreenshot',{'format':'png','captureBeyondViewport':False})['data']))
   def geometry():
    return s.evaluate(home,"(()=>{const box=id=>{const r=document.getElementById(id).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};return {w:innerWidth,h:innerHeight,logo:box('logo'),search:box('search'),weather:box('weatherToggle'),favorites:box('favoritesToggle'),input:box('query'),overflow:document.documentElement.scrollWidth>innerWidth||document.documentElement.scrollHeight>innerHeight}})()")
   for language in ('ru','en'):
    for theme in ('light','dark','system'):
     settings({'language':language,'theme':theme})
     wait(lambda:bridge(home,'home.get')['language']==language)
     for scale in (1,1.25,1.5,2):
      for width,height in ((1280,800),(640,480),(360,420)):
       s.command(home,'Emulation.setDeviceMetricsOverride',{'width':width,'height':height,'deviceScaleFactor':scale,'mobile':False})
       row=geometry();check(not row['overflow'] and abs(row['search']['x']+row['search']['w']/2-width/2)<2 and row['input']['w']>25 and row['search']['right']<=width, f'Layout {language}/{theme}/{scale}/{width}')
      s.command(home,'Emulation.setDeviceMetricsOverride',{'width':1280,'height':800,'deviceScaleFactor':scale,'mobile':False})
      capture(f'home-{language}-{theme}-{scale}')
   s.command(home,'Emulation.clearDeviceMetricsOverride');settings({'language':'ru','theme':'light','layout':'compact'})
   capture('light-main-normal',True);hwnd=wait(lambda:find_window(process.pid));u.ShowWindow(hwnd,3);time.sleep(.3);capture('light-main-maximized',True);u.ShowWindow(hwnd,9)
   settings({'theme':'dark'});capture('dark-main',True);settings({'theme':'light','layout':'classic'});capture('light-classic',True);settings({'layout':'compact'})
   for name in ('provider','weather','favorites'):
    s.evaluate(home,"document.getElementById('"+name+"Toggle').click()")
    check(s.evaluate(home,"!document.getElementById('"+name+"Panel').hidden"),name+' panel opens')
    capture(name+'-popover',True)
    s.command(home,'Input.dispatchKeyEvent',{'type':'keyDown','key':'Escape','code':'Escape','windowsVirtualKeyCode':27})
   bridge(shell,'browser.sites.set',{'domain':'soulu://home','permission':'microphone','value':2})
   check(bridge(home,'home.voice')['status']=='denied','Native microphone denial respects profile permission')
   bridge(shell,'browser.sites.set',{'domain':'soulu://home','permission':'microphone','value':0})
   s.evaluate(home,"window.voiceResult=null;cefQuery({request:JSON.stringify({action:'home.voice'}),onSuccess:v=>window.voiceResult=JSON.parse(v),onFailure:()=>window.voiceResult={status:'error'}})")
   bridge(home,'home.voice.cancel');wait(lambda:s.evaluate(home,'window.voiceResult!==null'))
   check(s.evaluate(home,"['cancelled','unavailable','denied','error'].includes(window.voiceResult.status)"),'Native voice cancel/no-device path releases without a crash')
   settings({'homeWeatherMode':'configured','homeWeatherCity':'Yekaterinburg','homeWeatherUnits':'celsius'})
   data=bridge(home,'home.weather');check(data['status']=='ready' and len(data['daily']['time'])>=4,'Real HTTPS weather current and forecast')
   again=bridge(home,'home.weather');check(data['fetchedAt']==again['fetchedAt'],'Weather service shares a fresh cache')
   s.evaluate(home,"document.querySelector('#weatherToggle').click()")
   wait(lambda:s.evaluate(home,"document.querySelectorAll('.forecast-day').length>=3"));capture('weather-real-forecast',True)
   check((Path(root)/'Soulu/User Data/Profiles/personal/soulu-weather.json').is_file(),'Normal profile weather cache persists')
   s.command(home,'Network.enable');s.command(home,'Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':0,'uploadThroughput':0});s.command(home,'Page.reload')
   wait(lambda:s.evaluate(home,"typeof window.souluHomeApply==='function' && document.documentElement.classList.contains('typography-ready')"))
   check(s.evaluate(home,"document.querySelector('#logo').complete && !document.querySelector('#query').disabled"),'Offline reload renders local logo, font and usable input')
   capture('offline-home')
   (out/'home-design.json').write_text(json.dumps({'passed':True,'checks':checks,'limitations':['DeviceScaleFactor covers renderer scaling; physical Windows monitor DPI must be checked separately.','Synthetic/cancel checks do not prove live RU/EN microphone recognition.']},ensure_ascii=False,indent=2),encoding='utf-8')
  finally:
   for ws in sockets:
    try:ws.close()
    except Exception:pass
   if process.poll() is None:s.close_normally(process)
if __name__=='__main__':main()
