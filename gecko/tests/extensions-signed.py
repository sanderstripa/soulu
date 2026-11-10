"""Real AMO-signed add-on: native pin persistence, disable and restart."""
import urllib.request,hashlib
signed=root/'multi-account-containers.xpi'
with urllib.request.urlopen('https://addons.mozilla.org/firefox/downloads/file/5168122/multi_account_containers-8.4.0.xpi',timeout=90) as response:signed.write_bytes(response.read())
assert hashlib.sha256(signed.read_bytes()).hexdigest()=='10936d682e17bd2e8afa018bde94f927b50cf05973d6ef8ca3c54f807b2cf7ba'
installed=run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");const file=Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);file.initWithPath('+json.dumps(str(signed))+');const install=await AddonManager.getInstallForFile(file);return await new Promise((resolve,reject)=>{install.addListener({onInstallEnded(i,a){resolve({id:a.id,signed:a.signedState,temporary:a.temporarilyInstalled});},onInstallFailed(i){reject(Error("Signed fixture install failed: "+i.error));},onDownloadFailed(i){reject(Error("Signed fixture download failed"));}});install.install();});')
check('real_amo_signature_verified_by_firefox',installed['signed']>=2 and not installed['temporary'],installed)
signed_id=installed['id'];wait(lambda:any(i['id']==signed_id and i['action'] for i in action_items()))
call('browser.extensions.pin',{'profile':'default','id':signed_id,'pinned':True});native_selector='[data-extension-toolbar="classic"] [data-extension-id="'+signed_id+'"]';wait(lambda:ui('return !!document.querySelector('+json.dumps(native_selector)+')'))
call('browser.settings.set',{'startupMode':'soulu'});stop();start()
check('firefox_default_browser_prompt_disabled_after_restart',chrome('return !Services.prefs.getBoolPref("browser.shell.checkDefaultBrowser")&&Services.prefs.prefIsLocked("browser.shell.checkDefaultBrowser")&&!document.documentElement.hasAttribute("window-modal-open")'))
check('signed_extension_and_native_pin_survive_restart',wait(lambda:any(i['id']==signed_id and i['enabled'] and i['pinned'] for i in action_items())) and wait(lambda:ui('return !!document.querySelector('+json.dumps(native_selector)+')')))
call('browser.navigate',url);select_latest();wait(lambda:content('return location.href==='+json.dumps(url)+'&&!!document.getElementById("v")'))
wait(lambda:next(i for i in action_items() if i['id']==signed_id)['actionEnabled'])
print('SIGNED_ACTION_DIAGNOSTIC',ui('const b=document.querySelector('+json.dumps(native_selector)+');const r=b.getBoundingClientRect();return {item:(()=>{const i=window.souluExtensionToolbar.items.find(i=>i.id==='+json.dumps(signed_id)+');return i?{id:i.id,enabled:i.enabled,actionEnabled:i.actionEnabled}:null;})(),disabled:b.disabled,rect:{x:r.x,y:r.y,w:r.width,h:r.height},active:document.activeElement?.id};'),chrome('return {focus:Services.focus.activeWindow===window,modal:document.documentElement.hasAttribute("window-modal-open"),tab:gBrowser.selectedBrowser.currentURI.spec};'),flush=True)
real_click(native_selector);print('SIGNED_CLICK_RESULT',ui('return window.souluExtensionToolbar.lastError'),flush=True);state=wait(lambda:(lambda s:s if s and s['state']=='open' else False)(popup_state()));check('real_signed_extension_popup_opens',state['id']==signed_id and state['remote'].startswith('extension'),state)
capture_popup('signed-extension-popup.png')
call('browser.extensions.close')
run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");await (await AddonManager.getAddonByID('+json.dumps(signed_id)+')).disable();return true;')
check('disable_removes_action_icon',wait(lambda:ui('return !document.querySelector('+json.dumps(native_selector)+')')))
run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");await (await AddonManager.getAddonByID('+json.dumps(signed_id)+')).enable();return true;')
check('enable_restores_pinned_action',wait(lambda:ui('return !!document.querySelector('+json.dumps(native_selector)+')')))
run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");await (await AddonManager.getAddonByID('+json.dumps(signed_id)+')).uninstall();return true;')
check('signed_addon_uninstall_removes_action',wait(lambda:not any(i['id']==signed_id for i in action_items())))
