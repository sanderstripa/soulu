/* Soul: trusted application chrome. Websites keep Firefox's normal principals. */
(() => {
'use strict';
if (window.Soulu || document.documentURI !== 'chrome://browser/content/browser.xhtml') return;
const Services=window.Services;
const IOUtils=window.IOUtils;
const PathUtils=window.PathUtils;
const {Subprocess}=ChromeUtils.importESModule('resource://gre/modules/Subprocess.sys.mjs');
const {PlacesUtils}=ChromeUtils.importESModule('resource://gre/modules/PlacesUtils.sys.mjs');
const {PrivateBrowsingUtils}=ChromeUtils.importESModule('resource://gre/modules/PrivateBrowsingUtils.sys.mjs');
const profile=PathUtils.profileDir, settingsFile=PathUtils.join(profile,'soulu-settings.json');
const isPrivate=PrivateBrowsingUtils.isWindowPrivate(window);
const defaults={settings:{language:'ru',theme:'system',layout:'adaptive',mattePanel:false,showExtensions:true,homeShowFavorites:true,showSidebar:true,showBack:true,showHome:false,showFavorites:true,showNewTab:true,showDownloads:true,vpnToolbarVisible:true,addressPosition:'center',bookmarksBarMode:'never',bookmarksBarPosition:'hidden',startupMode:'soulu',newTabMode:'soulu',homeMode:'soulu',homeProvider:'google',homeWeatherMode:'automatic',homeWeatherUnits:'celsius',homeFavoriteIds:[],saveHistory:true,historyGroupDays:true,readerTheme:'light',askDownloadLocation:false,freezeBackgroundTabs:false,memorySaver:false,searchEngine:'google',openStartPageAfterLastTab:true,performanceMode:'balanced',backgroundTabTimeout:'300'},rules:{defaults:{geolocation:1,camera:1,microphone:1,notifications:1,sound:0,popups:2,downloads:1},sites:{},blocking:{enabled:true,sites:{}}},vpn:{profiles:[],defaultProfileId:'',directDomains:''},reader:{theme:'light',font:'sans',size:18,width:0,spacing:1.5},profile:PathUtils.filename(profile)};
const {state:shared}=ChromeUtils.importESModule('chrome://soulu/content/shared.sys.mjs');
if(!shared.config)shared.config=structuredClone(defaults);
const windows=()=>[...Services.wm.getEnumerator('navigator:browser')];
const pref=(key,value)=>{if(typeof value==='boolean'){if(Services.prefs.getBoolPref(key,!value)!==value)Services.prefs.setBoolPref(key,value);}else if(typeof value==='number'){if(Services.prefs.getIntPref(key,-999)!==value)Services.prefs.setIntPref(key,value);}else if(Services.prefs.getStringPref(key,'')!==String(value))Services.prefs.setStringPref(key,String(value));};
function emit(name,value){for(const win of windows())win.Soulu?._emit(name,value);}
const builtin={geo:'geolocation',camera:'camera',microphone:'microphone','desktop-notification':'notifications',popup:'popups'};
async function save(){const write=async()=>{if(shared.storageError)throw Error('Encrypted settings could not be unlocked; the original file was preserved. '+shared.storageError);const disk=structuredClone(shared.config);const sdr=Cc['@mozilla.org/security/sdr;1'].getService(Ci.nsISecretDecoderRing);disk.vpn={protected:sdr.encryptString(JSON.stringify(disk.vpn))};await IOUtils.writeJSON(settingsFile,disk,{tmpPath:settingsFile+'.tmp'});await IOUtils.setPermissions(settingsFile,0o600);};const operation=(shared.saveQueue||Promise.resolve()).then(write);shared.saveQueue=operation.catch(()=>{});return operation;}
function layout(){const s=shared.config.settings,root=document.documentElement;root.toggleAttribute('soulu-single',gBrowser.visibleTabs.filter(t=>!t.closing).length<2);root.toggleAttribute('soulu-dark',s.theme==='dark'||s.theme==='system'&&matchMedia('(prefers-color-scheme:dark)').matches);}
function apply(){
 layout();
 document.documentElement.toggleAttribute('soulu-matte',!!shared.config.settings.mattePanel);try{Soulu.material=ChromeUtils.importESModule('chrome://soulu/content/window-controls.sys.mjs').material(window,!!shared.config.settings.mattePanel);}catch(error){Soulu.material={error:String(error)};}
 const s=shared.config.settings,root=document.documentElement;
 root.toggleAttribute('soulu-dark',s.theme==='dark'||s.theme==='system'&&matchMedia('(prefers-color-scheme:dark)').matches);
 root.toggleAttribute('soulu-single',gBrowser.visibleTabs.filter(t=>!t.closing).length<2);
 root.setAttribute('soulu-version','Soul 0.12.0 Preview');
 for(const [id,key] of [['soulu-sidebar','showSidebar'],['back-button','showBack'],['home-button','showHome'],['soulu-newtab','showNewTab'],['downloads-button','showDownloads'],['soulu-vpn','vpnToolbarVisible']]){const el=document.getElementById(id);if(el)el.hidden=s[key]===false;}
 const bar=document.getElementById('PersonalToolbar');if(bar)bar.collapsed=s.bookmarksBarMode==='never'||s.bookmarksBarPosition==='hidden';
 pref('browser.startup.page',s.startupMode==='continue'?3:1);
 pref('browser.startup.homepage',s.homeMode==='custom'?s.homeUrl||'about:blank':s.homeMode==='blank'?'about:blank':ChromeUtils.importESModule('chrome://soulu/content/AppParent.sys.mjs').appRoot()+'home.html');
 const {AboutNewTab}=ChromeUtils.importESModule('resource:///modules/AboutNewTab.sys.mjs');const newTab=s.newTabMode==='custom'?s.newTabUrl||'about:blank':s.newTabMode==='blank'?'about:blank':ChromeUtils.importESModule('chrome://soulu/content/AppParent.sys.mjs').appRoot()+'home.html';if(AboutNewTab.newTabURL!==newTab)AboutNewTab.newTabURL=newTab;
 pref('browser.download.useDownloadDir',!s.askDownloadLocation);if(s.downloadPath){pref('browser.download.dir',s.downloadPath);pref('browser.download.folderList',2);}
 const star=document.getElementById('star-button-box');if(star)star.hidden=s.showFavorites===false;
 root.toggleAttribute('soulu-address-left',s.addressPosition==='left');
 pref('browser.tabs.closeWindowWithLastTab',!s.openStartPageAfterLastTab);
 pref('browser.tabs.unloadOnLowMemory',s.performanceMode!=='performance');pref('places.history.enabled',s.saveHistory!==false);
 pref('browser.bookmarks.showMobileBookmarks',false);
 document.getElementById('PersonalToolbar')?.toggleAttribute('soulu-icons-only',!!s.bookmarksIconsOnly);
 for(const [type,key] of Object.entries(builtin))pref('permissions.default.'+type,({0:1,1:0,2:2})[Number(shared.config.rules.defaults[key]??1)]);
 pref('dom.disable_open_during_load',shared.config.rules.defaults.popups!==0);
 pref('media.autoplay.default',shared.config.rules.defaults.sound===2?5:0);
 for(const entry of shared.managedPermissions||[])if(shared.config.rules.sites[entry.origin]?.[entry.key]===undefined)Services.perms.removeFromPrincipal(entry.principal,entry.type);
 shared.managedPermissions=[];
 for(const [origin,rules] of Object.entries(shared.config.rules.sites)){
  const targets=new Set(origin.includes('://')?[origin]:['http://'+origin,'https://'+origin]);for(const tab of gBrowser.tabs){try{const u=new URL(tab.linkedBrowser.currentURI.spec);if(u.hostname===origin)targets.add(u.origin);}catch{}}
  for(const target of targets){let principal;try{principal=Services.scriptSecurityManager.createContentPrincipal(Services.io.newURI(target),{});}catch{continue;}
  for(const [type,key] of Object.entries(builtin)){if(rules[key]===undefined)continue;const v=Number(rules[key]);shared.managedPermissions.push({origin,key,principal,type});Services.perms.addFromPrincipal(principal,type,v===1?Services.perms.PROMPT_ACTION:v===2?Services.perms.DENY_ACTION:Services.perms.ALLOW_ACTION);}
  }
 }
 pref('privacy.trackingprotection.enabled',false);
 pref('privacy.trackingprotection.pbmode.enabled',false);
 
 pref('layout.css.prefers-color-scheme.content-override',s.theme==='dark'?0:s.theme==='light'?1:2);Soulu.notify?.();
}
function socksPort(){if(!shared.socksPort){const socket=Cc['@mozilla.org/network/server-socket;1'].createInstance(Ci.nsIServerSocket);socket.init(-1,true,-1);shared.socksPort=socket.port;socket.close();}return shared.socksPort;}
async function helperRequest(request){
 const operation=async()=>{
  if(!shared.helper){
   if(Services.appinfo.OS!=='WINNT')throw Error('VPN helper is available in the Windows build');
   const base=Services.dirsvc.get('GreD',Ci.nsIFile).path;
   const env=Subprocess.getEnvironment();env.SOULU_SOCKS_PORT=String(socksPort());env.SOULU_VPN_ROOT=PathUtils.join(profile,'soulu-vpn');
   shared.helper=await Subprocess.call({command:PathUtils.join(base,'soulu','vpn','SouluVpnHost.exe'),arguments:[],environment:env,stderr:'pipe'});
  }
  const bytes=new TextEncoder().encode(JSON.stringify(request));const header=new Uint8Array(4);new DataView(header.buffer).setUint32(0,bytes.length,true);
  await shared.helper.stdin.write(header.buffer);await shared.helper.stdin.write(bytes.buffer);
  const head=await shared.helper.stdout.read(4);if(head.byteLength!==4)throw Error('VPN helper closed');
  const n=new DataView(head).getUint32(0,true);if(n===0||n>1048576)throw Error('Invalid VPN helper response');
  const chunks=[];let remaining=n;while(remaining){const chunk=await shared.helper.stdout.read(remaining);if(!chunk.byteLength)throw Error('Truncated VPN helper response');chunks.push(new Uint8Array(chunk));remaining-=chunk.byteLength;}
  const buffer=new Uint8Array(n);let offset=0;for(const chunk of chunks){buffer.set(chunk,offset);offset+=chunk.length;}
  const result=JSON.parse(new TextDecoder().decode(buffer));if(result.ok===false)throw Error(result.error);return result;
 };
 const promise=shared.helperQueue.then(operation);shared.helperQueue=promise.catch(()=>{});return promise;
}
function proxy(enabled){
 const changed=shared.proxyEnabled!==enabled,previous=shared.proxyEnabled;if(changed){Soulu.adblock?.abortUpdate?.();shared.proxyEnabled=enabled;}
 // SOCKS DNS and no direct fallback: core failure leaves browser traffic blocked.
 pref('network.proxy.socks','127.0.0.1');pref('network.proxy.socks_port',enabled?socksPort():(shared.socksPort||17890));pref('network.proxy.socks_version',5);
 pref('network.proxy.socks_remote_dns',true);pref('network.proxy.failover_direct',false);
 pref('network.proxy.no_proxies_on',shared.config.vpn.directDomains.split(/[\s,]+/).filter(Boolean).join(','));
 if(enabled)shared.networkBeforeVPN??={trr:Services.prefs.getIntPref('network.trr.mode',0),rtc:Services.prefs.getBoolPref('media.peerconnection.enabled',true)};
 pref('network.trr.mode',enabled?5:(shared.networkBeforeVPN?.trr??Services.prefs.getIntPref('network.trr.mode',0)));pref('media.peerconnection.ice.proxy_only_if_behind_proxy',true);
 pref('media.peerconnection.enabled',enabled?false:(shared.networkBeforeVPN?.rtc??Services.prefs.getBoolPref('media.peerconnection.enabled',true)));pref('network.proxy.type',enabled?1:0);if(!enabled)shared.networkBeforeVPN=null;if(changed&&previous!==undefined){Services.obs.notifyObservers(null,'net:cancel-all-connections');Services.dns.clearCache(true);if(!Services.io.offline){Services.io.offline=true;Services.io.offline=false;}}
}
async function vpn(action){
 if(isPrivate)throw Error('Изменение VPN доступно из обычного окна профиля.');
 if(action==='status'){if(shared.vpnState.connected&&shared.helper){try{const result=await helperRequest({action:'status'});if(!result.connected)shared.vpnState={state:'error',connected:false,error:'VPN остановлен. Соединение заблокировано до отключения VPN.'};}catch(error){shared.vpnState={state:'error',connected:false,error:String(error)};}emit('vpnState',shared.vpnState);paintVPN();}return shared.vpnState;}
 if(action==='disconnect'){
  await helperRequest({action:'disconnect'});proxy(false);await IOUtils.remove(PathUtils.join(profile,'soulu-network-before-vpn.json'),{ignoreAbsent:true});shared.vpnState={ok:true,state:'disconnected',connected:false};
 }else if(action==='connect'){
  const selected=shared.config.vpn.profiles.find(p=>p.id===shared.config.vpn.defaultProfileId);if(!selected)throw Error('Добавьте и выберите ключ в Настройки → VPN.');
  shared.networkBeforeVPN??={trr:Services.prefs.getIntPref('network.trr.mode',0),rtc:Services.prefs.getBoolPref('media.peerconnection.enabled',true)};await IOUtils.writeJSON(PathUtils.join(profile,'soulu-network-before-vpn.json'),shared.networkBeforeVPN);
  proxy(true);shared.vpnState={state:'connecting',connected:false};emit('vpnState',shared.vpnState);
  try{const result=await helperRequest({action:'connect',url:selected.link,profileId:selected.id});shared.vpnState={...result,state:'connected'};}
  catch(error){shared.vpnState={state:'error',connected:false,error:error.message};emit('vpnState',shared.vpnState);paintVPN();throw error;}
 }else throw Error('Unsupported VPN operation');
 emit('vpnState',shared.vpnState);paintVPN();return shared.vpnState;
}
function paintVPN(){for(const win of windows()){const b=win.document.getElementById('soulu-vpn');b?.toggleAttribute('connected',shared.vpnState.connected);b?.toggleAttribute('blocked',shared.vpnState.state==='error');b?.setAttribute('tooltiptext',shared.vpnState.error||'VPN · '+shared.vpnState.state);}}
function open(url){
 const uri=Services.io.newURI(url);if(!['http','https','about'].includes(uri.scheme))throw Error('Unsupported navigation scheme');
 openTrustedLinkIn(url,'tab');return true;
}
function settings(){if(shared.settingsWindow&&!shared.settingsWindow.closed){shared.settingsWindow.focus();return;}shared.settingsWindow=window.openDialog('chrome://soulu/content/ui/settings.html','soulu-settings','chrome,dialog=no,resizable,centerscreen,width=1060,height=760');}
function tabRows(){return gBrowser.tabs.map((t,id)=>({id,title:t.label,url:t.linkedBrowser.currentURI.spec,incognito:isPrivate}));}
async function bookmarks(){const rows=[];const tree=await PlacesUtils.promiseBookmarksTree(PlacesUtils.bookmarks.rootGuid);function walk(node){for(const n of node.children||[]){if(n.uri)rows.push({id:n.guid,title:n.title||n.uri,url:n.uri});walk(n);}}walk(tree);return rows;}
async function state(){const dirs=await IOUtils.getChildren(PathUtils.parent(profile));const profiles=[];for(const path of dirs){if((await IOUtils.stat(path)).type!=='directory')continue;let name=PathUtils.filename(path);try{name=(await IOUtils.readJSON(PathUtils.join(path,'soulu-profile.json'))).name;}catch{}profiles.push({id:PathUtils.filename(path),name,active:path===profile});}return {settings:shared.config.settings,profiles,activeProfileId:shared.config.profile,tabs:tabRows(),capabilities:{matteAvailable:Soulu.material?.native===true},update:{soulu:'Gecko Preview 11',gecko:Services.appinfo.platformVersion,firefox:Services.appinfo.version,xray:Soulu.components?.xray?.version||'—',sudoku:Soulu.components?.sudoku?.version||'—',adblock:'adblock-rust 0.13.3'}};}
function validate(next){
 if(next.profile!==shared.config.profile)throw Error('Profile changed');
 if(!['system','light','dark'].includes(next.settings.theme))throw Error('Invalid theme');
 next.settings.layout='adaptive';
 for(const key of ['startupUrl','newTabUrl','homeUrl'])if(next.settings[key]){const u=new URL(next.settings[key]);if(!['http:','https:'].includes(u.protocol))throw Error('Only HTTP/HTTPS page addresses are supported');}
 for(const row of next.vpn.profiles||[])if(typeof row.link!=='string'||row.link.length>16384||!/^vless:\/\/|^sudoku:\/\//.test(row.link))throw Error('Invalid VPN key');
 if(JSON.stringify(next).length>1048576)throw Error('Settings too large');return structuredClone(next);
}
let settingsBaseline=null;
async function dispatch(action,payload,source){
 switch(action){
 case 'settings.begin':settingsBaseline=structuredClone(shared.config);return structuredClone(shared.config);
 case 'settings.capabilities':return {matteAvailable:Soulu.material?.native===true,defaultBrowser:ChromeUtils.importESModule('chrome://soulu/content/window-controls.sys.mjs').isDefault()};
 case 'settings.ready':return true;
 case 'settings.save':{if(settingsBaseline&&JSON.stringify(payload.settings?.homeFavoriteIds)===JSON.stringify(settingsBaseline.settings.homeFavoriteIds))payload={...payload,settings:{...payload.settings,homeFavoriteIds:shared.config.settings.homeFavoriteIds}};const next=validate({...payload,onboarding:shared.config.onboarding,bookmarkIds:shared.config.bookmarkIds||{}}),old=shared.config;shared.config=next;try{
 if(next.settings.searchEngine!==old.settings.searchEngine){await Services.search.init();const names={google:'Google',yandex:'Яндекс',bing:'Bing',duckduckgo:'DuckDuckGo'};const engines=await Services.search.getVisibleEngines();const engine=engines.find(e=>e.name.toLowerCase().includes(names[next.settings.searchEngine]?.toLowerCase()));if(!engine)throw Error('Поисковая система недоступна в этой локализации Soulu.');await Services.search.setDefault(engine,Services.search.CHANGE_REASON_USER);}await save();for(const w of windows())w.Soulu?.refresh();if(shared.vpnState.connected)proxy(true);emit('settings',shared.config.settings);settingsBaseline=structuredClone(shared.config);return {ok:true,persisted:structuredClone(shared.config)};}catch(error){shared.config=old;return {ok:false,error:error.message,persisted:structuredClone(shared.config)};}}
 case 'settings.close':source?.close();return true;
 case 'settings.resize':case 'settings.extensions':return true;
 case 'settings.geckoSiteSettings':return Soulu.settings('sites');
 case 'settings.geckoAdblockSettings':return Soulu.settings('extensions');
 case 'settings.geckoTranslation':return Soulu.settings('sites');
 case 'settings.geckoExtensions':return Soulu.settings('extensions');
 case 'settings.geckoExtensionStore':return open('https://addons.mozilla.org/firefox/');
 case 'settings.geckoReader':document.getElementById('reader-mode-button')?.click();return true;
 case 'settings.openFolder':{const file=Services.dirsvc.get('DfltDwnld',Ci.nsIFile);file.launch();return true;}
 case 'settings.defaultBrowser':{if(Services.appinfo.OS!=='WINNT')throw Error('Требуется Windows.');if(!source?.gesture||Date.now()-source.gesture.at>2000)throw Error('Нажмите кнопку назначения браузера.');const command=PathUtils.join(Services.dirsvc.get('GreD',Ci.nsIFile).parent.path,'Soul.exe');const task=await Subprocess.call({command,arguments:['--register-default','--profile',shared.config.profile],stdout:'pipe',stderr:'pipe'});const result=await task.wait();if(result.exitCode)throw Error('Не удалось зарегистрировать Soulu.');return {ok:true};}
 case 'settings.chooseFolder':{const picker=Cc['@mozilla.org/filepicker;1'].createInstance(Ci.nsIFilePicker);picker.init(window.browsingContext,'Загрузки',Ci.nsIFilePicker.modeGetFolder);return new Promise(resolve=>picker.open(result=>resolve(result===Ci.nsIFilePicker.returnOK?picker.file.path:'')));}
 case 'browser.state.get':return state();
 case 'browser.settings.get':return shared.config.settings;
 case 'browser.settings.openWindow':settings();return true;
 case 'browser.openTab':return open(payload.url);
 case 'browser.newIncognito':OpenBrowserWindow({private:true});return true;
 case 'browser.history.open':if(payload)Sanitizer.showUI(window);else PlacesCommandHook.showPlacesOrganizer('History');return true;
 case 'browser.bookmarks.get':return bookmarks();
 case 'browser.bookmarks.add':await PlacesCommandHook.bookmarkPage();return true;
 case 'browser.bookmarks.remove':await PlacesUtils.bookmarks.remove(payload);return bookmarks();
 case 'browser.bookmarks.open':return open(payload);
 case 'browser.sites.get':return shared.config.rules;
 case 'browser.sites.blocking':shared.config.rules.blocking.enabled=!!payload;await save();apply();return shared.config.rules;
 case 'browser.profile.create':{const id=Services.uuid.generateUUID().toString().replace(/[{}]/g,'');const path=PathUtils.join(PathUtils.parent(profile),id);await IOUtils.makeDirectory(path,{permissions:0o700});await IOUtils.writeJSON(PathUtils.join(path,'soulu-profile.json'),{name:String(payload).slice(0,160)});return {id};}
 case 'browser.profile.switch':{
  if(!/^[\w-]{1,64}$/.test(payload))throw Error('Invalid profile');
  const base=Services.dirsvc.get('GreD',Ci.nsIFile).parent;base.append('Soul.exe');
  const proc=Cc['@mozilla.org/process/util;1'].createInstance(Ci.nsIProcess);proc.init(base);proc.runw(false,['--profile',payload],2);return true;}
 case 'browser.profile.delete':if(payload===shared.config.profile||!/^[\w-]{1,64}$/.test(payload))throw Error('Cannot delete active profile');await IOUtils.remove(PathUtils.join(PathUtils.parent(profile),payload),{recursive:true});return true;
 case 'vpn.send':return vpn(payload.action);
 case 'vpn.settings.get':return shared.config.vpn;
 case 'browser.components.manage':{if(!['xray','sudoku'].includes(payload?.component)||!['status','list','install','rollback'].includes(payload?.operation))throw Error('Invalid VPN component operation');return helperRequest({...payload,action:'components',name:payload.operation,proxy:shared.proxyEnabled===true});}
 case 'browser.extensions.list':{const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');return {items:(await AddonManager.getAddonsByTypes(['extension'])).map(a=>({id:a.id,name:a.name,version:a.version,enabled:a.isActive,action:false}))};}
 case 'browser.extensions.manager':return Soulu.settings('extensions');
 case 'browser.extensions.openStore':return open('https://addons.mozilla.org/firefox/');
 case 'browser.performance.optimize':open('about:unloads');return {ok:true};
 case 'browser.passwords.get':return Soulu.settings('passwords');
 case 'browser.import.native':throw Error('Мастер импорта ещё загружается. Повторите через секунду.');
 case 'browser.import.sources':case 'browser.import.browsers':return Soulu.dispatch('browser.import.native',null,source);
 default:throw Error('Эта функция ещё не перенесена в Gecko Preview 4: '+action);
 }
}
window.Soulu={dispatch,settings,refresh:apply,get config(){return shared.config;},get vpnState(){return shared.vpnState;},_emit(name,value){if(shared.settingsWindow&&!shared.settingsWindow.closed)shared.settingsWindow.__souluEmit?.(name,value);},ready:false};
function button(id,label,command){const b=document.createXULElement('toolbarbutton');b.id=id;b.className='toolbarbutton-1 chromeclass-toolbar-additional';b.setAttribute('label',label);b.setAttribute('tooltiptext',label);b.addEventListener('command',command);return b;}
async function initialize(){
 const began=performance.now();Soulu.startupTimings={initializeWindowAge:Math.round(began)};const timing=name=>Soulu.startupTimings[name]=Math.round(performance.now()-began);
 if(!shared.initialized){shared.isNewProfile=!(await IOUtils.exists(settingsFile));if(shared.isNewProfile){try{const choice=await IOUtils.readJSON(PathUtils.join(PathUtils.parent(PathUtils.parent(profile)),'install-preferences.json'));if(['ru','en'].includes(choice.language))defaults.settings.language=shared.config.settings.language=choice.language;if(['light','dark'].includes(choice.theme))defaults.settings.theme=shared.config.settings.theme=choice.theme;}catch{}}try{const stored=await IOUtils.readJSON(settingsFile);if(stored.vpn?.protected)stored.vpn=JSON.parse(Cc['@mozilla.org/security/sdr;1'].getService(Ci.nsISecretDecoderRing).decryptString(stored.vpn.protected));shared.config={...defaults,...stored,settings:{...defaults.settings,...stored.settings},rules:{...defaults.rules,...stored.rules},vpn:{...defaults.vpn,...stored.vpn}};}catch(error){if(await IOUtils.exists(settingsFile)){shared.storageError=String(error);console.error('Soulu settings preserved:',error);}}try{shared.networkBeforeVPN=await IOUtils.readJSON(PathUtils.join(profile,'soulu-network-before-vpn.json'));}catch{}proxy(false);await IOUtils.remove(PathUtils.join(profile,'soulu-network-before-vpn.json'),{ignoreAbsent:true});shared.initialized=true;}
 shared.config.settings.layout='adaptive';
 Soulu.backend={shared,Services,IOUtils,PathUtils,PlacesUtils,profile,isPrivate,save,apply};
 layout();timing('settings');
 Services.scriptloader.loadSubScript('chrome://soulu/content/storage.js',window);
 Services.scriptloader.loadSubScript('chrome://soulu/content/shell-host.js',window);
 Services.scriptloader.loadSubScript('chrome://soulu/content/weather.js',window);
 // Native filter compilation is synchronous FFI even inside an async method.
 // Start it after the first real Soulu frame has been presented, not during
 // backend initialization while the window is hidden.
 window.addEventListener('SouluPresented',()=>{window.setTimeout(async()=>{
 try{const {adblock}=ChromeUtils.importESModule('chrome://soulu/content/adblock.sys.mjs');Soulu.adblock=adblock;await adblock.initialize(shared,profile);if(!shared.blockerUpdateScheduled){shared.blockerUpdateScheduled=true;setTimeout(()=>adblock.scheduleUpdate(),15000);}}catch(error){Soulu.blockerError=String(error);console.error(error);}
 },0);},{once:true});
 timing('adblock');
 window.addEventListener('unload',()=>{if(windows().filter(w=>w!==window&&!w.closed).length===0&&shared.helper){shared.helper.stdin.close();shared.helper=null;}},{once:true});
 try{Soulu.components=await IOUtils.readJSON(PathUtils.join(Services.dirsvc.get('GreD',Ci.nsIFile).path,'soulu','vpn','components.json'));}catch{}
 Services.scriptloader.loadSubScript('chrome://soulu/content/translations.js',window);
 const nativeWindow=ChromeUtils.importESModule('chrome://soulu/content/window-controls.sys.mjs');try{nativeWindow.brand(window);}catch(error){console.error(error);}
 await save();apply();timing('applied');
 Services.scriptloader.loadSubScript('chrome://soulu/content/integration.js',window);
 Services.scriptloader.loadSubScript('chrome://soulu/content/page-glass.js',window);
 Services.scriptloader.loadSubScript('chrome://soulu/content/settings-routing.js',window);
 window.Soulu.ready=true;timing('ready');window.dispatchEvent(new Event('SouluBackendReady'));
}
initialize().catch(console.error);
})();

