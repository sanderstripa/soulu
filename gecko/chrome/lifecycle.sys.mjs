/* Process lifetime belongs to the application, not a closing window global. */
const {setTimeout,clearTimeout}=ChromeUtils.importESModule('resource://gre/modules/Timer.sys.mjs');
let registered=false,timer=null,quitting=false;
const observer={observe(_subject,topic){
 if(topic==='quit-application-granted'){quitting=true;if(timer)clearTimeout(timer);return;}
 if(quitting)return;
 if(timer)clearTimeout(timer);
 timer=setTimeout(()=>{timer=null;if(quitting)return;
  if([...Services.wm.getEnumerator('navigator:browser')].some(win=>!win.closed))return;
  // eForceQuit still performs normal XPCOM/profile shutdown; with every browser
  // window already closed there is no remaining window whose close can be vetoed.
  Services.startup.quit(Ci.nsIAppStartup.eForceQuit);
 },50);
}};
export function ensureApplicationLifetime(win,shared){
 if(!shared.initialWindow||shared.initialWindow.closed)shared.initialWindow=win;
 const interacted=event=>{if(event.isTrusted)shared.initialUserInput=true;};
 win.addEventListener('mousedown',interacted,true);win.addEventListener('keydown',interacted,true);
 if(registered)return;registered=true;Services.obs.addObserver(observer,'domwindowclosed');Services.obs.addObserver(observer,'quit-application-granted');}

// Suppress only redundant, empty automatic windows before the first user input.
// User-created windows and every window with actual page data remain untouched.
export function consolidateAutomaticStart(win){
 const backend=win.Soulu?.backend;if(!backend)return;
 const {shared,isPrivate}=backend,owner=shared.initialWindow;
 if(isPrivate||shared.initialUserInput||!owner||owner.closed||shared.config.settings.startupMode==='continue')return;
 const empty=w=>{if(w.closed||!w.Soulu?.backend||w.Soulu.backend.isPrivate||w.gBrowser?.tabs.length!==1)return false;const uri=w.gBrowser.selectedBrowser.currentURI.spec;return ['about:blank','about:newtab','about:home',w.Soulu.native.homeURL].includes(uri);};
 if(!empty(owner))return;
 for(const other of Services.wm.getEnumerator('navigator:browser'))if(other!==owner&&empty(other))other.close();
}
