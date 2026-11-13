"""Only changes after the successful 66-check Windows candidate, plus retained translation/weather."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'scope':'Final small fixes after full Windows run 41653080983','checks':{},'limitations':[]}
try:
 (profile/'sona-settings.json').write_text(json.dumps({'settings':{'layout':'compact'}}),encoding='utf-8')
 start()
 check('legacy_compact_setting_migrates_to_adaptive',call('settings.begin')['settings']['layout']=='adaptive')
 check('no_native_firefox_startup_modal',chrome('return !document.documentElement.hasAttribute("window-modal-open")'))
 check('forward_hidden_when_unavailable',ui('const b=document.getElementById("geckoForward");return !!b&&getComputedStyle(b).display==="none"'))
 call('browser.navigate',url);wait(lambda:content('return location.href==='+json.dumps(url)+'&&!!document.getElementById("v")'))
 call('browser.navigate',url+'forward-target');wait(lambda:content('return location.pathname==="/forward-target"'))
 call('browser.back');wait(lambda:content('return location.pathname==="/"'))
 check('forward_button_enabled_on_native_history',wait(lambda:ui('const b=document.getElementById("geckoForward");return !!b&&!b.disabled&&getComputedStyle(b).display!=="none"')))
 ui('document.getElementById("geckoForward").click();return true;');check('forward_button_navigates_real_page',wait(lambda:content('return location.pathname==="/forward-target"')))
 # A genuinely typed/submitted login, approved via the native save prompt.
 chrome('Services.prefs.setBoolPref("signon.autofillForms.http",true)')
 call('browser.navigate',url+'login-save');wait(lambda:content('return !!document.getElementById("password")'))
 m.set_context('content');m.find_element('id','username').send_keys('saved-through-site');m.find_element('id','password').send_keys('fixture-site-save');m.find_element('tag name','button').click()
 wait(lambda:chrome('return !!PopupNotifications.getNotification("password",gBrowser.selectedBrowser)'))
 wait(lambda:chrome('const n=document.getElementById("password-notification"),p=PopupNotifications.getNotification("password",gBrowser.selectedBrowser);return !!n?.button&&!n.button.disabled&&p?.timeShown&&ChromeUtils.now()-p.timeShown>Services.prefs.getIntPref("security.notification_enable_delay",500)+100'))
 check('native_save_prompt_action',chrome('const n=document.getElementById("password-notification");if(!n?.button)return false;n.button.click();return true;'))
 check('native_submitted_login_saved_in_nss',wait(lambda:any(r['username']=='saved-through-site' for r in call('browser.passwords.get'))))
 chrome('Services.prefs.clearUserPref("signon.autofillForms.http")')
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady'])
 ui('sonaSettings.openSection("general");return true;','settings')
 # Locate the original section containing the default-browser action.
 check('unsupported_default_registration_explicitly_disabled',wait(lambda:ui('return !!document.querySelector("#control-settings-defaultBrowser button")?.disabled','settings')))
 ui('sonaSettings.openSection("privacy");return true;','settings')
 # Original groups are split into 12 sections; find the blocker control.
 filters=ui('for(const b of document.querySelectorAll("#homeCards [data-section]")){sonaSettings.openSection(b.dataset.section);if(document.getElementById("blocking-contentBlocking"))return true;}return false;','settings')
 check('filter_update_control_exposed',filters and wait(lambda:ui('return !!document.querySelector("[data-filter-update]")','settings')))
 chrome('Sona.closeSettings()');time.sleep(.25)
 if not args.ui_only:
  # Inject data responses only in the parent TEST process, exercising the real
  # async Rust validation and its JS rejection path, without changing any URL.
  failed=run('const before=Sona.adblock.status(),original=window.fetch;let rejected=false;try{window.fetch=async()=>new Response("<html>bad upstream response</html>",{headers:{"content-type":"text/plain"}});try{await Sona.adblock.update();}catch(e){rejected=true;}const after=Sona.adblock.status();return {rejected,ready:after.ready,same:before.networkRules===after.networkRules&&before.cosmeticRules===after.cosmeticRules,error:!!after.lastUpdateError};}finally{window.fetch=original;}')
  check('failed_filter_compile_rejects_and_preserves_active_engine',all(failed.values()),failed)
  call('browser.settings.set',{'homeWeatherMode':'configured','homeWeatherCity':'Moscow','homeWeatherUnits':'celsius'})
  weather=call('home.weather');check('real_weather_provider_response',weather.get('status') in ['ready','stale'] and isinstance(weather.get('current',{}).get('temperature_2m'),(int,float)),{'status':weather.get('status'),'temperature':weather.get('current',{}).get('temperature_2m')})
  call('browser.navigate',url+'article');wait(lambda:content('return !!document.querySelector("article")'))
  ui('document.querySelector(".sona-translate-button").click();return true;');wait(lambda:ui('return !!document.getElementById("gecko-translation-run")'))
  ui('document.getElementById("gecko-translation-from").value="en";document.getElementById("gecko-translation-to").value="ru";document.getElementById("gecko-translation-run").click();return true;')
  check('real_local_russian_translation',wait(lambda:content('return /[А-Яа-я]/.test(document.querySelector("article").textContent)'),180))
  ui('document.getElementById("gecko-translation-restore").click();return true;');check('translation_restores_original',wait(lambda:content('return document.querySelector("article")?.textContent.includes("beautiful day")')))
 if os.name=='nt':
  import ctypes as C
  from ctypes import wintypes as W
  exe=binary.parent.parent/'Sona Gecko Preview 4.exe';large=C.c_void_p();small=C.c_void_p();C.windll.shell32.ExtractIconExW.argtypes=[W.LPCWSTR,C.c_int,C.POINTER(C.c_void_p),C.POINTER(C.c_void_p),C.c_uint]
  icons=C.windll.shell32.ExtractIconExW(str(exe),0,C.byref(large),C.byref(small),1);check('original_cef_icon_in_portable_exe',icons>=1 and large.value is not None and small.value is not None)
  for icon in [large,small]:
   if icon.value:C.windll.user32.DestroyIcon(icon)
 report['passed']=True
except Exception as error:
 report['error']=str(error)
 import traceback;report['traceback']=traceback.format_exc()
 try:report['diagnostic']=chrome('return {url:gBrowser.selectedBrowser.currentURI.spec,errors:Services.console.getMessageArray().map(m=>m.message).filter(s=>/sona|Error|ranslat/.test(s)).slice(-15)}');(out/'final-failure.png').write_bytes(base64.b64decode(m.screenshot()))
 except Exception:pass
 raise
finally:
 stop();server.shutdown();log.close();(out/'final4.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
