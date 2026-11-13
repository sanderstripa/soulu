/* Native compositor snapshots: bounded memory, per window, no capture loop. */
(()=>{
const {tabID,tabs}=Sona.native,{PageThumbs}=ChromeUtils.importESModule('resource://gre/modules/PageThumbs.sys.mjs');
const cache=new Map(),inflight=new Map();let sequence=0,closed=false;
const generation=tab=>tab.linkedBrowser.browsingContext.currentWindowGlobal?.innerWindowId;
async function capture(id,force=false){
 const tab=tabs.get(Number(id));if(!tab||tab.closing||tab.hasAttribute('pending'))return null;
 const browser=tab.linkedBrowser,key=generation(tab),old=cache.get(tab);
 if(old?.key===key&&(!force||Date.now()-old.at<1500))return old.url;
 if(inflight.has(tab))return inflight.get(tab);
 const task=(async()=>{try{
  const canvas=document.createElementNS('http://www.w3.org/1999/xhtml','canvas');canvas.width=480;canvas.height=300;
  await PageThumbs.captureToCanvas(browser,canvas,{fullViewport:true,targetWidth:480},true);
  if(closed||tab.closing||generation(tab)!==key)return null;
  const url=canvas.toDataURL('image/jpeg',.72);if(url.length>400000)return null;
  cache.delete(tab);cache.set(tab,{url,key,at:Date.now()});while(cache.size>32)cache.delete(cache.keys().next().value);
  Sona.notify();return url;
 }catch(error){console.debug('Sona thumbnail unavailable',String(error));return null;}finally{inflight.delete(tab);}})();inflight.set(tab,task);return task;
}
Sona.thumbnails={capture,get:tab=>{const item=cache.get(tab);return item?.key===generation(tab)?item.url:null;},async overview(){const epoch=++sequence;for(const tab of gBrowser.tabs){if(closed||epoch!==sequence)return;await capture(tabID(tab),tab===gBrowser.selectedTab);}}};
const selected=()=>capture(tabID(gBrowser.selectedTab),true);
gBrowser.tabContainer.addEventListener('TabSelect',selected);gBrowser.tabContainer.addEventListener('TabClose',e=>cache.delete(e.target));
gBrowser.addTabsProgressListener({onStateChange(browser,progress,_request,flags){if(progress?.isTopLevel&&(flags&Ci.nsIWebProgressListener.STATE_STOP)&&browser===gBrowser.selectedBrowser)selected();}});
const base=Sona.dispatch;Sona.dispatch=async(action,payload,source)=>{if(action==='browser.tab.thumbnail')return {thumbnail:await capture(payload.id),id:payload.id};if(action==='browser.overview'&&payload)Sona.thumbnails.overview().catch(console.error);return base(action,payload,source);};
window.addEventListener('unload',()=>{closed=true;sequence++;cache.clear();},{once:true});
})();
