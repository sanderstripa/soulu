"""User extensions remain native and controllable through the grouped UI."""
from pathlib import Path
source=Path(__file__).with_name('extensions.py').read_text().split('\ntry:\n',1)[0]
exec(compile(source,str(Path(__file__).with_name('extensions.py')),'exec'),globals())
report={'passed':False,'checks':{}}
def click_settings(selector):
 wait(lambda:chrome('return document.getElementById("soulu-settings-frame").getAnimations().length===0'));ui('document.querySelector('+json.dumps(selector)+').scrollIntoView({block:"center"});return true','settings')
 r=ui('const r=document.querySelector('+json.dumps(selector)+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};','settings');offset=chrome('const r=document.getElementById("soulu-settings-frame").getBoundingClientRect();return {x:r.x,y:r.y};')
 m.set_context('chrome');m._send_message('WebDriver:PerformActions',{'actions':[{'type':'pointer','id':'settings-extension-click','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport','x':round(r['x']+offset['x']),'y':round(r['y']+offset['y']),'duration':0},{'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
try:
 (profile/'soulu-settings.json').write_text(json.dumps({'onboarding':{'done':True}}));start();call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 path=root/'menu-fixture.xpi';fixture(path,fixture_id);install(path);wait(lambda:any(i['id']==fixture_id and i['action'] for i in action_items()))
 check('extension_icons_are_grouped_only',ui('return !!document.getElementById("soulu-extensions-menu")&&!document.querySelector("[data-extension-toolbar] [data-extension-id]")'))
 real_click('#soulu-extensions-menu');check('group_menu_lists_real_extension',wait(lambda:chrome('const p=document.querySelector("menupopup[data-soulu-extensions]");return p?.state==="open"&&p.querySelector("[data-extension-id]")?.dataset.extensionId==="'+fixture_id+'"')))
 m.set_context('chrome');m._send_message('WebDriver:PerformActions',{'actions':[{'type':'key','id':'extension-menu-enter','actions':[{'type':'keyDown','value':'\ue010'},{'type':'keyUp','value':'\ue010'},{'type':'keyDown','value':'\ue007'},{'type':'keyUp','value':'\ue007'}]}]})
 check('group_menu_opens_actual_remote_popup',wait(lambda:(lambda p:p and p['state']=='open' and p['remote'].startswith('extension'))(popup_state())));capture_popup('grouped-extension-popup.png');call('browser.extensions.close')
 call('browser.settings.openWindow','extensions');wait(lambda:call('browser.state.get')['settingsOverlayReady']);ui('souluSettings.openSection("extensions");return true','settings');selector='input[data-extension-id="'+fixture_id+'"]';wait(lambda:ui('return !!document.querySelector('+json.dumps(selector)+')','settings'))
 check('no_obsolete_pin_setting',ui('return !document.getElementById("extensionPins").textContent.includes("после VPN")','settings'))
 click_settings(selector);check('settings_switch_disables_actual_addon',wait(lambda:not next(i for i in action_items() if i['id']==fixture_id)['enabled']));check('disabled_addon_remains_manageable',wait(lambda:ui('const n=document.querySelector('+json.dumps(selector)+');return !!n&&!n.disabled&&!n.checked','settings')))
 click_settings(selector);check('settings_switch_enables_actual_addon',wait(lambda:next(i for i in action_items() if i['id']==fixture_id)['enabled']))
 run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");await (await AddonManager.getAddonByID('+json.dumps(fixture_id)+')).uninstall();return true;');check('native_addon_uninstall_removes_user_extension',wait(lambda:not any(i['id']==fixture_id for i in action_items())))
 check('signature_enforcement_retained',chrome('return Services.prefs.getBoolPref("xpinstall.signatures.required",true)'))
 report['passed']=True
except Exception as error:
 report['error']=str(error)
 try:(out/'extensions-failure.png').write_bytes(base64.b64decode(m.screenshot()));report['console']=chrome('return Services.console.getMessageArray().map(x=>x.message).slice(-15)')
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'extensions7.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
