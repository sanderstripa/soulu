/* Restore native tabs into one initial window; explicit later windows remain native. */
(()=>{
 const {shared,isPrivate}=Soulu.backend;if(isPrivate||shared.startupWindowTask)return;
 shared.startupWindowTask=(async()=>{
  const {SessionStore}=ChromeUtils.importESModule('moz-src:///browser/components/sessionstore/SessionStore.sys.mjs');
  await SessionStore.promiseAllWindowsRestored;
  const {PrivateBrowsingUtils}=ChromeUtils.importESModule('resource://gre/modules/PrivateBrowsingUtils.sys.mjs');
  const restored=[...Services.wm.getEnumerator('navigator:browser')].filter(w=>!w.closed&&!PrivateBrowsingUtils.isWindowPrivate(w));
  if(restored.length<2)return;
  const primary=restored.find(w=>w===window)||restored[0];
  for(const other of restored){
   if(other===primary||other.closed||!other.gBrowser)continue;
   // Keep every restored page, including pinned tabs. Never discard user data
   // merely to remove a stale/duplicate restored top-level window.
   for(const tab of [...other.gBrowser.tabs])if(!tab.closing)primary.gBrowser.adoptTab(tab,primary.gBrowser.tabs.length,false);
   if(!other.closed)other.close();
  }
  primary.Soulu?.notify();
 })().catch(error=>{Soulu.startupWindowError=String(error);console.error(error);});
})();
