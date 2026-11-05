/* Adapter for the exact CEF frontend. This file does not draw replacement controls. */
(() => {
'use strict';
const {shared,Services,IOUtils,PathUtils,PlacesUtils,profile,isPrivate,save,apply}=Soulu.backend;
const {appRoot}=ChromeUtils.importESModule('chrome://soulu/content/AppParent.sys.mjs');const appURL=appRoot();
const H='http://www.w3.org/1999/xhtml',homeURL=appURL+'home.html';
const base=Soulu.dispatch,ids=new WeakMap(),tabs=new Map();let nextId=1,frame,settingsFrame,shade,pending=0,expanded=false,side=false,bookmarksSide=false,overview=false,rightPanel=0,suggestions=0,popover=false,barAuto=false,toolbarHeight=68,marks=[],downloads=[],lastSnapshot='',lastTabCount=0,lastCosmeticGeneration=0,autoMuted=new WeakSet(),targetHeight=68,geometryToken=0,settingsReady=false,settingsAnimation=null,settingsEpoch=0,pendingSection=null,focusAfterHome=0;
let bookmarkConfirmation=false;
const tabID=tab=>{if(!ids.has(tab)){ids.set(tab,nextId);tabs.set(nextId++,tab);}return ids.get(tab);};
const selected=()=>gBrowser.selectedBrowser;
const currentURL=browser=>browser.currentURI.spec===homeURL?'soulu://home':browser.currentURI.spec;
const validTabs=()=>gBrowser.tabs.filter(t=>!t.closing);
function internalURL(kind){if(kind==='startup'&&shared.isNewProfile&&!isPrivate&&shared.config.onboarding?.done!==true)return appURL+'onboarding.html';const s=shared.config.settings,mode=s[kind+'Mode'];return mode==='custom'?s[kind+'Url']:mode==='blank'?'about:blank':homeURL;}
function load(url,background=false){const tab=gBrowser.addTrustedTab(url,{inBackground:background,skipAnimation:true});if(!background)gBrowser.selectedTab=tab;return tabID(tab);}
function rows(){return validTabs().map(tab=>({id:tabID(tab),active:tab===gBrowser.selectedTab,pinned:tab.pinned,title:tab.linkedBrowser.currentURI.spec===homeURL?'Soulu':tab.label,label:tab.label,url:currentURL(tab.linkedBrowser),favicon:tab.image||'',loading:tab.linkedBrowser.currentURI.spec!==homeURL&&tab.hasAttribute('busy'),canGoBack:tab.linkedBrowser.canGoBack,canGoForward:tab.linkedBrowser.canGoForward,microphoneActive:!!tab._sharingState?.microphone,cameraActive:!!tab._sharingState?.camera,audible:tab.hasAttribute('soundplaying'),muted:tab.hasAttribute('muted'),generation:tab.linkedBrowser.browsingContext.currentWindowGlobal?.innerWindowId||0,incognito:isPrivate,thumbnail:overview?(Soulu.thumbnails?.get(tab)||null):null}));}
function barVisible(){const s=shared.config.settings;if(s.bookmarksBarPosition==='hidden'||s.bookmarksBarMode==='never')return false;return s.bookmarksBarMode==='always'||s.bookmarksBarMode==='auto'&&barAuto||['newTab','home'].includes(s.bookmarksBarMode)&&currentURL(selected())==='soulu://home';}
function geometry(){
 const isolatedSidebar=bookmarksSide&&!bookmarkConfirmation&&!popover&&!side&&!overview&&!rightPanel&&!suggestions;
 const full=bookmarkConfirmation||popover||side||bookmarksSide||overview||rightPanel>0||suggestions>0;if(isolatedSidebar&&frame)frame.style.clipPath=`polygon(0 0,100% 0,100% ${toolbarHeight}px,276px ${toolbarHeight}px,276px 100%,0 100%)`;else if(!full&&frame)frame.style.clipPath='none';else if(frame&&frame.style.clipPath==='none')frame.style.clipPath=`inset(0 0 calc(100% - ${toolbarHeight}px) 0)`;
 if(bookmarkConfirmation&&frame)frame.style.clipPath='none';
 const height=(validTabs().length>1?88:68)+(barVisible()?28:0),root=document.documentElement;
 if(height!==targetHeight){targetHeight=height;const from=toolbarHeight,start=performance.now(),token=++geometryToken,duration=matchMedia('(prefers-reduced-motion:reduce)').matches?60:320;
  send('adaptiveGeometry',{animation:{startAt:Date.now(),duration,from:from-(barVisible()?28:0),to:height-(barVisible()?28:0)},expanded:validTabs().length>1});
  const tick=now=>{if(token!==geometryToken)return;const p=Math.min(1,(now-start)/duration),e=1-Math.pow(1-p,3);toolbarHeight=from+(height-from)*e;root.style.setProperty('--soulu-toolbar-height',toolbarHeight+'px');if(!popover&&!side&&!bookmarksSide&&!overview&&!rightPanel&&!suggestions)root.style.setProperty('--soulu-surface-height',toolbarHeight+'px');if(p===1)notify();if(p<1)requestAnimationFrame(tick);};requestAnimationFrame(tick);
 }
 root.style.setProperty('--soulu-surface-height',(full?innerHeight:toolbarHeight)+'px');root.style.setProperty('--soulu-right-panel',rightPanel+'px');root.style.setProperty('--soulu-left-panel',bookmarksSide?'276px':'0px');root.toggleAttribute('soulu-fullscreen',fullScreen);
}
function snapshot(){const list=rows(),page=list.find(t=>t.active);return {tabs:list,page,activeTabId:page?.id,update:{soulu:'0.12.0 Preview',gecko:Services.appinfo.platformVersion,firefox:Services.appinfo.version,xray:Soulu.components?.xray?.version||'—',sudoku:Soulu.components?.sudoku?.version||'—',adblock:'adblock-rust 0.13.3'},settings:{...shared.config.settings,layout:'adaptive'},incognito:isPrivate,fullscreen:fullScreen,maximized:windowState===STATE_MAXIMIZED,sidebarVisible:side,bookmarksSidebarVisible:bookmarksSide,overviewVisible:overview,bookmarksBarVisible:barVisible(),bookmarks:marks,clientHeight:innerHeight,clientWidth:innerWidth,activeProfileId:shared.config.profile,adaptiveToolbar:{expanded:list.length>1,progress:Math.max(0,Math.min(1,(toolbarHeight-(barVisible()?28:0)-68)/20)),height:toolbarHeight-(barVisible()?28:0),active:toolbarHeight!==targetHeight},pageGlassReady:document.documentElement.hasAttribute('soulu-page-glass'),surfaceExpanded:!!(popover||side||bookmarksSide||overview||rightPanel||suggestions),settingsOverlayOpen:!!settingsFrame&&!settingsFrame.hidden,settingsOverlayReady:settingsReady};}
function actorSend(browser,name,data){try{browser?.browsingContext?.currentWindowGlobal?.getActor('SouluApp').sendAsyncMessage(name,data);}catch{}}
function send(name,value){actorSend(frame,'emit',{name,value});if(settingsFrame&&!settingsFrame.hidden)actorSend(settingsFrame,'emit',{name,value});}
function emitTo(browser,value){actorSend(browser,'home',value);}
function soundPolicy(){for(const tab of validTabs()){let host='';try{host=new URL(tab.linkedBrowser.currentURI.spec).hostname;}catch{}const value=shared.config.rules.sites[host]?.sound??shared.config.rules.defaults.sound;const mute=value===1||value===2;if(mute&&!tab.hasAttribute('muted')){tab.toggleMuteAudio();autoMuted.add(tab);}else if(!mute&&autoMuted.has(tab)){if(tab.hasAttribute('muted'))tab.toggleMuteAudio();autoMuted.delete(tab);}}}
let lastHomeState='';function notify(){if(pending)return;pending=requestAnimationFrame(()=>{pending=0;const h=homeState(),hs=JSON.stringify(h);if(hs!==lastHomeState){lastHomeState=hs;for(const tab of validTabs())if(tab.linkedBrowser.currentURI.spec===homeURL)emitTo(tab.linkedBrowser,h);}geometry();soundPolicy();const value=snapshot();if(value.page?.generation!==lastCosmeticGeneration&&/^https?:/.test(value.page?.url||'')){lastCosmeticGeneration=value.page.generation;Soulu.adblock?.attach?.(selected());}const signature=JSON.stringify(value);if(signature!==lastSnapshot){lastSnapshot=signature;send('state',value);}document.title=(value.page?.title?value.page.title+' — ':'')+'Soulu';});}
function surface(){geometry();return snapshot();}
const originalEmit=Soulu._emit;Soulu._emit=(name,value)=>{originalEmit(name,value);send(name,value);if(name==='settings'){notify();for(const tab of validTabs())if(tab.linkedBrowser.currentURI.spec===homeURL)emitTo(tab.linkedBrowser,homeState());}};
function makeFrame(id,url){const node=document.createXULElement('browser');node.id=id;node.setAttribute('type','content');node.setAttribute('remote','true');node.setAttribute('remoteType','file');node.setAttribute('disablehistory','true');node.setAttribute('transparent','true');node.setAttribute('src',url);node.setAttribute('aria-label',id==='soulu-shell-frame'?'Панель Soulu':'Настройки Soulu');document.documentElement.append(node);return node;}
function animateSettings(open){const epoch=++settingsEpoch;settingsAnimation?.cancel();settingsFrame.hidden=shade.hidden=false;settingsFrame.style.visibility='visible';const reduced=matchMedia('(prefers-reduced-motion:reduce)').matches;settingsAnimation=settingsFrame.animate(open?[{transform:'translate(-50%,-24px)',opacity:0},{transform:'translate(-50%,0)',opacity:1}]:[{transform:'translate(-50%,0)',opacity:1},{transform:'translate(-50%,-24px)',opacity:0}],{duration:reduced?60:190,easing:'cubic-bezier(.22,1,.36,1)',fill:'both'});shade.animate(open?[{opacity:0},{opacity:1}]:[{opacity:1},{opacity:0}],{duration:reduced?60:190,fill:'both'});settingsAnimation.finished.then(()=>{if(epoch!==settingsEpoch)return;if(!open){Soulu.settingsRequested=false;settingsFrame.hidden=shade.hidden=true;selected().focus();}settingsAnimation.cancel();settingsAnimation=null;notify();},()=>{});}
function prepareSettings(){if(settingsFrame)return;shade=document.createElementNS(H,'div');shade.id='soulu-settings-shade';shade.addEventListener('click',()=>closeSettings());document.documentElement.append(shade);settingsFrame=makeFrame('soulu-settings-frame',appURL+'settings.html?host=overlay');settingsFrame.style.visibility='hidden';settingsFrame.hidden=shade.hidden=true;}
function settings(section){Soulu.settingsRequested=true;pendingSection=section||null;prepareSettings();{shade.hidden=settingsFrame.hidden=false;if(settingsReady)actorSend(settingsFrame,'openSection',section||'');if(settingsReady)animateSettings(true);}settingsFrame.focus();notify();}
function closeSettings(){Soulu.settingsRequested=false;pendingSection=null;if(settingsFrame&&!settingsFrame.hidden)animateSettings(false);}
function homeState(){const s=shared.config.settings;return {...s,resolvedTheme:s.theme==='system'?(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'):s.theme,favorites:(s.homeFavoriteIds||[]).map(id=>marks.find(r=>r.id===id&&r.type!=='folder')).filter(Boolean),weather:Soulu.weatherSnapshot?.()||null,homeProvider:s.homeProvider||'google',homeLocationAllowed:shared.config.rules.sites['soulu://home']?.geolocation===0,homeLocationPermission:shared.config.rules.sites['soulu://home']?.geolocation??1};}
function navigate(value){value=String(value||'').trim();if(!value)return;let url;if(value==='soulu://home')url=homeURL;else if(/^https?:\/\//i.test(value))url=new URL(value).href;else if(/^(localhost|[^\s/.]+\.[^\s/]+)(:\d+)?([/?#].*)?$/.test(value))url='https://'+value;else{const engines={google:'https://www.google.com/search?q=',yandex:'https://yandex.ru/search/?text=',bing:'https://www.bing.com/search?q=',duckduckgo:'https://duckduckgo.com/?q='};url=(engines[shared.config.settings.searchEngine]||engines.google)+encodeURIComponent(value);}
 if(shared.config.settings.addressOpenMode==='newIfOccupied'&&!['about:blank',homeURL].includes(selected().currentURI.spec))load(url);else selected().loadURI(Services.io.newURI(url),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});notify();}
function site(){const browser=selected(),url=currentURL(browser);let origin='',domain='';try{const u=new URL(url);if(['http:','https:'].includes(u.protocol)){origin=u.origin;domain=u.hostname;}}catch{}const block=Soulu.adblock?.status(browser.browsingContext.id)||{};return {tabId:tabID(gBrowser.selectedTab),url,generation:browser.browsingContext.currentWindowGlobal?.innerWindowId||0,origin,domain,favicon:gBrowser.selectedTab.image||'',secureConnection:url.startsWith('https:'),mainLoading:browser.currentURI.spec!==homeURL&&gBrowser.selectedTab.hasAttribute('busy'),zoom:Math.round(browser.fullZoom*100),rules:structuredClone(shared.config.rules),preferences:shared.config.reader,readerAvailable:!!browser.isArticle,readerActive:false,adblock:{...block,active:shared.config.rules.blocking.sites[domain]??shared.config.rules.blocking.enabled}};}
async function siteAction(action,payload){const browser=selected();if(payload?.tabId!==undefined&&(payload.tabId!==tabID(gBrowser.selectedTab)||payload.url!==currentURL(browser)))throw Error('Страница изменилась. Откройте меню заново.');
 if(action==='permission'){shared.config.rules.sites[site().domain]??={};if(Number(payload.value)<0)delete shared.config.rules.sites[site().domain][payload.permission];else shared.config.rules.sites[site().domain][payload.permission]=Number(payload.value);await save();apply();}
 else if(action==='blocking'){shared.config.rules.blocking.sites[site().domain]=payload.value===undefined?!!payload.enabled:!!Number(payload.value);await save();browser.reload();}
 else if(action==='reset'){delete shared.config.rules.sites[site().domain];delete shared.config.rules.blocking.sites[site().domain];for(const permission of Services.perms.getAllForPrincipal(browser.contentPrincipal))Services.perms.removeFromPrincipal(browser.contentPrincipal,permission.type);await save();apply();}
 else if(action==='zoom'){browser.fullZoom=payload.command==='reset'?1:Math.max(.3,Math.min(3,browser.fullZoom+(payload.command==='in'?.1:-.1)));}
 else if(action==='find'){browser.finder.fastFind(payload.text||'',false,false);}
 else if(action==='probe'||action==='reader.probe')return site();
 else if(action==='clear'){await new Promise(resolve=>Services.clearData.deleteDataFromPrincipal(browser.contentPrincipal,false,Ci.nsIClearDataService.CLEAR_DOM_STORAGES,resolve));return {...site(),cleared:true};}
 else if(action.startsWith('reader.'))throw Error('Режим чтения Gecko будет подключён отдельным этапом.');
 else throw Error('Недоступное действие сайта: '+action);notify();return site();}
async function menu(items,x,y){return new Promise(resolve=>{const popup=document.createXULElement('menupopup');let result=0;for(const item of items){const el=document.createXULElement(item.separator?'menuseparator':'menuitem');if(!item.separator){el.setAttribute('label',item.label||'');if(item.enabled===false)el.setAttribute('disabled','true');el.addEventListener('command',()=>{result=item.command;});}popup.append(el);}document.getElementById('mainPopupSet').append(popup);popup.addEventListener('popuphidden',()=>{popup.remove();resolve(result);},{once:true});popup.openPopupAtScreen(x,y,false);});}
async function key(event){if(event.defaultPrevented)return;const code=event.key.toLowerCase();if(event.ctrlKey&&event.shiftKey&&code==='t')return;if(event.ctrlKey&&!event.shiftKey&&code==='j'){event.preventDefault();send('openDownloads',null);}else if(event.ctrlKey&&event.shiftKey&&code==='b'){event.preventDefault();await dispatch('browser.bookmarks.auto',!barVisible());}else if(event.ctrlKey&&(code==='b'||event.shiftKey&&code==='o')){event.preventDefault();bookmarksSide=!bookmarksSide;geometry();notify();}else if(event.ctrlKey&&code===','){event.preventDefault();settings();}else if(event.altKey&&['f','t'].includes(code)){event.preventDefault();await dispatch('window.toolbarMenu');}else if(event.ctrlKey&&code==='l'){event.preventDefault();send('focusAddress',null);frame.focus();}else if(event.ctrlKey&&code==='t'){event.preventDefault();await dispatch('browser.newTab');}else if(event.ctrlKey&&code==='w'){event.preventDefault();await dispatch('browser.closeTab',tabID(gBrowser.selectedTab));}else if(event.ctrlKey&&code==='h'){event.preventDefault();openHistory();}else if(event.key==='Escape'){popover=false;suggestions=0;overview=false;bookmarksSide=false;geometry();notify();}}
function openHistory(clear=false){const id=load(appURL+'history.html'+(clear?'?clear=1':''));return id;}
async function dispatch(action,payload,source){
 if(action.startsWith('home.')){
  if(action==='home.get'){await Soulu.weatherReady;return homeState();}if(action==='home.ready'){if(focusAfterHome===tabID(gBrowser.selectedTab)){focusAfterHome=0;frame.focus();send('focusAddress',null);}return true;}if(action==='home.navigate'){const query=String(payload||'').trim();if(query&&!/^https?:\/\//i.test(query)&&!/^([^\s/.]+\.[^\s/]+)(:\d+)?([/?#].*)?$/.test(query)){const provider=shared.config.settings.homeProvider==='perplexity'?'https://www.perplexity.ai/search?q=':'https://www.google.com/search?q=';navigate(provider+encodeURIComponent(query));}else navigate(query);return true;}
  if(action==='home.set'){Object.assign(shared.config.settings,payload);await save();notify();return homeState();}
  if(action==='home.favorite.add'){const row=marks.find(r=>String(r.id)===String(payload)&&r.url&&/^https?:/.test(r.url));if(!row)throw Error('Bookmark unavailable');const ids=shared.config.settings.homeFavoriteIds||[];if(!ids.includes(row.id)){shared.config.settings.homeFavoriteIds=[...ids,row.id];await save();notify();}return homeState();}
  if(action==='home.favorite.reorder'){const ids=shared.config.settings.homeFavoriteIds||[];if(!Array.isArray(payload)||payload.length!==ids.length||new Set(payload).size!==ids.length||payload.some(id=>!ids.includes(id)))throw Error('Invalid favorites order');shared.config.settings.homeFavoriteIds=payload;await save();notify();return homeState();}
  if(action==='home.favorite'){const row=marks.find(r=>r.id===payload.id);if(row)load(row.url,payload.background);return true;}
  if(action==='home.favorite.edit'){settings('startup');return true;}
  if(action==='home.weather.permission'){if(typeof payload!=='boolean')throw Error('Invalid permission');shared.config.rules.sites['soulu://home']={...(shared.config.rules.sites['soulu://home']||{}),geolocation:payload?0:2};await save();notify();return homeState();}
  if(action==='home.weather')return Soulu.weather?Soulu.weather(payload||{}):{status:'unavailable'};
  throw Error('Эта дополнительная функция домашней страницы пока недоступна.');
 }
 if(action.startsWith('history.'))return Soulu.history(action.slice(8),payload,source);
 switch(action){
 case 'browser.state.get':return {...await base('browser.state.get'),...snapshot()};
 case 'browser.navigate':navigate(payload);return true;
 case 'browser.newTab':focusAfterHome=load(internalURL('newTab'));setTimeout(()=>send('focusAddress',null),40);notify();return true;
 case 'browser.openTab':{const url=payload.url;if(!/^(https?:|about:)/.test(url))throw Error('Unsupported URL');load(url,!!payload.background);notify();return true;}
 case 'browser.home':navigate('soulu://home');return true;
 case 'browser.back':if(selected().canGoBack)selected().goBack();return true;
 case 'browser.reload':if(gBrowser.selectedTab.hasAttribute('busy'))selected().stop();else selected().reload();return true;
 case 'browser.switchTab':{const tab=tabs.get(Number(payload));if(tab&&!tab.closing)gBrowser.selectedTab=tab;notify();return true;}
 case 'browser.closeTab':{const tab=tabs.get(Number(payload));if(tab&&!tab.closing){if(validTabs().length===1&&shared.config.settings.openStartPageAfterLastTab)tab.linkedBrowser.loadURI(Services.io.newURI(internalURL('startup')),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});else gBrowser.removeTab(tab,{animate:false});}notify();return true;}
 case 'browser.pinTab':{const t=tabs.get(Number(payload));if(t)t.pinned?gBrowser.unpinTab(t):gBrowser.pinTab(t);notify();return true;}
 case 'browser.tab.audio':{const t=tabs.get(Number(payload));if(t)t.toggleMuteAudio();notify();return true;}
 case 'browser.toggleSidebar':side=!side;geometry();notify();return snapshot();
 case 'browser.bookmarks.sidebar':bookmarksSide=!!payload;geometry();notify();return snapshot();
 case 'browser.overview':overview=!!payload;geometry();notify();return snapshot();
 case 'browser.bookmarks.auto':barAuto=!!payload;notify();return snapshot();
 case 'browser.setRightPanel':rightPanel=Math.max(0,Math.min(400,Number(payload)||0));geometry();return true;
 case 'browser.setSuggestionsHeight':suggestions=Number(payload)||0;geometry();return true;
 case 'browser.bookmarks.confirmation':{if(!source?.appURI?.endsWith('/index.html')||typeof payload!=='boolean')throw Error('Trusted shell required');bookmarkConfirmation=payload;geometry();notify();return true;}
 case 'browser.surfaceRegions':{
  if(!source?.appURI?.endsWith('/index.html'))throw Error('Trusted shell required');
  if(bookmarkConfirmation){frame.style.clipPath='none';return true;}
  if(!(popover||side||bookmarksSide||overview||rightPanel||suggestions))return true;
  if(bookmarksSide&&!popover&&!side&&!overview&&!rightPanel&&!suggestions){geometry();return true;}
  if(!Array.isArray(payload)||payload.length>24)throw Error('Invalid regions');
  let path=`M0 0H${innerWidth}V${toolbarHeight}H0Z`;
  for(const rect of payload){if(!Array.isArray(rect)||rect.length!==4||rect.some(n=>!Number.isFinite(n)))throw Error('Invalid rectangle');const [x,y,w,h]=rect,left=Math.max(0,x),top=Math.max(0,y),right=Math.min(innerWidth,x+w),bottom=Math.min(innerHeight,y+h);if(right>left&&bottom>top)path+=` M${left} ${top}H${right}V${bottom}H${left}Z`;}
  frame.style.clipPath=`path('${path}')`;return true;
 }
 case 'browser.popover':popover=!!payload;geometry();return true;
 case 'browser.pageMenu':send('requestSiteMenu',null);return true;
 case 'browser.site.get':return site();
 case 'browser.find':selected().finder.fastFind(payload.text||'',false,false);return true;
 case 'browser.suggestions':{const q=String(payload||'').toLowerCase();const history=await Soulu.history('query',{search:q,offset:0,limit:5});return [...rows().filter(t=>(t.title+' '+t.url).toLowerCase().includes(q)).map(t=>({...t,source:'tab'})),...marks.filter(r=>r.url&&(r.title+' '+r.url).toLowerCase().includes(q)).map(r=>({...r,source:'bookmark'})),...history.rows.map(r=>({...r,source:'history'}))].slice(0,9);}
 case 'browser.downloads.get':return downloads;
 case 'browser.menu.show':return menu(payload.items,source?.pointer?.screenX??(window.mozInnerScreenX+payload.x),source?.pointer?.screenY??(window.mozInnerScreenY+payload.y));
 case 'browser.history.open':return openHistory(!!payload);
 case 'browser.settings.openWindow':settings(payload);return true;
 case 'settings.close':closeSettings();return true;
 case 'settings.resize':{if(settingsFrame){settingsFrame.style.height=Math.min(Number(payload.height)||720,innerHeight)+'px';}return true;}
 case 'settings.ready':settingsReady=true;if(settingsFrame&&Soulu.settingsRequested)animateSettings(true);if(pendingSection)actorSend(settingsFrame,'openSection',pendingSection);notify();return true;
 case 'settings.capabilities':return {matteAvailable:Soulu.material?.native===true,defaultBrowser:ChromeUtils.importESModule('chrome://soulu/content/window-controls.sys.mjs').isDefault()};
 case 'window.frontendReady':if(source?.appURI?.endsWith('/index.html')){document.documentElement.setAttribute('soulu-ui-ready','true');if(!Soulu.settingsWarmupScheduled){Soulu.settingsWarmupScheduled=true;window.requestIdleCallback(()=>prepareSettings(),{timeout:2500});}Soulu.startupTimings??={};Soulu.startupTimings.functionalFirstFrameProcessAge=Date.now()-Services.startup.getStartupInfo().process.getTime();ChromeUtils.importESModule('chrome://soulu/content/window-controls.sys.mjs').revealStartup(window);notify();}return true;
 case 'browser.bookmarks.get':marks=await Soulu.bookmarks('get');notify();return marks;
 case 'browser.bookmarks.add':marks=await Soulu.bookmarks('add',{url:currentURL(selected()),title:gBrowser.selectedTab.label});notify();return marks;
 case 'browser.bookmarks.remove':marks=await Soulu.bookmarks('remove',payload);shared.config.settings.homeFavoriteIds=(shared.config.settings.homeFavoriteIds||[]).filter(id=>marks.some(r=>r.id===id&&r.url));await save();notify();return marks;
 case 'browser.bookmarks.replace':marks=await Soulu.bookmarks('replace',Array.isArray(payload)?payload:payload.rows);shared.config.settings.homeFavoriteIds=(shared.config.settings.homeFavoriteIds||[]).filter(id=>marks.some(r=>r.id===id&&r.url));await save();notify();return marks;
 case 'browser.bookmarks.open':navigate(payload);return true;
 case 'browser.bookmarks.homeFavorite':{if(!Number.isSafeInteger(payload.id)||payload.selected&&!marks.some(r=>r.id===payload.id&&r.url))throw Error('Закладка изменилась. Откройте редактор заново.');const ids=new Set(shared.config.settings.homeFavoriteIds||[]);payload.selected?ids.add(payload.id):ids.delete(payload.id);shared.config.settings.homeFavoriteIds=[...ids];await save();notify();return true;}
 case 'browser.settings.set':{const c=structuredClone(shared.config);Object.assign(c.settings,payload);const r=await base('settings.save',c,source);notify();return r;}
 case 'settings.save':{const r=await base(action,payload,source);if(r.ok){Soulu.adblock?.refresh?.();notify();for(const t of validTabs())if(t.linkedBrowser.currentURI.spec===homeURL)emitTo(t.linkedBrowser,homeState());}return r;}
 case 'window.minimize':window.minimize();return true;
 case 'window.maximize':windowState===STATE_MAXIMIZED?window.restore():window.maximize();notify();return true;
 case 'window.close':await shared.saveQueue;window.close();return true;
 case 'window.captionBounds':return true;
 case 'window.beginDrag':if(Number(payload)>1){windowState===STATE_MAXIMIZED?window.restore():window.maximize();}else ChromeUtils.importESModule('chrome://soulu/content/window-controls.sys.mjs').beginDrag();return true;
 case 'window.toolbarMenu':{const en=shared.config.settings.language==='en';const items=[{command:1,label:en?'Settings':'Настройки'},{command:2,label:en?'Downloads':'Загрузки'},{command:5,label:en?'History':'История'},{command:6,label:en?'Clear browsing data…':'Очистить данные браузера…'},{separator:true},{command:3,label:en?'New tab':'Новая вкладка'},{command:4,label:en?'New incognito tab':'Новая вкладка инкогнито'}];const command=await menu(items,source?.pointer?.screenX??window.mozInnerScreenX+40,source?.pointer?.screenY??window.mozInnerScreenY+40);if(command===1)settings();if(command===2)send('openDownloads',null);if(command===5)openHistory();if(command===6)openHistory(true);if(command===3)await dispatch('browser.newTab');if(command===4)OpenBrowserWindow({private:true});return true;}
 }
 if(action.startsWith('browser.site.'))return siteAction(action.slice(13),payload||{});
 return base(action,payload,source);
}
Soulu.native={tabID,tabs,load,navigate,site,settings,send,homeURL,homeState};Soulu.dispatch=dispatch;Soulu.settings=settings;Soulu.key=key;Soulu.snapshot=snapshot;Soulu.notify=notify;Soulu.ui=()=>frame;Soulu.closeSettings=closeSettings;
const css=document.createProcessingInstruction('xml-stylesheet','href="chrome://soulu/content/host.css" type="text/css"');document.insertBefore(css,document.documentElement);
document.documentElement.setAttribute('chromemargin','0,0,0,0');
frame=document.getElementById('soulu-shell-frame')||makeFrame('soulu-shell-frame',appURL+'index.html');
const permissionAnchor=document.getElementById('notification-popup-box');if(permissionAnchor){document.documentElement.append(permissionAnchor);permissionAnchor.style.cssText='position:fixed;left:calc(50% - 285px);top:14px;width:22px;height:22px;opacity:.01;pointer-events:none;z-index:9999';}
gBrowser.tabContainer.addEventListener('TabClose',event=>{const id=ids.get(event.target);if(id)tabs.delete(id);},true);
for(const event of ['TabOpen','TabClose','TabSelect','TabPinned','TabUnpinned','TabAttrModified'])gBrowser.tabContainer.addEventListener(event,notify);
gBrowser.addTabsProgressListener({onLocationChange(browser,progress){if(!progress||progress.isTopLevel){try{if(shared.config.rules.sites[browser.currentURI.host])apply();}catch{}notify();}},onStateChange(_browser,progress,_request,flags){if((!progress||progress.isTopLevel)&&(flags&(Ci.nsIWebProgressListener.STATE_START|Ci.nsIWebProgressListener.STATE_STOP)))notify();},onSecurityChange(_browser,progress){if(!progress||progress.isTopLevel)notify();}});
window.addEventListener('resize',()=>{geometry();if(settingsFrame&&!settingsFrame.hidden)settingsFrame.style.maxHeight=innerHeight+'px';notify();});window.addEventListener('sizemodechange',notify);window.addEventListener('keydown',key,true);
gBrowser.addEventListener('mousedown',()=>{suggestions=0;popover=false;send('dismissSuggestions',null);geometry();},true);
window.addEventListener('blur',()=>{suggestions=0;geometry();send('dismissSuggestions',null);});
Soulu.startupReady=(async()=>{await Soulu.storageReady;marks=await Soulu.bookmarks('get');if(shared.config.settings.startupMode==='continue'){const {SessionStore}=ChromeUtils.importESModule('moz-src:///browser/components/sessionstore/SessionStore.sys.mjs');await SessionStore.promiseAllWindowsRestored;}if(shared.config.settings.startupMode!=='continue'&&validTabs().every(t=>['about:blank','about:newtab','about:home',homeURL].includes(t.linkedBrowser.currentURI.spec)))selected().loadURI(Services.io.newURI(internalURL('startup')),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});notify();})().catch(console.error);
})();

