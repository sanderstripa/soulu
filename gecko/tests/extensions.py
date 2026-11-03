"""Native WebExtensions integration against real Gecko; signatures stay enabled."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
import zipfile,io
from PIL import Image
report={'passed':False,'scope':'Native extension action integration','checks':{},'limitations':[]}
fixture_id='soulu-action-fixture@example.test'
click_id='soulu-click-fixture@example.test'
def fixture(path,id,popup=True):
 image=io.BytesIO();Image.new('RGBA',(32,32),(65,130,232,255)).save(image,format='PNG')
 manifest={'manifest_version':3,'name':'Soulu extension fixture','version':'1.0','browser_specific_settings':{'gecko':{'id':id}},'permissions':['activeTab','scripting','storage'],'background':{'scripts':['background.js']},'action':{'default_icon':{'32':'icon.png'},'default_title':'Fixture action'}}
 if popup:manifest['action']['default_popup']='popup.html'
 background='browser.action.onClicked.addListener(async tab=>{await browser.scripting.executeScript({target:{tabId:tab.id},func:()=>document.documentElement.dataset.souluExtensionClicked="yes"});await browser.action.setBadgeText({text:"C"});});'
 popup_js='browser.action.setBadgeText({text:"A"});document.getElementById("apply").onclick=async()=>{const [tab]=await browser.tabs.query({active:true,currentWindow:true});await browser.scripting.executeScript({target:{tabId:tab.id},func:()=>document.documentElement.dataset.souluExtensionPopup="yes"});await browser.storage.local.set({worked:true});await browser.action.setBadgeText({text:"B"});document.getElementById("result").textContent="done";};'
 with zipfile.ZipFile(path,'w') as z:
  z.writestr('manifest.json',json.dumps(manifest));z.writestr('background.js',background);z.writestr('icon.png',image.getvalue());z.writestr('popup.html','<!doctype html><meta charset=utf-8><title>Fixture popup</title><link rel=stylesheet href=popup.css><button id=apply>Apply to active tab</button><p id=result>ready</p><script src=popup.js></script>');z.writestr('popup.js',popup_js);z.writestr('popup.css','body{width:260px;min-height:120px;background:#fff;color:#111;font:14px sans-serif}button{padding:12px}')
def install(path):return run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");const file=Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);file.initWithPath('+json.dumps(str(path))+');const addon=await AddonManager.installTemporaryAddon(file);return addon.id;')
def action_items():return call('browser.extensions.list',{'profile':'default'})['items']
def real_click(selector):
 rect=ui('const r=document.querySelector('+json.dumps(selector)+').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};')
 m.set_context('chrome');m._send_message('WebDriver:PerformActions',{'actions':[{'type':'pointer','id':'soulu-native-mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport','x':round(rect['x']),'y':round(rect['y']),'duration':0},{'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
def popup_state():return chrome('const panel=document.querySelector("panel[data-soulu-extension]");return panel?{id:panel.dataset.souluExtension,state:panel.state,url:panel.querySelector("browser")?.currentURI.spec,remote:panel.querySelector("browser")?.remoteType,rect:(()=>{const r=panel.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})()}:null')
try:
 start();print('NATIVE_GUARD',chrome('return {guard:typeof ExtensionGuardSet,api:typeof WebExtensionPolicy.getActiveExtensions}'),flush=True);check('native_extension_module_loaded',chrome('return !!Soulu.extensions'))
 check('signature_enforcement_retained',chrome('return Services.prefs.getBoolPref("xpinstall.signatures.required",true)'))
 call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 path=root/'popup.xpi';fixture(path,fixture_id);check('temporary_native_fixture_installed',install(path)==fixture_id)
 row=wait(lambda:next((i for i in action_items() if i['id']==fixture_id and i['action']),None));check('native_action_and_local_icon',row['enabled'] and row['icon'].startswith('data:image/png'),row['id'])
 call('browser.extensions.pin',{'profile':'default','id':fixture_id,'pinned':True});selector='[data-extension-toolbar="classic"] [data-extension-id="'+fixture_id+'"]'
 check('original_soulu_action_slot',wait(lambda:ui('return !!document.querySelector('+json.dumps(selector)+')')))
 before=content('return {height:innerHeight,width:innerWidth,identity:document.documentElement.dataset.identity}')
 real_click(selector);state=wait(lambda:(lambda s:s if s and s['state']=='open' else False)(popup_state()));check('real_native_popup_in_extension_process',state['url'].startswith('moz-extension:') and state['remote'].startswith('extension'),state)
 # The fixture popup runs in Firefox's extension process. A test-only frame
 # script clicks its real DOM control; no test actor or evaluator is shipped.
 applied=run('const browser=document.querySelector("panel[data-soulu-extension] browser");if(!browser?.currentURI.spec.startsWith("moz-extension:"))throw Error("Not a fixture popup");return await new Promise((resolve,reject)=>{const mm=browser.messageManager,listener=m=>{mm.removeMessageListener("SouluFixtureClick",listener);resolve(m.data);};mm.addMessageListener("SouluFixtureClick",listener);mm.loadFrameScript("data:application/javascript,"+encodeURIComponent(`content.document.getElementById("apply").click();sendAsyncMessage("SouluFixtureClick",true);`),false);});')
 check('popup_action_changes_real_active_tab',applied and wait(lambda:content('return document.documentElement.dataset.souluExtensionPopup==="yes"')))
 check('native_badge_updates_without_polling',wait(lambda:ui('return document.querySelector('+json.dumps(selector)+')?.textContent.includes("B")')))
 after=content('return {height:innerHeight,width:innerWidth,identity:document.documentElement.dataset.identity}');check('popup_does_not_resize_or_reload_page',before==after)
 (out/'extension-popup.png').write_bytes(base64.b64decode(m.screenshot()))
 call('browser.extensions.close');wait(lambda:not popup_state())
 # A stale/programmatic UI request cannot mint an activeTab grant.
 time.sleep(2.1)
 denied=ui('try{await browserShell.extensions("open",{profile:"default",id:'+json.dumps(fixture_id)+',tabId:0,generation:0,anchor:{x:10,y:10,width:32,height:32}});return false;}catch(e){return e.message.includes("Нажмите");}')
 check('programmatic_action_without_recent_user_input_rejected',denied)
 path2=root/'clicked.xpi';fixture(path2,click_id,False);install(path2);wait(lambda:any(i['id']==click_id and i['action'] for i in action_items()));call('browser.extensions.pin',{'profile':'default','id':click_id,'pinned':True})
 second='[data-extension-toolbar="classic"] [data-extension-id="'+click_id+'"]';wait(lambda:ui('return !!document.querySelector('+json.dumps(second)+')'));real_click(second)
 check('native_onclicked_and_active_tab_permission',wait(lambda:content('return document.documentElement.dataset.souluExtensionClicked==="yes"')))
 check('onclick_does_not_open_empty_popup',not popup_state())
 known=set(m.window_handles);normal=m.current_window_handle;call('browser.newIncognito');wait(lambda:len(m.window_handles)>len(known));m.switch_to_window(next(h for h in m.window_handles if h not in known));wait(lambda:chrome('return !!Soulu?.ready'))
 check('private_window_hides_disallowed_extensions',not any(i['id'] in [fixture_id,click_id] for i in action_items()))
 chrome('window.close()');m.switch_to_window(normal)
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady']);ui('souluSettings.openSection("extensions");return true;','settings')
 pinSelector='#extensionPins input[data-extension-id="'+fixture_id+'"]'
 check('original_settings_pin_controls',wait(lambda:ui('return !!document.querySelector('+json.dumps(pinSelector)+')','settings')))
 pinSelector='#extensionPins input[data-extension-id="'+fixture_id+'"]'
 ui('document.querySelector('+json.dumps(pinSelector)+').click();return true;','settings')
 check('settings_unpin_changes_native_placement',wait(lambda:next(i for i in action_items() if i['id']==fixture_id)['pinned']==False))
 chrome('Soulu.closeSettings()');time.sleep(.25)
 check('unpin_removes_soulu_icon',wait(lambda:ui('return !document.querySelector('+json.dumps(selector)+')')))
 call('browser.extensions.pin',{'profile':'default','id':fixture_id,'pinned':True})
 for id in [fixture_id,click_id]:run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");await (await AddonManager.getAddonByID('+json.dumps(id)+')).uninstall();return true;')
 check('uninstall_removes_action_and_observers',wait(lambda:not any(i['id'] in [fixture_id,click_id] for i in action_items())) and wait(lambda:ui('return !document.querySelector("[data-extension-id]")')))
 # A file-enabled add-on must still be unable to inject into Soulu UI.
 guarded='soulu-file-fixture@example.test';guardpath=root/'guarded.xpi'
 manifest={'manifest_version':2,'name':'File injection fixture','version':'1.0','applications':{'gecko':{'id':guarded}},'permissions':['<all_urls>','tabs','activeTab'],'browser_action':{'default_title':'File guard probe'},'background':{'scripts':['guard-background.js']},'content_scripts':[{'matches':['<all_urls>'],'js':['guard-content.js'],'all_frames':True,'run_at':'document_start'}]}
 background='browser.browserAction.onClicked.addListener(async tab=>{try{await browser.tabs.executeScript(tab.id,{code:"document.documentElement.dataset.souluDynamicInjection=1"});await browser.browserAction.setBadgeText({text:"UNSAFE"});}catch(error){await browser.browserAction.setBadgeText({text:"DENIED"});}});'
 with zipfile.ZipFile(guardpath,'w') as z:
  z.writestr('manifest.json',json.dumps(manifest));z.writestr('guard-background.js',background);z.writestr('guard-content.js','document.documentElement.dataset.souluStaticInjection="yes";')
 run('const {ExtensionPermissions}=ChromeUtils.importESModule("resource://gre/modules/ExtensionPermissions.sys.mjs");await ExtensionPermissions.add('+json.dumps(guarded)+',{permissions:["internal:fileSchemeAllowed"],origins:[]});return true;')
 install(guardpath);wait(lambda:any(i['id']==guarded and i['action'] for i in action_items()))
 protected=chrome('const p=WebExtensionPolicy.getByID('+json.dumps(guarded)+');const {appRoot}=ChromeUtils.importESModule("chrome://soulu/content/AppParent.sys.mjs");return {fileAllowed:p.fileSchemeAllowed,guard:p.checkGuarded(Services.io.newURI(appRoot()+"home.html"))};')
 check('native_guard_survives_explicit_file_permission',protected['fileAllowed'] and protected['guard'] is not None,protected)
 call('browser.navigate',url+'extension-positive-control');wait(lambda:content('return document.documentElement.dataset.souluStaticInjection==="yes"'))
 check('extension_content_scripts_still_work_on_websites',True)
 call('browser.home');wait(lambda:ui('return !!window.souluHomeApply','page'))
 check('static_extension_script_cannot_reach_app_document',ui('return !document.documentElement.dataset.souluStaticInjection','page'))
 call('browser.extensions.pin',{'profile':'default','id':guarded,'pinned':True});guardselector='[data-extension-toolbar="classic"] [data-extension-id="'+guarded+'"]';wait(lambda:ui('return !!document.querySelector('+json.dumps(guardselector)+')'));real_click(guardselector)
 check('dynamic_extension_injection_into_app_document_denied',wait(lambda:next(i for i in action_items() if i['id']==guarded)['badge']=='DENIED'))
 check('app_bridge_not_escalated_by_extension',ui('return !document.documentElement.dataset.souluDynamicInjection','page'))
 run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");await (await AddonManager.getAddonByID('+json.dumps(guarded)+')).uninstall();return true;')
 if os.name=='nt':
  exec(compile(Path(__file__).with_name('extensions-signed.py').read_text(encoding='utf-8'),str(Path(__file__).with_name('extensions-signed.py')),'exec'),globals())
 report['passed']=True
except Exception as error:
 report['error']=str(error)
 import traceback;report['traceback']=traceback.format_exc()
 try:
  report['diagnostic']=chrome('return {ready:Soulu?.ready,popup:!!document.querySelector("panel[data-soulu-extension]"),errors:Services.console.getMessageArray().map(m=>m.message).filter(s=>/soulu|Error|xtension/.test(s)).slice(-25)}')
  (out/'extension-failure.png').write_bytes(base64.b64decode(m.screenshot()))
 except Exception:pass
 raise
finally:
 stop();server.shutdown();log.close();(out/'extensions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
