/* Soulu controls; Firefox owns extension actions, permissions, storage and popup processes. */
(()=>{
'use strict';
const {shared,isPrivate,Services}=Soulu.backend;
const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');
const {ExtensionParent}=ChromeUtils.importESModule('resource://gre/modules/ExtensionParent.sys.mjs');
const {CustomizableUI}=ChromeUtils.importESModule('moz-src:///browser/components/customizableui/CustomizableUI.sys.mjs');
const {PanelPopup}=ChromeUtils.importESModule('resource:///modules/ExtensionPopups.sys.mjs');
const base=Soulu.dispatch,icons=new Map(),widgets=new Map();let pending=0,revision=0,last='',popup=null,anchor=null,epoch=0,closed=false;
function native(id){const policy=WebExtensionPolicy.getByID(id),extension=policy?.extension,api=extension&&ExtensionParent.apiManager.global.browserActionFor?.(extension);return {extension,api};}
function checkProfile(payload){if(payload?.profile!==shared.config.profile)throw Error('Профиль изменился. Обновите список расширений.');}
async function iconFor(extension,api){
 const context=api.action.getContextData(gBrowser.selectedTab),all=context.icon||{},sizes=Object.keys(all).map(Number).filter(Number.isFinite).sort((a,b)=>a-b),size=sizes.find(n=>n>=32)||sizes.at(-1);let url=all[size];if(typeof url==='object')url=url[document.documentElement.hasAttribute('soulu-dark')?'dark':'light'];if(typeof url!=='string')return '';
 if(!url.startsWith('data:image/')){url=extension.baseURI.resolve(url);const uri=Services.io.newURI(url);if(uri.scheme!=='moz-extension'||uri.prePath!==extension.baseURI.prePath)return '';}
 const key=extension.id+':'+url;if(icons.has(key))return icons.get(key);
 const value=(async()=>{try{const response=await window.fetch(url,{credentials:'omit'}),mime=(response.headers.get('content-type')||'').split(';')[0];if(!response.ok||!/^image\/(png|jpeg|gif|webp|svg\+xml|x-icon|vnd\.microsoft\.icon)$/i.test(mime))return '';const reader=response.body.getReader(),parts=[];let length=0;for(;;){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>262144){await reader.cancel();return '';}parts.push(value);}let binary='';for(const part of parts)for(const byte of part)binary+=String.fromCharCode(byte);return 'data:'+mime+';base64,'+btoa(binary);}catch{return '';}})();
 if(icons.size>=128)icons.delete(icons.keys().next().value);icons.set(key,value);return value;
}
function delegate(api){
 const delegates=shared.extensionDelegates??=new Map();if(delegates.has(api))return;const original=api.openPopup;
 const wrapped=function(win,withoutUserInteraction=false){const handler=win?.Soulu?.extensions?.openNativePopup;if(handler)return handler(this.extension.id,withoutUserInteraction);return original.call(this,win,withoutUserInteraction);};
 delegates.set(api,{original,wrapped});api.openPopup=wrapped;
}
function watch(api){delegate(api);const node=api.widget?.forWindow(window)?.node;if(!node?.isConnected||widgets.has(node))return;const observer=new MutationObserver(schedule);observer.observe(node,{attributes:true,subtree:true,attributeFilter:['style','badge','badgeStyle','disabled','data-l10n-args']});widgets.set(node,observer);}
async function list(){
 if(Soulu.votReady)await Soulu.votReady;
 for(const [node,observer] of widgets)if(!node.isConnected){observer.disconnect();widgets.delete(node);}
 const addons=await AddonManager.getAddonsByTypes(['extension']),items=[];
 for(const addon of addons){if(addon.isSystem||addon.isBuiltin||addon.hidden)continue;const {extension,api}=native(addon.id);if(isPrivate&&(!extension||!extension.canAccessWindow(window)))continue;const action=api?.action,context=action?.getContextData(gBrowser.selectedTab);if(api)watch(api);const color=context?.badgeBackgroundColor||[217,46,54,255],textColor=context?.badgeTextColor||[255,255,255,255];
  items.push({id:addon.id,name:addon.name,version:addon.version,enabled:addon.isActive,action:!!action,actionEnabled:!!action?.isShownForTab(gBrowser.selectedTab),pinned:!!api&&CustomizableUI.getPlacementOfWidget(api.id)?.area===CustomizableUI.AREA_NAVBAR,title:context?.title||addon.name,badge:String(context?.badgeText||'').slice(0,12),badgeColor:color,badgeTextColor:textColor,icon:api?await iconFor(extension,api):'',privateAllowed:!!extension?.privateBrowsingAllowed});
 }
 return {profile:shared.config.profile,incognito:isPrivate,items};
}
function schedule(){if(closed||pending)return;const current=++revision;pending=requestAnimationFrame(async()=>{pending=0;try{const value=await list();if(closed||current!==revision)return;const signature=JSON.stringify(value);if(signature!==last){last=signature;Soulu.native.send('extensions',value);}}catch(error){console.error('Soulu extensions:',error);}});}
function closePopup(){epoch++;if(popup){const old=popup;popup=null;if(!old.destroyed)old.closePopup();}anchor?.remove();anchor=null;}
function checkRequest(payload,source){
 checkProfile(payload);if(!source?.appURI?.endsWith('/index.html')||!Number.isFinite(source.gesture?.at)||Date.now()-source.gesture.at<0||Date.now()-source.gesture.at>2000)throw Error('Нажмите кнопку расширения в панели Soulu.');
 if(payload.tabId!==Soulu.native.tabID(gBrowser.selectedTab)||payload.generation!==(gBrowser.selectedBrowser.browsingContext.currentWindowGlobal?.innerWindowId||0))throw Error('Активная страница изменилась. Нажмите кнопку снова.');
}
function triggerUserAction(api,tab){const handling=window.windowUtils.setHandlingUserInput(true);try{return api.action.triggerClickOrPopup(tab,{button:0,modifiers:[]});}finally{handling.destruct();}}
async function open(payload,source){
 checkRequest(payload,source);
 const {extension,api}=native(payload.id);if(!extension||!api||!extension.canAccessWindow(window))throw Error('Расширение недоступно в этом окне.');if(!api.action.isShownForTab(gBrowser.selectedTab))throw Error('Действие расширения отключено для этой страницы.');
 if(popup?.extension===extension&&!popup.destroyed){closePopup();return {open:false};}closePopup();const ticket=epoch,tab=gBrowser.selectedTab;
 // This is the stock action path: enabled/restricted-site checks, activeTab grant,
 // activation of scripts and onClicked dispatch remain inside Firefox.
 const url=triggerUserAction(api,tab);if(!url){schedule();return {open:false,clicked:true};}
 return showPopup(extension,api,url,payload.anchor,tab,ticket);
}
async function showPopup(extension,api,url,rectangle,tab,ticket){
 const uri=Services.io.newURI(url);if(uri.scheme!=='moz-extension'||uri.prePath!==extension.baseURI.prePath)throw Error('Неподдерживаемый адрес панели расширения.');
 const rect=rectangle;if(!rect||!['x','y','width','height'].every(k=>Number.isFinite(rect[k]))||rect.width<=0||rect.height<=0)throw Error('Invalid action anchor');
 const node=document.createElementNS('http://www.w3.org/1999/xhtml','span');node.id='soulu-extension-anchor';node.style.cssText=`position:fixed;left:${Math.max(0,Math.min(innerWidth-1,rect.x))}px;top:${Math.max(0,Math.min(innerHeight-1,rect.y))}px;width:${Math.min(64,rect.width)}px;height:${Math.min(64,rect.height)}px;pointer-events:none;background:transparent;`;document.documentElement.append(node);anchor=node;
 const current=new PanelPopup(extension,document,url,api.browserStyle);popup=current;const panel=current.viewNode;panel.dataset.souluExtension=extension.id;
 panel.addEventListener('popuphidden',()=>{if(popup===current){popup=null;anchor?.remove();anchor=null;}schedule();},{once:true});
 try{await current.browserReady;if(ticket!==epoch||tab!==gBrowser.selectedTab||!extension.canAccessWindow(window)||current.destroyed){if(!current.destroyed)current.closePopup();return {open:false};}panel.openPopup(node,'after_end',0,0,false,false);await current.browserLoaded;return {open:true};}catch(error){closePopup();throw error;}
}
Soulu.dispatch=async(action,payload,source)=>{
 if(action==='browser.extensions.manage'){checkProfile(payload);Soulu.closeSettings?.();await window.BrowserAddonUI.openAddonsMgr('addons://list/extension');return true;}
 if(action==='browser.extensions.list'){if(payload?.profile!==undefined)checkProfile(payload);return list();}
 if(action==='browser.extensions.setEnabled'){checkProfile(payload);if(!source?.gesture||Date.now()-source.gesture.at>2000)throw Error('Нажмите переключатель расширения.');const addon=await AddonManager.getAddonByID(payload.id);if(!addon||addon.isSystem||addon.isBuiltin||addon.hidden)throw Error('Расширение недоступно.');payload.enabled?await addon.enable():await addon.disable();schedule();return list();}
 if(action==='browser.extensions.pin'){checkProfile(payload);const {extension,api}=native(payload.id);if(!extension||!api||!extension.canAccessWindow(window))throw Error('Расширение недоступно.');CustomizableUI.addWidgetToArea(api.id,payload.pinned?CustomizableUI.AREA_NAVBAR:CustomizableUI.AREA_ADDONS);schedule();return list();}
 if(action==='browser.extensions.open')return open(payload,source);
 if(action==='browser.extensions.overflow'){
  checkRequest(payload,source);closePopup();const available=(await list()).items.filter(i=>i.enabled&&i.action),menu=document.createXULElement('menupopup');menu.dataset.souluExtensions='true';let chosen=null;
  if(!available.length){const empty=document.createXULElement('menuitem');empty.setAttribute('label','Нет расширений');empty.setAttribute('disabled','true');menu.append(empty);}
  for(const item of available){const node=document.createXULElement('menuitem');node.setAttribute('label',item.title||item.name);if(/^data:image\//.test(item.icon||'')){node.classList.add('menuitem-iconic');node.setAttribute('image',item.icon);}node.dataset.extensionId=item.id;if(!item.actionEnabled)node.setAttribute('disabled','true');node.addEventListener('command',event=>{if(event.isTrusted)chosen=item.id;});menu.append(node);}
  document.getElementById('mainPopupSet').append(menu);return new Promise((resolve,reject)=>{menu.addEventListener('popuphidden',()=>{menu.remove();if(!chosen){resolve({open:false});return;}open({...payload,id:chosen},{...source,gesture:{at:Date.now()}}).then(resolve,reject);},{once:true});const r=payload.anchor;if(!r||!['x','y','width','height'].every(k=>Number.isFinite(r[k]))){menu.remove();reject(Error('Invalid menu anchor'));return;}menu.openPopupAtScreen(window.mozInnerScreenX+r.x,window.mozInnerScreenY+r.y+r.height,false);});
 }
 if(action==='browser.extensions.close'){closePopup();return true;}
 return base(action,payload,source);
};
const addonListener={onInstalled:schedule,onEnabled:schedule,onDisabled(){closePopup();schedule();},onUninstalled(addon){closePopup();icons.clear();for(const [api,value] of shared.extensionDelegates||[])if(api.extension.id===addon.id){if(api.openPopup===value.wrapped)api.openPopup=value.original;shared.extensionDelegates.delete(api);}schedule();},onPropertyChanged:schedule};AddonManager.addAddonListener(addonListener);
const customization={onWidgetAdded:schedule,onWidgetRemoved:schedule,onWidgetMoved:schedule,onWidgetAfterDOMChange:schedule};CustomizableUI.addListener(customization);
const selected=()=>{closePopup();schedule();};gBrowser.tabContainer.addEventListener('TabSelect',selected);gBrowser.tabContainer.addEventListener('TabAttrModified',schedule);window.addEventListener('resize',closePopup);
window.addEventListener('unload',()=>{closed=true;closePopup();if(pending)cancelAnimationFrame(pending);for(const observer of widgets.values())observer.disconnect();widgets.clear();icons.clear();AddonManager.removeAddonListener(addonListener);CustomizableUI.removeListener(customization);if(![...Services.wm.getEnumerator('navigator:browser')].some(w=>w!==window&&!w.closed&&w.Soulu?.extensions)){for(const [api,value] of shared.extensionDelegates||[])if(api.openPopup===value.wrapped)api.openPopup=value.original;shared.extensionDelegates?.clear();}},{once:true});
async function openNativePopup(id,withoutUserInteraction){
 const {extension,api}=native(id);if(!extension||!api||!extension.canAccessWindow(window))throw Error('Расширение недоступно в этом окне.');
 if(Services.focus.activeWindow!==window)return;if(popup?.extension===extension&&!popup.destroyed)return {open:true};
 const tab=gBrowser.selectedTab,url=api.action.getPopupUrl(tab);if(!url)return;
 const rectangle=await Soulu.ui().browsingContext.currentWindowGlobal.getActor('SouluApp').sendQuery('extensionAnchor',id);
 if(!rectangle)throw Error('Закрепите расширение на панели Soulu перед открытием его окна.');
 if(tab!==gBrowser.selectedTab)return;closePopup();const ticket=epoch;
 // Firefox's API has already validated its own user-gesture policy. Preserve
 // its distinction: programmatic openPopup must not mint activeTab permission.
 const target=withoutUserInteraction?url:triggerUserAction(api,tab);if(!target)return;
 return showPopup(extension,api,target,rectangle,tab,ticket);
}
Soulu.extensions={refresh:schedule,openNativePopup};schedule();
})();
