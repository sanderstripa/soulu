/* Sona: trusted application chrome. Websites keep Firefox's normal principals. */
(() => {
'use strict';
if (window.Sona || document.documentURI !== 'chrome://browser/content/browser.xhtml') return;
const Services=window.Services;
const {resolveTheme}=ChromeUtils.importESModule('chrome://sona/content/theme.sys.mjs');
const IOUtils=window.IOUtils;
const PathUtils=window.PathUtils;
const {Subprocess}=ChromeUtils.importESModule('resource://gre/modules/Subprocess.sys.mjs');
const {PlacesUtils}=ChromeUtils.importESModule('resource://gre/modules/PlacesUtils.sys.mjs');
const {PrivateBrowsingUtils}=ChromeUtils.importESModule('resource://gre/modules/PrivateBrowsingUtils.sys.mjs');
const profile=PathUtils.profileDir, settingsFile=PathUtils.join(profile,'sona-settings.json');
const isPrivate=PrivateBrowsingUtils.isWindowPrivate(window);
const defaults={settings:{language:'ru',theme:'system',layout:'adaptive',mattePanel:false,showExtensions:false,homeShowFavorites:true,homeShowLogo:true,showSidebar:true,showBack:true,showHome:false,showFavorites:true,showNewTab:true,showDownloads:true,vpnToolbarVisible:false,addressPosition:'center',bookmarksBarMode:'never',bookmarksBarPosition:'hidden',startupMode:'sona',newTabMode:'sona',homeMode:'sona',homeProvider:'google',homeWeatherMode:'automatic',homeWeatherUnits:'celsius',homeFavoriteIds:[],saveHistory:true,historyGroupDays:true,readerTheme:'light',askDownloadLocation:false,freezeBackgroundTabs:false,memorySaver:false,searchEngine:'google',openStartPageAfterLastTab:true,performanceMode:'balanced',backgroundTabTimeout:'300'},rules:{defaults:{geolocation:1,camera:1,microphone:1,notifications:1,sound:0,popups:2,downloads:1},sites:{},blocking:{enabled:true,sites:{}}},vpn:{profiles:[],defaultProfileId:'',directDomains:''},reader:{theme:'light',font:'sans',size:18,width:0,spacing:1.5},profile:PathUtils.filename(profile)};
const {state:shared}=ChromeUtils.importESModule('chrome://sona/content/shared.sys.mjs');
if(!shared.config)shared.config=structuredClone(defaults);
const windows=()=>[...Services.wm.getEnumerator('navigator:browser')];
const pref=(key,value)=>{if(typeof value==='boolean'){if(Services.prefs.getBoolPref(key,!value)!==value)Services.prefs.setBoolPref(key,value);}else if(typeof value==='number'){if(Services.prefs.getIntPref(key,-999)!==value)Services.prefs.setIntPref(key,value);}else if(Services.prefs.getStringPref(key,'')!==String(value))Services.prefs.setStringPref(key,String(value));};
function emit(name,value){for(const win of windows())win.Sona?._emit(name,value);}
const builtin={geo:'geolocation',camera:'camera',microphone:'microphone','desktop-notification':'notifications',popup:'popups'};
// SDR accepts bytes, so JSON must be ASCII escaped before encryption.
function vpnJSON(value){return JSON.stringify(value).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));}
function readVPNJSON(text){
 try{return {value:JSON.parse(text),repaired:false};}catch(original){
  // Legacy SDR truncated Unicode code points to bytes. Escape only literal
  // controls inside strings; never rewrite JSON structure or discard keys.
  let quoted=false,escaped=false,fixed='';
  for(const c of text){if(quoted&&c.charCodeAt(0)<32){fixed+='\\u'+c.charCodeAt(0).toString(16).padStart(4,'0');escaped=false;continue;}fixed+=c;if(escaped){escaped=false;continue;}if(quoted&&c==='\\'){escaped=true;continue;}if(c==='"')quoted=!quoted;}
  if(fixed===text)throw original;
  return {value:JSON.parse(fixed),repaired:true};
 }
}
async function save(){const write=async()=>{if(shared.storageError)throw Error('Encrypted settings could not be unlocked; the original file was preserved. '+shared.storageError);const disk=structuredClone(shared.config);const sdr=Cc['@mozilla.org/security/sdr;1'].getService(Ci.nsISecretDecoderRing);if(shared.lockedVPN){if(JSON.stringify(disk.vpn)!==shared.lockedVPNBaseline)throw Error('Не удалось восстановить сохранённые VPN-ключи. Исходные данные сохранены; импортируйте ключи из резервной копии.');disk.vpn=shared.lockedVPN;}else disk.vpn={protected:sdr.encryptString(vpnJSON(disk.vpn))};await IOUtils.writeJSON(settingsFile,disk,{tmpPath:settingsFile+'.tmp'});await IOUtils.setPermissions(settingsFile,0o600);};const operation=(shared.saveQueue||Promise.resolve()).then(write);shared.saveQueue=operation.catch(()=>{});return operation;}
function layout(){const s=shared.config.settings,root=document.documentElement;root.toggleAttribute('sona-single',gBrowser.visibleTabs.filter(t=>!t.closing).length<2);root.toggleAttribute('sona-dark',resolveTheme(s.theme)==='dark');}
function apply(){
 layout();
 document.documentElement.toggleAttribute('sona-matte',!!shared.config.settings.mattePanel);try{Sona.material=ChromeUtils.importESModule('chrome://sona/content/window-controls.sys.mjs').material(window,!!shared.config.settings.mattePanel);}catch(error){Sona.material={error:String(error)};}
 const s=shared.config.settings,root=document.documentElement;
 root.toggleAttribute('sona-dark',resolveTheme(s.theme)==='dark');
 root.toggleAttribute('sona-single',gBrowser.visibleTabs.filter(t=>!t.closing).length<2);
 root.setAttribute('sona-version','Sona 0.13.0 Preview');
 for(const [id,key] of [['sona-sidebar','showSidebar'],['back-button','showBack'],['home-button','showHome'],['sona-newtab','showNewTab'],['downloads-button','showDownloads'],['sona-vpn','vpnToolbarVisible']]){const el=document.getElementById(id);if(el)el.hidden=s[key]===false;}
 const bar=document.getElementById('PersonalToolbar');if(bar)bar.collapsed=s.bookmarksBarMode==='never'||s.bookmarksBarPosition==='hidden';
 pref('browser.startup.page',s.startupMode==='continue'?3:1);
 pref('browser.startup.homepage',s.homeMode==='custom'?s.homeUrl||'about:blank':s.homeMode==='blank'?'about:blank':ChromeUtils.importESModule('chrome://sona/content/AppParent.sys.mjs').appRoot()+'home.html');
 const {AboutNewTab}=ChromeUtils.importESModule('resource:///modules/AboutNewTab.sys.mjs');const newTab=s.newTabMode==='custom'?s.newTabUrl||'about:blank':s.newTabMode==='blank'?'about:blank':ChromeUtils.importESModule('chrome://sona/content/AppParent.sys.mjs').appRoot()+'home.html';if(AboutNewTab.newTabURL!==newTab)AboutNewTab.newTabURL=newTab;
 pref('browser.download.useDownloadDir',!s.askDownloadLocation);if(s.downloadPath){pref('browser.download.dir',s.downloadPath);pref('browser.download.folderList',2);}
 const star=document.getElementById('star-button-box');if(star)star.hidden=s.showFavorites===false;
 root.toggleAttribute('sona-address-left',s.addressPosition==='left');
 pref('browser.tabs.closeWindowWithLastTab',!s.openStartPageAfterLastTab);
 pref('browser.tabs.unloadOnLowMemory',s.performanceMode!=='performance');pref('places.history.enabled',s.saveHistory!==false);
 pref('browser.bookmarks.showMobileBookmarks',false);
 document.getElementById('PersonalToolbar')?.toggleAttribute('sona-icons-only',!!s.bookmarksIconsOnly);
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
 
 pref('layout.css.prefers-color-scheme.content-override',resolveTheme(s.theme)==='dark'?0:1);Sona.notify?.();
}
function socksPort(){if(!shared.socksPort){const socket=Cc['@mozilla.org/network/server-socket;1'].createInstance(Ci.nsIServerSocket);socket.init(-1,true,-1);shared.socksPort=socket.port;socket.close();}return shared.socksPort;}
async function helperRequest(request){
 const operation=async()=>{
  if(!shared.helper){
   if(Services.appinfo.OS!=='WINNT')throw Error('VPN helper is available in the Windows build');
   const base=Services.dirsvc.get('GreD',Ci.nsIFile).path;
   const env=Subprocess.getEnvironment();env.SONA_SOCKS_PORT=String(socksPort());env.SONA_VPN_ROOT=PathUtils.join(profile,'sona-vpn');
   shared.helper=await Subprocess.call({command:PathUtils.join(base,'sona','vpn','SonaVpnHost.exe'),arguments:[],environment:env,stderr:'pipe'});
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
 const changed=shared.proxyEnabled!==enabled,previous=shared.proxyEnabled;if(changed){Sona.adblock?.abortUpdate?.();shared.proxyEnabled=enabled;}
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
  await helperRequest({action:'disconnect'});proxy(false);await IOUtils.remove(PathUtils.join(profile,'sona-network-before-vpn.json'),{ignoreAbsent:true});shared.vpnState={ok:true,state:'disconnected',connected:false};
 }else if(action==='connect'){
  const selected=shared.config.vpn.profiles.find(p=>p.id===shared.config.vpn.defaultProfileId);if(!selected)throw Error('Добавьте и выберите ключ в Настройки → VPN.');
  shared.networkBeforeVPN??={trr:Services.prefs.getIntPref('network.trr.mode',0),rtc:Services.prefs.getBoolPref('media.peerconnection.enabled',true)};await IOUtils.writeJSON(PathUtils.join(profile,'sona-network-before-vpn.json'),shared.networkBeforeVPN);
  proxy(true);shared.vpnState={state:'connecting',connected:false};emit('vpnState',shared.vpnState);
  try{const result=await helperRequest({action:'connect',url:selected.link,profileId:selected.id});shared.vpnState={...result,state:'connected'};}
  catch(error){shared.vpnState={state:'error',connected:false,error:error.message};emit('vpnState',shared.vpnState);paintVPN();throw error;}
 }else throw Error('Unsupported VPN operation');
 emit('vpnState',shared.vpnState);paintVPN();return shared.vpnState;
}
function paintVPN(){for(const win of windows()){const b=win.document.getElementById('sona-vpn');b?.toggleAttribute('connected',shared.vpnState.connected);b?.toggleAttribute('blocked',shared.vpnState.state==='error');b?.setAttribute('tooltiptext',shared.vpnState.error||'VPN · '+shared.vpnState.state);}}
function open(url){
 const uri=Services.io.newURI(url);if(!['http','https','about'].includes(uri.scheme))throw Error('Unsupported navigation scheme');
 openTrustedLinkIn(url,'tab');return true;
}
function settings(){if(shared.settingsWindow&&!shared.settingsWindow.closed){shared.settingsWindow.focus();return;}shared.settingsWindow=window.openDialog('chrome://sona/content/ui/settings.html','sona-settings','chrome,dialog=no,resizable,centerscreen,width=1060,height=760');}
function tabRows(){return gBrowser.tabs.map((t,id)=>({id,title:t.label,url:t.linkedBrowser.currentURI.spec,incognito:isPrivate}));}
async function bookmarks(){const rows=[];const tree=await PlacesUtils.promiseBookmarksTree(PlacesUtils.bookmarks.rootGuid);function walk(node){for(const n of node.children||[]){if(n.uri)rows.push({id:n.guid,title:n.title||n.uri,url:n.uri});walk(n);}}walk(tree);return rows;}
async function state(){const dirs=await IOUtils.getChildren(PathUtils.parent(profile)).catch(()=>[profile]);const profiles=[];for(const path of dirs){const info=await IOUtils.stat(path).catch(()=>null);if(info?.type!=='directory')continue;let name=PathUtils.filename(path);try{name=(await IOUtils.readJSON(PathUtils.join(path,'sona-profile.json'))).name;}catch{}profiles.push({id:PathUtils.filename(path),name,active:path===profile});}return {settings:shared.config.settings,profiles,activeProfileId:shared.config.profile,tabs:tabRows(),capabilities:{matteAvailable:Sona.material?.native===true},update:{sona:'0.13.0 Preview',gecko:Services.appinfo.platformVersion,firefox:Services.appinfo.version,xray:Sona.components?.xray?.version||'—',sudoku:Sona.components?.sudoku?.version||'—',adblock:'adblock-rust 0.13.3'}};}
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
 case 'settings.capabilities':return {matteAvailable:Sona.material?.native===true,defaultBrowser:ChromeUtils.importESModule('chrome://sona/content/window-controls.sys.mjs').isDefault()};
 case 'settings.ready':return true;
 case 'settings.save':{if(settingsBaseline&&JSON.stringify(payload.settings?.homeFavoriteIds)===JSON.stringify(settingsBaseline.settings.homeFavoriteIds))payload={...payload,settings:{...payload.settings,homeFavoriteIds:shared.config.settings.homeFavoriteIds}};const next=validate({...payload,onboarding:shared.config.onboarding,bookmarkIds:shared.config.bookmarkIds||{}}),old=shared.config;shared.config=next;try{
 if(next.settings.searchEngine!==old.settings.searchEngine){await Services.search.init();const names={google:'Google',yandex:'Яндекс',bing:'Bing',duckduckgo:'DuckDuckGo'};const engines=await Services.search.getVisibleEngines();const engine=engines.find(e=>e.name.toLowerCase().includes(names[next.settings.searchEngine]?.toLowerCase()));if(!engine)throw Error('Поисковая система недоступна в этой локализации Sona.');await Services.search.setDefault(engine,Services.search.CHANGE_REASON_USER);}await save();for(const w of windows())w.Sona?.refresh();if(shared.vpnState.connected)proxy(true);emit('settings',shared.config.settings);settingsBaseline=structuredClone(shared.config);return {ok:true,persisted:structuredClone(shared.config)};}catch(error){shared.config=old;return {ok:false,error:error.message,persisted:structuredClone(shared.config)};}}
 case 'settings.close':source?.close();return true;
 case 'settings.resize':case 'settings.extensions':return true;
 case 'settings.geckoSiteSettings':return Sona.settings('sites');
 case 'settings.geckoAdblockSettings':return Sona.settings('extensions');
 case 'settings.geckoTranslation':return Sona.settings('sites');
 case 'settings.geckoExtensions':return Sona.settings('extensions');
 case 'settings.geckoExtensionStore':return open('https://addons.mozilla.org/firefox/');
 case 'settings.geckoReader':document.getElementById('reader-mode-button')?.click();return true;
 case 'settings.openFolder':{const file=Services.dirsvc.get('DfltDwnld',Ci.nsIFile);file.launch();return true;}
 case 'settings.defaultBrowser':{if(Services.appinfo.OS!=='WINNT')throw Error('Требуется Windows.');if(!source?.gesture||Date.now()-source.gesture.at>2000)throw Error('Нажмите кнопку назначения браузера.');const command=PathUtils.join(Services.dirsvc.get('GreD',Ci.nsIFile).parent.path,'Sona.exe');const task=await Subprocess.call({command,arguments:['--register-default','--profile',shared.config.profile],stdout:'pipe',stderr:'pipe'});const result=await task.wait();if(result.exitCode)throw Error('Не удалось зарегистрировать Sona.');return {ok:true};}
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
 case 'browser.sites.blocking':shared.config.rules.blocking.enabled=!!payload;try{await save();}catch(error){console.error('Sona settings preserved:',error);}apply();return shared.config.rules;
 case 'browser.profile.create':{const id=Services.uuid.generateUUID().toString().replace(/[{}]/g,'');const path=PathUtils.join(PathUtils.parent(profile),id);await IOUtils.makeDirectory(path,{permissions:0o700});await IOUtils.writeJSON(PathUtils.join(path,'sona-profile.json'),{name:String(payload).slice(0,160)});return {id};}
 case 'browser.profile.switch':{
  if(!/^[\w-]{1,64}$/.test(payload))throw Error('Invalid profile');
  const base=Services.dirsvc.get('GreD',Ci.nsIFile).parent;base.append('Sona.exe');
  const proc=Cc['@mozilla.org/process/util;1'].createInstance(Ci.nsIProcess);proc.init(base);proc.runw(false,['--profile',payload],2);return true;}
 case 'browser.profile.delete':if(payload===shared.config.profile||!/^[\w-]{1,64}$/.test(payload))throw Error('Cannot delete active profile');await IOUtils.remove(PathUtils.join(PathUtils.parent(profile),payload),{recursive:true});return true;
 case 'vpn.send':return vpn(payload.action);
 case 'vpn.settings.get':return shared.config.vpn;
 case 'browser.components.manage':{if(!['xray','sudoku'].includes(payload?.component)||!['status','list','install','rollback'].includes(payload?.operation))throw Error('Invalid VPN component operation');return helperRequest({...payload,action:'components',name:payload.operation,proxy:shared.proxyEnabled===true});}
 case 'browser.extensions.list':{const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');return {items:(await AddonManager.getAddonsByTypes(['extension'])).map(a=>({id:a.id,name:a.name,version:a.version,enabled:a.isActive,action:false}))};}
 case 'browser.extensions.manager':return Sona.settings('extensions');
 case 'browser.extensions.openStore':return open('https://addons.mozilla.org/firefox/');
 case 'browser.performance.optimize':open('about:unloads');return {ok:true};
 case 'browser.passwords.get':return Sona.settings('passwords');
 case 'browser.import.native':throw Error('Мастер импорта ещё загружается. Повторите через секунду.');
 case 'browser.import.sources':case 'browser.import.browsers':return Sona.dispatch('browser.import.native',null,source);
 default:throw Error('Эта функция ещё не перенесена в Gecko Preview 4: '+action);
 }
}
window.Sona={dispatch,settings,refresh:apply,get config(){return shared.config;},get vpnState(){return shared.vpnState;},_emit(name,value){if(shared.settingsWindow&&!shared.settingsWindow.closed)shared.settingsWindow.__sonaEmit?.(name,value);},ready:false};
function button(id,label,command){const b=document.createXULElement('toolbarbutton');b.id=id;b.className='toolbarbutton-1 chromeclass-toolbar-additional';b.setAttribute('label',label);b.setAttribute('tooltiptext',label);b.addEventListener('command',command);return b;}
async function initialize(){
 const began=performance.now();Sona.startupTimings={initializeWindowAge:Math.round(began)};const timing=name=>Sona.startupTimings[name]=Math.round(performance.now()-began);
 if(!shared.initialized){shared.isNewProfile=!(await IOUtils.exists(settingsFile));if(shared.isNewProfile){try{const choice=await IOUtils.readJSON(PathUtils.join(PathUtils.parent(PathUtils.parent(profile)),'install-preferences.json'));if(['ru','en'].includes(choice.language))defaults.settings.language=shared.config.settings.language=choice.language;if(['light','dark'].includes(choice.theme))defaults.settings.theme=shared.config.settings.theme=choice.theme;}catch{}}try{const stored=await IOUtils.readJSON(settingsFile);if(stored.vpn?.protected){const encrypted=stored.vpn;try{const decoded=readVPNJSON(Cc['@mozilla.org/security/sdr;1'].getService(Ci.nsISecretDecoderRing).decryptString(stored.vpn.protected));if(decoded.repaired){const backup=settingsFile+'.before-unicode-repair';if(!(await IOUtils.exists(backup)))await IOUtils.copy(settingsFile,backup);await IOUtils.setPermissions(backup,0o600);shared.repairedSettings=true;}stored.vpn=decoded.value;}catch(error){shared.lockedVPN=encrypted;stored.vpn=structuredClone(defaults.vpn);shared.lockedVPNBaseline=JSON.stringify(stored.vpn);console.error("Sona VPN ciphertext preserved; other settings remain available",error);}}shared.config={...defaults,...stored,settings:{...defaults.settings,...stored.settings},rules:{...defaults.rules,...stored.rules},vpn:{...defaults.vpn,...stored.vpn}};}catch(error){if(await IOUtils.exists(settingsFile)){shared.storageError=String(error);console.error('Sona settings preserved:',error);}}try{shared.networkBeforeVPN=await IOUtils.readJSON(PathUtils.join(profile,'sona-network-before-vpn.json'));}catch{}proxy(false);await IOUtils.remove(PathUtils.join(profile,'sona-network-before-vpn.json'),{ignoreAbsent:true});shared.initialized=true;}
 shared.config.settings.layout='adaptive';
 Sona.backend={shared,Services,IOUtils,PathUtils,PlacesUtils,profile,isPrivate,save,apply};
 // Restore internal tabs saved before the product's filesystem identity changed.
 // Ordinary web addresses and their browsing state remain unchanged.
 const prior=String.fromCharCode(115,111,117,108,117);
 const restoreInternalTab=tab=>{try{
  const browser=tab.linkedBrowser,spec=browser.currentURI.spec;
  let leaf='';
  if(spec===prior+'://home')leaf='home.html';
  else if(spec.startsWith('file:')){const path=decodeURIComponent(new URL(spec).pathname);if(path.toLowerCase().includes('/engine/'+prior+'/chrome/ui/'))leaf=path.match(/\/([a-z0-9-]+\.html)$/i)?.[1]||'';}
  if(!leaf)return;
  const target=Services.dirsvc.get('GreD',Ci.nsIFile);for(const part of ['sona','chrome','ui',leaf])target.append(part);
  if(target.exists())browser.loadURI(Services.io.newFileURI(target),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});
 }catch(error){console.error('Sona internal tab migration',error);}};
 gBrowser.tabContainer.addEventListener('SSTabRestored',event=>restoreInternalTab(event.target));
 for(const tab of gBrowser.tabs)restoreInternalTab(tab);

 ChromeUtils.importESModule('chrome://sona/content/lifecycle.sys.mjs').ensureApplicationLifetime(window,shared);
 const themeChanged=()=>{if(shared.config.settings.theme==='system'){apply();Sona.notify?.();}};Services.obs.addObserver(themeChanged,'look-and-feel-changed');window.addEventListener('unload',()=>Services.obs.removeObserver(themeChanged,'look-and-feel-changed'),{once:true});
 layout();timing('settings');
 Services.scriptloader.loadSubScript('chrome://sona/content/storage.js',window);
 Services.scriptloader.loadSubScript('chrome://sona/content/shell-host.js',window);
 Services.scriptloader.loadSubScript('chrome://sona/content/weather.js',window);
 // Native filter compilation is synchronous FFI even inside an async method.
 // Start it after the first real Sona frame has been presented, not during
 // backend initialization while the window is hidden.
 window.addEventListener('SonaPresented',()=>{window.setTimeout(async()=>{
 try{const {adblock}=ChromeUtils.importESModule('chrome://sona/content/adblock.sys.mjs');Sona.adblock=adblock;await adblock.initialize(shared,profile);if(!shared.blockerUpdateScheduled){shared.blockerUpdateScheduled=true;setTimeout(()=>adblock.scheduleUpdate(),15000);}}catch(error){Sona.blockerError=String(error);console.error(error);}
 },0);},{once:true});
 timing('adblock');
 // Process-level lifecycle owns helper and remoting shutdown, even after XUL unload.
 try{Sona.components=await IOUtils.readJSON(PathUtils.join(Services.dirsvc.get('GreD',Ci.nsIFile).path,'sona','vpn','components.json'));}catch{}
 Services.scriptloader.loadSubScript('chrome://sona/content/translations.js',window);
 const nativeWindow=ChromeUtils.importESModule('chrome://sona/content/window-controls.sys.mjs');try{nativeWindow.brand(window);}catch(error){console.error(error);}
 try{await save();}catch(error){console.error('Sona settings preserved:',error);}apply();timing('applied');
 Services.scriptloader.loadSubScript('chrome://sona/content/integration.js',window);
 Services.scriptloader.loadSubScript('chrome://sona/content/page-glass.js',window);
 Services.scriptloader.loadSubScript('chrome://sona/content/settings-routing.js',window);
 // An early actor can time out while a large profile is loading. Give the
 // toolbar a fresh actor once the backend is available, preserving every tab.
 let retries=0;
 const recoverShell=()=>{
  if(window.closed||document.documentElement.hasAttribute('sona-ui-ready'))return;
  const frame=document.getElementById('sona-shell-frame');
  if(frame && retries++<2){
   frame.reload();
   window.setTimeout(recoverShell,20000);
  }
 };
 window.setTimeout(recoverShell,20000);
 window.Sona.ready=true;timing('ready');window.dispatchEvent(new Event('SonaBackendReady'));
}
initialize().catch(error=>{
 console.error('Sona startup',error);
 const panel=document.createElementNS('http://www.w3.org/1999/xhtml','div');
 panel.style.cssText='position:fixed;inset:0;z-index:20000;padding:48px;background:Canvas;color:CanvasText;font:16px system-ui';
 panel.textContent='Sona · Не удалось загрузить интерфейс. '+String(error);
 document.documentElement.append(panel);
});
})();

