/* Existing Soulu welcome layout, new-profile-only state and real native actions. */
(()=>{
const {shared,save,isPrivate}=Soulu.backend,base=Soulu.dispatch;
const flow=()=>shared.config.onboarding??={step:1,done:!shared.isNewProfile};
Soulu.showOnboarding=()=>{if(isPrivate||flow().done)return;const url=ChromeUtils.importESModule('chrome://soulu/content/AppParent.sys.mjs').appRoot()+'onboarding.html';gBrowser.selectedBrowser.loadURI(Services.io.newURI(url),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});};
Soulu.dispatch=async(action,payload,source)=>{
 if(!action.startsWith('onboarding.'))return base(action,payload,source);
 if(!source?.appURI?.endsWith('/onboarding.html')||isPrivate)throw Error('Trusted welcome page required');
 const current=flow();if(action==='onboarding.get')return {flow:current,settings:shared.config.settings,rules:shared.config.rules};
 if(action==='onboarding.progress'){
  if(Number.isInteger(payload.step)&&payload.step>=1&&payload.step<=6)current.step=payload.step;
  const c=structuredClone(shared.config);
  if(['en','ru'].includes(payload.language))c.settings.language=payload.language;
  if(['system','light','dark'].includes(payload.theme))c.settings.theme=payload.theme;
  if(typeof payload.weatherLocation==='boolean'){c.rules.sites['soulu://home']={...(c.rules.sites['soulu://home']||{}),geolocation:payload.weatherLocation?0:2};}
  if(typeof payload.adblock==='boolean'){c.rules.blocking.enabled=payload.adblock;current.privacyApplied=true;}
  if(typeof payload.askPermissions==='boolean'){for(const k of ['camera','microphone','geolocation','notifications'])c.rules.defaults[k]=payload.askPermissions?1:2;current.privacyApplied=true;}
  c.onboarding=current;const result=await base('settings.save',c,source);if(!result.ok)throw Error(result.error);return {flow:current,settings:shared.config.settings,rules:shared.config.rules};
 }
 if(action==='onboarding.import'){current.importOpened=true;await save();return Soulu.dispatch('browser.import.native',null,source);}
 if(action==='onboarding.vpn'){
 const link=String(payload?.link||'').trim();if(!/^vless:\/\/|^sudoku:\/\//.test(link)||link.length>16384)throw Error('Введите ключ VLESS или Sudoku.');
 const c=structuredClone(shared.config),id=Services.uuid.generateUUID().toString();c.vpn.profiles.push({id,name:String(payload.name||'VPN'),link});c.vpn.defaultProfileId=id;
 const result=await base('settings.save',c,source);if(!result.ok)throw Error(result.error);return {ok:true};
 }
 if(action==='onboarding.default')return Soulu.dispatch('settings.defaultBrowser',null,source);
 if(action==='onboarding.finish'){current.done=true;current.skipped=!!payload?.skip;await save();Soulu.native.navigate('soulu://home');return true;}
 throw Error('Unknown welcome action');
};
let welcomeRedirectPending=false;gBrowser.addTabsProgressListener({onLocationChange(browser,_progress,_request,uri){if(isPrivate||!shared.isNewProfile||flow().done||welcomeRedirectPending||browser!==gBrowser.selectedBrowser||!['about:home','about:newtab',Soulu.native.homeURL].includes(uri.spec))return;welcomeRedirectPending=true;window.setTimeout(()=>{welcomeRedirectPending=false;if(!flow().done&&browser===gBrowser.selectedBrowser)Soulu.showOnboarding();},0);}});
const ensureWelcome=()=>{if(!isPrivate&&!flow().done&&['about:blank','about:newtab','about:home',Soulu.native.homeURL].includes(gBrowser.selectedBrowser.currentURI.spec))Soulu.showOnboarding();};
if(gBrowserInit.delayedStartupFinished)Promise.resolve(Soulu.startupReady).then(ensureWelcome).catch(console.error);else{const ready=subject=>{if(subject!==window)return;Services.obs.removeObserver(ready,'browser-delayed-startup-finished');Promise.resolve(Soulu.startupReady).then(ensureWelcome).catch(console.error);};Services.obs.addObserver(ready,'browser-delayed-startup-finished');window.addEventListener('unload',()=>{try{Services.obs.removeObserver(ready,'browser-delayed-startup-finished');}catch{}},{once:true});}
})();
