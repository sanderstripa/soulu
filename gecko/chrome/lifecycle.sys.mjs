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
export function ensureApplicationLifetime(){if(registered)return;registered=true;Services.obs.addObserver(observer,'domwindowclosed');Services.obs.addObserver(observer,'quit-application-granted');}
