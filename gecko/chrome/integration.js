/* Native Firefox integrations. This script runs only in the trusted browser window. */
(()=>{
'use strict';
const {shared,Services,IOUtils,PathUtils,PlacesUtils,profile,isPrivate,save}=Soulu.backend;
const {tabID,tabs,load,send}=Soulu.native;
const {SessionStore}=ChromeUtils.importESModule('moz-src:///browser/components/sessionstore/SessionStore.sys.mjs');
const base=Soulu.dispatch,selected=()=>gBrowser.selectedBrowser;
function checkedTab(id){const tab=tabs.get(Number(id));if(!tab||tab.closing)throw Error('Вкладка закрыта.');return tab;}
function profileFile(id){if(!/^[\w-]{1,64}$/.test(id))throw Error('Invalid profile');const file=Cc['@mozilla.org/file/local;1'].createInstance(Ci.nsIFile);file.initWithPath(PathUtils.join(PathUtils.parent(profile),id));if(!file.exists()||!file.isDirectory()||file.isSymlink())throw Error('Invalid profile directory');return file;}
async function choose(mode,title,filter){const picker=Cc['@mozilla.org/filepicker;1'].createInstance(Ci.nsIFilePicker);picker.init(window.browsingContext,title,mode);if(filter)picker.appendFilter(filter[0],filter[1]);const result=await new Promise(resolve=>picker.open(resolve));return result===Ci.nsIFilePicker.returnOK||result===Ci.nsIFilePicker.returnReplace?picker.file.path:null;}
async function importFile(kind,path){
 if(isPrivate)throw Error('Импорт недоступен в инкогнито.');if(!['bookmarks','passwords'].includes(kind))throw Error('Unknown import');const stat=await IOUtils.stat(path);if(stat.size>20*1024*1024)throw Error('Файл превышает 20 МБ.');
 if(kind==='bookmarks'){const {BookmarkHTMLUtils}=ChromeUtils.importESModule('resource://gre/modules/BookmarkHTMLUtils.sys.mjs');const result=await BookmarkHTMLUtils.importFromFile(path,{replace:false});await Soulu.bookmarks('invalidate');await Soulu.dispatch('browser.bookmarks.get');return {imported:result};}
 const {LoginCSVImport}=ChromeUtils.importESModule('resource://gre/modules/LoginCSVImport.sys.mjs');const rows=await LoginCSVImport.importFromCSV(path);return {added:rows.filter(r=>r.result==='added').length,modified:rows.filter(r=>r.result==='modified').length,failed:rows.filter(r=>!['added','modified','no_change'].includes(r.result)).length};
}
// Parent-only entry point for native fixture tests; no web-content action accepts file paths.
Soulu.importFile=importFile;
function readerPrefs(){const r=shared.config.reader;Services.prefs.setStringPref('reader.font_type',r.font==='serif'?'serif':'sans-serif');Services.prefs.setIntPref('reader.font_size',Math.max(1,Math.min(9,Math.round((Number(r.size)||18)/2)-4)));Services.prefs.setStringPref('reader.color_scheme',['light','dark','sepia','auto'].includes(r.theme)?r.theme:'auto');Services.prefs.setIntPref('reader.content_width',[3,6,9][Math.max(0,Math.min(2,Math.round(Number(r.width)||0)))]);Services.prefs.setIntPref('reader.line_height',[3,5,7][Math.max(0,Math.min(2,Math.round(Number(r.spacing)||0)))]);}
const refresh=Soulu.refresh;Soulu.refresh=()=>{refresh();readerPrefs();};readerPrefs();
Soulu.dispatch=async(action,payload,source)=>{
 if(action.startsWith('browser.site.'))action='site.'+action.slice(13);
 const browser=selected();
 if(action.startsWith('site.')&&payload?.tabId!==undefined&&(payload.tabId!==tabID(gBrowser.selectedTab)||payload.url!==browser.currentURI.spec||payload.generation!==undefined&&payload.generation!==(browser.browsingContext.currentWindowGlobal?.innerWindowId||0)))throw Error('Страница изменилась. Откройте меню заново.');
 switch(action){
 case 'browser.adblock.status':return Soulu.adblock?.status()||{ready:false};
 case 'browser.adblock.update':return Soulu.adblock.update();
 case 'site.find':send('requestFind',null);return true;
 case 'site.reader.preferences':{const values=payload.preferences||{};for(const [key,value] of Object.entries(values)){if(!['theme','font','size','width','spacing'].includes(key))throw Error('Параметр недоступен в режиме чтения Firefox.');if(key==='theme'&&!['light','dark','sepia','auto'].includes(value)||key==='font'&&!['system','sans','serif'].includes(value)||['size','width','spacing'].includes(key)&&!Number.isFinite(Number(value)))throw Error('Invalid reader preference');}Object.assign(shared.config.reader,values);await save();readerPrefs();return Soulu.dispatch('browser.site.get');}
 case 'browser.shareMenu':{const url=browser.currentURI.spec;if(!/^https?:/.test(url))throw Error('Откройте веб-страницу.');const command=await base('browser.menu.show',{items:[{command:1,label:'Копировать ссылку'},{command:2,label:'QR-код страницы'}],x:innerWidth/2,y:50},source);if(command===1)Cc['@mozilla.org/widget/clipboardhelper;1'].getService(Ci.nsIClipboardHelper).copyString(url);if(command===2)send('geckoQR',url);return true;}
 case 'browser.restoreTab':{const tab=SessionStore.undoCloseTab(window,0,window);Soulu.notify();return tab?tabID(tab):null;}
 case 'browser.duplicateTab':{const tab=SessionStore.duplicateTab(window,checkedTab(payload));gBrowser.selectedTab=tab;Soulu.notify();return tabID(tab);}
 case 'browser.reloadTab':checkedTab(payload).linkedBrowser.reload();return true;
 case 'browser.closeOtherTabs':gBrowser.removeAllTabsBut(checkedTab(payload));Soulu.notify();return true;
 case 'browser.moveTabBefore':case 'browser.moveTabAfter':{const tab=checkedTab(payload.id),target=checkedTab(payload.targetId);if(tab.pinned!==target.pinned)throw Error('Закреплённые вкладки перемещаются отдельно.');if(action.endsWith('Before'))gBrowser.moveTabBefore(tab,target);else gBrowser.moveTabAfter(tab,target);Soulu.notify();return true;}
 case 'browser.forward':if(browser.canGoForward)browser.goForward();return true;
 case 'browser.stop':browser.stop();return true;
 case 'browser.forceReload':browser.reloadWithFlags(Ci.nsIWebNavigation.LOAD_FLAGS_BYPASS_CACHE);return true;
 case 'browser.requestFind':send('requestFind',null);return true;
 case 'browser.find':if(payload?.repeat)browser.finder.findAgain(!!payload.backwards,false,false);else browser.finder.fastFind(String(payload?.text||''),false,false);return true;
 case 'browser.profile.rename':{const file=profileFile(payload.id),name=String(payload.name||'').replace(/[\x00-\x1f]/g,'').trim().slice(0,160);if(!name)throw Error('Введите название профиля.');await IOUtils.writeJSON(PathUtils.join(file.path,'soulu-profile.json'),{name});return true;}
 case 'browser.profile.delete':{if(payload===shared.config.profile)throw Error('Нельзя удалить активный профиль.');const file=profileFile(payload),service=Cc['@mozilla.org/toolkit/profile-service;1'].getService(Ci.nsIToolkitProfileService);try{await service.removeProfileFilesByPath(file,file,0);}catch{throw Error('Профиль используется другим процессом или недоступен. Закройте его перед удалением.');}return true;}
 case 'browser.settings.siteSnapshot':{const tab=checkedTab(payload.tabId),b=tab.linkedBrowser;return {tabId:tabID(tab),url:b.currentURI.spec,generation:b.browsingContext.currentWindowGlobal?.innerWindowId||0};}
 case 'browser.settings.clearSite':{const tab=checkedTab(payload.tabId),b=tab.linkedBrowser;if(!payload.confirmed||b.currentURI.spec!==payload.url||b.browsingContext.currentWindowGlobal?.innerWindowId!==payload.generation)throw Error('Страница изменилась. Подтвердите очистку заново.');await new Promise((resolve,reject)=>Services.clearData.deleteDataFromPrincipal(b.contentPrincipal,false,Ci.nsIClearDataService.CLEAR_DOM_STORAGES,failed=>failed?reject(Error('Не удалось очистить данные.')):resolve()));return {cleared:true};}
 case 'browser.import.native':{const {MigrationUtils}=ChromeUtils.importESModule('moz-src:///browser/components/migration/MigrationUtils.sys.mjs');MigrationUtils.showMigrationWizard(null,{entrypoint:MigrationUtils.MIGRATION_ENTRYPOINTS.UNKNOWN});return true;}
 case 'browser.import.filePicker':{const kind=payload;if(!['bookmarks','passwords'].includes(kind))throw Error('Invalid import');const path=await choose(Ci.nsIFilePicker.modeOpen,kind==='bookmarks'?'Импорт закладок':'Импорт паролей',kind==='bookmarks'?['HTML','*.html;*.htm']:['CSV','*.csv']);return path?importFile(kind,path):{canceled:true};}
 case 'browser.import.exportBookmarks':{if(isPrivate)throw Error('Экспорт недоступен в инкогнито.');const path=await choose(Ci.nsIFilePicker.modeSave,'Экспорт закладок',['HTML','*.html']);if(!path)return {canceled:true};const {BookmarkHTMLUtils}=ChromeUtils.importESModule('resource://gre/modules/BookmarkHTMLUtils.sys.mjs');await BookmarkHTMLUtils.exportToFile(path);return {ok:true};}
 case 'site.reader.toggle':case 'site.reader.enter':case 'site.reader.exit':{const url=browser.currentURI.spec;if(url.startsWith('about:reader?')){const original=new URL(url).searchParams.get('url');if(!/^https?:/.test(original||''))throw Error('Invalid reader URL');browser.loadURI(Services.io.newURI(original),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});}else{if(!/^https?:/.test(url))throw Error('Режим чтения доступен для веб-страниц.');readerPrefs();browser.loadURI(Services.io.newURI('about:reader?url='+encodeURIComponent(url)),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});}return true;}
 case 'site.get':case 'site.reader.probe':{const result=await base('browser.site.get',payload,source);return {...result,readerActive:browser.currentURI.spec.startsWith('about:reader?'),readerAvailable:!!browser.isArticle||browser.currentURI.spec.startsWith('about:reader?')};}
 case 'browser.performance.optimize':{let count=0;for(const tab of gBrowser.tabs){if(tab===gBrowser.selectedTab||tab.pinned||tab.hasAttribute('soundplaying')||tab._sharingState?.microphone||tab._sharingState?.camera)continue;if(gBrowser.discardBrowser(tab))count++;}return {ok:true,unloaded:count};}
 }
 return base(action.startsWith('site.')?'browser.'+action:action,payload,source);
};
async function key(event){if(event.defaultPrevented)return;const k=event.key.toLowerCase();let action,payload;if(event.ctrlKey&&event.shiftKey&&k==='t')action='browser.restoreTab';else if(event.ctrlKey&&event.shiftKey&&k==='delete'){action='browser.history.open';payload=true;}else if(event.ctrlKey&&k==='f')action='browser.requestFind';else if(event.altKey&&k==='arrowleft')action='browser.back';else if(event.altKey&&k==='arrowright')action='browser.forward';else if(k==='f5'||event.ctrlKey&&k==='r')action=event.shiftKey?'browser.forceReload':'browser.reload';else if(k==='f9')action='site.reader.toggle';else if(event.ctrlKey&&['+','=','-','0'].includes(k)){action='site.zoom';payload={command:k==='0'?'reset':k==='-'?'out':'in'};}if(action){event.preventDefault();event.stopPropagation?.();await Soulu.dispatch(action,payload);}}
Soulu.integrationKey=key;window.addEventListener('keydown',e=>key(e).catch(console.error),true);
let bookmarkTimer;const bookmarkChanged=()=>{clearTimeout(bookmarkTimer);bookmarkTimer=setTimeout(async()=>{try{await Soulu.bookmarks('invalidate');await Soulu.dispatch('browser.bookmarks.get');}catch(e){console.error(e);}},80);};
const events=['bookmark-added','bookmark-removed','bookmark-moved','bookmark-title-changed','bookmark-url-changed'];PlacesUtils.observers.addListener(events,bookmarkChanged);gBrowser.tabContainer.addEventListener('TabMove',Soulu.notify);window.addEventListener('unload',()=>{clearTimeout(bookmarkTimer);PlacesUtils.observers.removeListener(events,bookmarkChanged);},{once:true});
let checkingVPN=false;const failedRequest={observe(){if(!shared.vpnState.connected||checkingVPN)return;checkingVPN=true;Soulu.dispatch('vpn.send',{action:'status'}).catch(console.error).finally(()=>checkingVPN=false);}};Services.obs.addObserver(failedRequest,'http-on-failed-opening-request');window.addEventListener('unload',()=>Services.obs.removeObserver(failedRequest,'http-on-failed-opening-request'),{once:true});
Services.scriptloader.loadSubScript('chrome://soulu/content/downloads.js',window);
Services.scriptloader.loadSubScript('chrome://soulu/content/extensions.js',window);
})();
