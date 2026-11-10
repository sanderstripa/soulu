"""Real signed VOT install and Windows registration; no account login required."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'scope':'Preview 5 native Windows integrations','checks':{},'limitations':[]}
def trusted_settings_click(selector):
 r=ui('const r=document.querySelector('+json.dumps(selector)+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};','settings');host=chrome('const r=document.getElementById("soulu-settings-frame").getBoundingClientRect();return {x:r.x,y:r.y};')
 m.set_context('chrome');m._send_message('WebDriver:PerformActions',{'actions':[{'type':'pointer','id':'native-input','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport','x':round(r['x']+host['x']),'y':round(r['y']+host['y']),'duration':0},{'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
try:
 (profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'done':True}}));start()
 status=call('browser.vot.status');check('pinned_signed_vot_candidate_loads',status['version']=='1.12.6' and not status['installed'])
 check('vot_install_without_trusted_input_denied',run('try{await Soulu.dispatch("browser.vot.install",{consent:true});return false;}catch(e){return true;}'))
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady']);ui('souluSettings.openSection("translation");souluVideoSettings.open();return true;','settings');wait(lambda:ui('return !!document.getElementById("gecko-vot-install")','settings'));time.sleep(.3)
 ui('const n=document.getElementById("gecko-vot-consent");n.checked=true;n.dispatchEvent(new Event("change"));return true;','settings');trusted_settings_click('#gecko-vot-install')
 check('vot_installed_after_explicit_soulu_consent',wait(lambda:call('browser.vot.status')['installed']))
 signed=run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");const a=await AddonManager.getAddonByID("vot-ext@firefox");return {signed:a.signedState,version:a.version,enabled:a.isActive};');check('vot_firefox_signature_and_version',signed['signed']>=2 and signed['version']=='1.12.6' and signed['enabled'],signed)
 call('browser.vot.setEnabled',{'enabled':False});check('vot_disable_actual_extension',not call('browser.vot.status')['enabled']);call('browser.vot.setEnabled',{'enabled':True});check('vot_enable_actual_extension',call('browser.vot.status')['enabled'])
 ui('document.getElementById("actionDialog").close();return true;','settings');chrome('Soulu.closeSettings()');time.sleep(.3)
 # Attempt genuine public YouTube playback; a CI bot wall is a limitation, never a pass.
 call('browser.navigate','https://www.youtube.com/watch?v=jNQXAC9IVRw');select_latest();time.sleep(12)
 yt=content('const v=document.querySelector("video");return {url:location.href,title:document.title,text:document.body.innerText.slice(0,1800),ready:v?.readyState||0,time:v?.currentTime||0,paused:v?.paused??true};');(out/'youtube-vot-diagnostic.json').write_text(json.dumps(yt,ensure_ascii=False,indent=2),encoding='utf-8')
 report['limitations'].append('VOT installs/enables with native Firefox signature checks. End-to-end Russian YouTube voice-over is not certified by installation alone; see youtube-vot-diagnostic.json and manual playback requirement.')
 if os.name=='nt':
  brand=chrome('return ChromeUtils.importESModule("chrome://soulu/content/window-controls.sys.mjs").brand(window)');check('native_window_icon_is_soulu',brand['icons'],brand)
  group=chrome('return Cc["@mozilla.org/windows-taskbar;1"].getService(Ci.nsIWinTaskbar).getGroupIdForWindow(window)');check('native_taskbar_group_is_soulu',group=='Soulu.Gecko.Preview',group)
  exe=binary.parent.parent/'Soulu.exe';env=dict(os.environ,LOCALAPPDATA=str(root/'environment'))
  count=len(call('browser.state.get')['tabs']);subprocess.run([str(exe),'--url',url+'launcher-url'],env=env,timeout=20,check=True);check('launcher_external_link_reuses_profile',wait(lambda:len(call('browser.state.get')['tabs'])==count+1))
  subprocess.run([str(exe),'--register-default'],env=env,timeout=20,check=True)
  import winreg
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Classes\Soulu.Gecko.URL\shell\open\command') as k:command=winreg.QueryValueEx(k,'')[0]
  check('per_user_http_https_registration_targets_soulu',command=='"'+str(exe)+'" --url "%1"')
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:report['diagnostic']=chrome('return Services.console.getMessageArray().map(m=>m.message).slice(-20)');(out/'optional-failure.png').write_bytes(base64.b64decode(m.screenshot()))
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'optional5.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');log.close();server.shutdown()
