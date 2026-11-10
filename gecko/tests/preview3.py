"""Targeted Preview 3 checks: only the requested UI, weather and translation changes."""
from pathlib import Path
source=Path(__file__).with_name('preview2.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0]
source=source.replace('Soulu Gecko Preview 2.exe','Soulu Gecko Preview 3.exe').replace('<meta charset=utf-8>','<meta charset=utf-8><html lang=en>').replace('Gecko fixture','This is a beautiful day. The browser is fast and easy to use. You can read the latest news and learn more about the world.')
exec(compile(source,str(Path(__file__).with_name('preview2.py')),'exec'),globals())
report={'passed':False,'scope':'Preview 3 requested fixes only','checks':{}}
try:
 start()
 wait(lambda:chrome('return document.documentElement.hasAttribute("soulu-ui-ready")'),10)
 print('EARLY_DIAGNOSTIC',chrome('return {ready:document.documentElement.hasAttribute("soulu-ui-ready"),display:getComputedStyle(document.getElementById("navigator-toolbox")).display,registered:Cc["@mozilla.org/content/style-sheet-service;1"].getService(Ci.nsIStyleSheetService).sheetRegistered(Services.io.newURI("chrome://soulu/content/early.css"),Cc["@mozilla.org/content/style-sheet-service;1"].getService(Ci.nsIStyleSheetService).USER_SHEET),early:window.__souluEarlyDisplay,uri:document.documentURI}'),flush=True)
 check('early_global_stylesheet_and_own_first_surface',chrome('return document.documentElement.hasAttribute("soulu-ui-ready") && getComputedStyle(document.getElementById("navigator-toolbox")).display==="none" && Cc["@mozilla.org/content/style-sheet-service;1"].getService(Ci.nsIStyleSheetService).sheetRegistered(Services.io.newURI("chrome://soulu/content/early.css"),Cc["@mozilla.org/content/style-sheet-service;1"].getService(Ci.nsIStyleSheetService).USER_SHEET)'))
 for width,height in [(1000,740),(780,600),(1120,780)]:
  chrome(f'window.resizeTo({width},{height});');time.sleep(.15)
  check('native_firefox_chrome_hidden_resize_'+str(width),chrome('return ["navigator-toolbox","titlebar","sidebar-main"].every(id=>!document.getElementById(id)||getComputedStyle(document.getElementById(id)).display==="none")'))
 # Exercise the actual popup and verify six CEF-equivalent commands at the pointer.
 menu=run('const x=window.mozInnerScreenX+160,y=window.mozInnerScreenY+30;const result=Soulu.dispatch("window.toolbarMenu",null,{pointer:{screenX:x,screenY:y}});for(let i=0;i<50;i++){const p=[...document.querySelectorAll("menupopup")].find(p=>p.state==="open"&&p.children.length===7);if(p){const r=p.getBoundingClientRect();const labels=[...p.querySelectorAll("menuitem")].map(n=>n.getAttribute("label"));const delta=Math.abs(r.x-160);p.hidePopup();await result;return {labels,delta};}await new Promise(r=>setTimeout(r,20));}throw Error("Toolbar popup did not open");')
 check('toolbar_menu_six_commands_at_clicked_position',len(menu['labels'])==6 and menu['delta']<25,menu)
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady']);time.sleep(.25)
 ui('souluSettings.openSection("about");return true;','settings');time.sleep(.15)
 versions=ui('return [...document.querySelectorAll(".version-grid strong")].map(n=>n.textContent);','settings');check('about_versions_remain_visible_after_state_updates',len(versions)>=6 and 'Gecko Preview 3' in versions and versions[1]!='—',versions)
 (out/'about-preview3.png').write_bytes(base64.b64decode(m.screenshot()))
 ui('souluSettings.openSection("extensions");return true;','settings');check('firefox_extensions_store_no_chrome_embedding',ui('return !document.getElementById("sectionContent").textContent.includes("Chrome Web Store")&&document.getElementById("sectionContent").textContent.includes("Firefox Add-ons")','settings'))
 ui('souluSettings.openSection("interface");document.querySelector("input[name=settings-layout][value=compact]").click();await souluSettings.flush();return true;','settings');time.sleep(.5)
 check('original_compact_toolbar_and_58px_page_geometry',ui('return document.body.dataset.layout==="compact"&&getComputedStyle(document.querySelector(".compact-toolbar")).display!=="none"') and abs(chrome('return gBrowser.selectedBrowser.getBoundingClientRect().top')-58)<2)
 ui('document.querySelector("input[name=settings-layout][value=adaptive]").click();await souluSettings.flush();return true;','settings');time.sleep(.4)
 call('browser.settings.set',{'mattePanel':False});time.sleep(.1);opaque=ui('return getComputedStyle(document.querySelector(".classic-toolbar")).backgroundImage')
 call('browser.settings.set',{'mattePanel':True});time.sleep(.1);matte=ui('return getComputedStyle(document.querySelector(".classic-toolbar")).backgroundImage')
 if os.name=='nt':check('windows_native_backdrop_is_enabled',chrome('return !!Soulu.material?.native'),chrome('return Soulu.material'))
 check('matte_toggle_changes_actual_material',opaque!=matte,{'opaque':opaque,'matte':matte,'native':chrome('return Soulu.material')})
 chrome('Soulu.closeSettings()');check('settings_exit_is_animated',chrome('return !document.getElementById("soulu-settings-frame").hidden&&document.getElementById("soulu-settings-frame").getAnimations().length>0'));time.sleep(.3)
 check('settings_hide_after_animation_finishes',chrome('return document.getElementById("soulu-settings-frame").hidden'))
 call('browser.overview',True);time.sleep(.15);check('overview_no_search_autofocus_and_centered_close',ui('const b=document.querySelector(".overview-close"),s=getComputedStyle(b);return document.activeElement?.className!=="navigation-search"&&s.paddingTop==="0px"&&s.display==="grid"&&b.querySelector("svg")&&Math.abs(b.getBoundingClientRect().width-b.getBoundingClientRect().height)<1;'));
 (out/'overview-preview3.png').write_bytes(base64.b64decode(m.screenshot()))
 call('browser.overview',False)
 call('browser.newTab');time.sleep(.4);call('browser.closeTab',call('browser.state.get')['activeTabId']);time.sleep(.05)
 check('single_remaining_tab_row_never_flashes',ui('return document.body.dataset.adaptiveExpanded==="false"&&getComputedStyle(document.querySelector(".tabs-zone")).visibility==="hidden";'))
 if not args.ui_only:
  # A real provider response, not a fixture or a button check.
  call('browser.settings.set',{'homeWeatherMode':'configured','homeWeatherCity':'Moscow','homeWeatherUnits':'celsius'})
  weather=call('home.weather');check('actual_open_meteo_city_and_current_temperature',weather.get('status') in ['ready','stale'] and isinstance(weather.get('current',{}).get('temperature_2m'),(int,float)),weather)
 call('browser.navigate',url);select_latest();wait(lambda:content('return !!document.getElementById("box")'))
 check('translation_button_in_original_address_capsule',wait(lambda:ui('return !!document.querySelector(".classic-address-pill .soulu-translate-button");')))
 if not args.ui_only:
  ui('document.querySelector(".soulu-translate-button").click();return true;');wait(lambda:ui('return !!document.getElementById("gecko-translation-run");'))
  ui('document.getElementById("gecko-translation-from").value="en";document.getElementById("gecko-translation-to").value="ru";document.getElementById("gecko-translation-run").click();return true;')
  check('real_local_gecko_translation_changes_page_text',wait(lambda:content('return /[А-Яа-я]/.test(document.getElementById("box").textContent)'),180))
  ui('document.getElementById("gecko-translation-restore").click();return true;');check('translation_restores_original',wait(lambda:content('return document.getElementById("box")?.textContent.startsWith("This is a beautiful day")'),30))
 if os.name=='nt':
  import ctypes as C
  from ctypes import wintypes as W
  exe=binary.parent.parent/'Soulu Gecko Preview 3.exe';large=C.c_void_p();small=C.c_void_p();C.windll.shell32.ExtractIconExW.argtypes=[W.LPCWSTR,C.c_int,C.POINTER(C.c_void_p),C.POINTER(C.c_void_p),C.c_uint]
  icons=C.windll.shell32.ExtractIconExW(str(exe),0,C.byref(large),C.byref(small),1);check('launcher_contains_cef_app_icon',icons>=1 and large.value is not None,{'path':str(exe),'exists':exe.exists(),'count':icons,'large':large.value,'small':small.value,'lastError':C.windll.kernel32.GetLastError()})
  for icon in [large,small]:
   if icon.value:C.windll.user32.DestroyIcon(icon)
 # Screenshots for this change set only.
 for theme in ['light','dark']:
  call('browser.settings.set',{'theme':theme});time.sleep(.25);(out/(theme+'-preview3.png')).write_bytes(base64.b64decode(m.screenshot()))
 report['passed']=True
except Exception as error:
 report['error']=str(error)
 try:
  report['diagnostic']=chrome('return {url:gBrowser.selectedBrowser.currentURI.spec,pref:Services.prefs.getBoolPref("browser.translations.enable",false),group:gBrowser.selectedBrowser.getAttribute("messagemanagergroup"),errors:Services.console.getMessageArray().map(x=>x.message).filter(x=>/soulu|ranslat|Error/.test(x)).slice(-20)}')
  print('FAILURE_DIAGNOSTIC',json.dumps(report['diagnostic']),flush=True)
  (out/'failure.png').write_bytes(base64.b64decode(m.screenshot()))
  print('TRANSLATION_UI_STATUS',ui('return document.getElementById("gecko-translation-status")?.textContent||"";'),flush=True)
 except Exception as diagnostic_error:print('DIAGNOSTIC_ERROR',str(diagnostic_error),flush=True)
 raise
finally:
 stop();server.shutdown();log.close();(out/'preview3.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
