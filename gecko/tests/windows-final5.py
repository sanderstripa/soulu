"""Only the remaining Windows branding, launcher and registration gates."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{}}
try:
 (profile/'sona-settings.json').write_text(json.dumps({'onboarding':{'done':True}}));start()
 brand=chrome('return window.__sonaBrand');check('startup_window_icons_loaded',brand['icons'],brand)
 group=chrome('return Cc["@mozilla.org/windows-taskbar;1"].getService(Ci.nsIWinTaskbar).getGroupIdForWindow(window)');check('native_taskbar_group_is_sona',group=='Sona.Gecko.Preview',group)
 exe=binary.parent.parent/'Sona.exe';env=dict(os.environ,LOCALAPPDATA=str(root/'environment'))
 count=len(call('browser.state.get')['tabs']);subprocess.run([str(exe),'--url',url+'launcher-url'],env=env,timeout=20,check=True);check('launcher_url_reuses_profile',wait(lambda:len(call('browser.state.get')['tabs'])==count+1));select_latest();check('launcher_url_loads_real_page',wait(lambda:content('return location.pathname==="/launcher-url"')))
 original=m.current_window_handle;known=set(m.window_handles);subprocess.run([str(exe),'--private'],env=env,timeout=20,check=True);wait(lambda:len(m.window_handles)>len(known));private=next(h for h in m.window_handles if h not in known);m.switch_to_window(private);check('launcher_private_uses_native_private_window',wait(lambda:chrome('return !!Sona?.ready&&Sona.backend.isPrivate')));chrome('window.close()');m.switch_to_window(original)
 # Registration leaves UserChoice to Windows. This disposable CI user owns the keys.
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady']);ui('sonaSettings.openSection("general");return true;','settings');chrome('window.focus();document.getElementById("sona-settings-frame").focus();');wait(lambda:chrome('return Services.focus.activeWindow===window'));time.sleep(.25)
 ui('window.__registrationProbe={};const original=window.cefQuery;window.cefQuery=args=>{if(JSON.parse(args.request).action!=="settings.defaultBrowser")return original(args);window.__registrationProbe.request=true;original({...args,onSuccess:v=>{window.__registrationProbe.value=v;args.onSuccess(v);},onFailure:(c,m)=>{window.__registrationProbe.error=m;args.onFailure(c,m);}});};return true;','settings')
 r=ui('const r=document.querySelector("#control-settings-defaultBrowser button").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};','settings');host=chrome('const r=document.getElementById("sona-settings-frame").getBoundingClientRect();return {x:r.x,y:r.y};')
 m.set_context('chrome');m._send_message('WebDriver:PerformActions',{'actions':[{'type':'pointer','id':'default-browser-click','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport','x':round(r['x']+host['x']),'y':round(r['y']+host['y']),'duration':0},{'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
 import winreg
 def registered():
  try:
   with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Classes\Sona.Gecko.URL\shell\open\command') as key:return bool(winreg.QueryValueEx(key,'')[0])
  except FileNotFoundError:return False
 check('default_browser_button_runs_real_registration',wait(registered,20))
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Classes\Sona.Gecko.URL\shell\open\command') as k:command=winreg.QueryValueEx(k,'')[0]
 check('per_user_url_command_targets_sona',command=='"'+str(exe)+'" --url "%1"',command)
 for scheme in ['http','https']:
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Clients\StartMenuInternet\SonaGecko\Capabilities\URLAssociations') as k:value=winreg.QueryValueEx(k,scheme)[0]
  check('registered_'+scheme,value=='Sona.Gecko.URL')
 properties=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"(Get-Item -LiteralPath '"+str(exe).replace("'","''")+"').VersionInfo | Select-Object ProductName,FileDescription,FileVersion | ConvertTo-Json -Compress"],encoding='utf-8'));check('exe_windows_properties_brand_sona',properties['ProductName']=='Sona Gecko' and properties['FileVersion']=='0.5.0.0',properties)
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:report['ui']=ui('return {probe:window.__registrationProbe,message:document.getElementById("dataMessage")?.textContent,sectionError:document.getElementById("sectionError")?.textContent,focused:document.hasFocus()};','settings');report['diagnostic']=chrome('return {brand:window.__sonaBrand,errors:Services.console.getMessageArray().map(m=>m.message).filter(s=>/sona/i.test(s)).slice(-12)}')
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'windows-final5.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');log.close();server.shutdown()
