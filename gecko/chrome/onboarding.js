/* Existing Sona welcome layout, new-profile-only state and real native actions. */
(()=>{
const {shared,save,isPrivate}=Sona.backend,base=Sona.dispatch;
const flow=()=>shared.config.onboarding??={step:1,done:!shared.isNewProfile};
Sona.showOnboarding=()=>{if(isPrivate||flow().done)return;const url=ChromeUtils.importESModule('chrome://sona/content/AppParent.sys.mjs').appRoot()+'onboarding.html';gBrowser.selectedBrowser.loadURI(Services.io.newURI(url),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});};
Sona.dispatch=async(action,payload,source)=>{
 if(!action.startsWith('onboarding.'))return base(action,payload,source);
 if(!source?.appURI?.endsWith('/onboarding.html')||isPrivate)throw Error('Trusted welcome page required');
 const current=flow();if(action==='onboarding.get')return {flow:current,settings:shared.config.settings,resolvedTheme:ChromeUtils.importESModule('chrome://sona/content/theme.sys.mjs').resolveTheme(shared.config.settings.theme),rules:shared.config.rules};
 if(action==='onboarding.progress'){
  if(Number.isInteger(payload.step)&&payload.step>=1&&payload.step<=6)current.step=payload.step;
  const c=structuredClone(shared.config);
  if(['en','ru'].includes(payload.language))c.settings.language=payload.language;
  if(['system','light','dark'].includes(payload.theme))c.settings.theme=payload.theme;
  if(typeof payload.weatherLocation==='boolean'){c.rules.sites['sona://home']={...(c.rules.sites['sona://home']||{}),geolocation:payload.weatherLocation?0:2};}
  if(typeof payload.adblock==='boolean'){c.rules.blocking.enabled=payload.adblock;current.privacyApplied=true;}
  if(typeof payload.askPermissions==='boolean'){for(const k of ['camera','microphone','geolocation','notifications'])c.rules.defaults[k]=payload.askPermissions?1:2;current.privacyApplied=true;}
  c.onboarding=current;const result=await base('settings.save',c,source);if(!result.ok)throw Error(result.error);if(payload.weatherLocation===true)Sona.weather({interactive:false}).catch(console.error);return {flow:current,settings:shared.config.settings,resolvedTheme:ChromeUtils.importESModule('chrome://sona/content/theme.sys.mjs').resolveTheme(shared.config.settings.theme),rules:shared.config.rules};
 }
 if(action==='onboarding.import'){current.importOpened=true;await save();return Sona.dispatch('browser.import.native',null,source);}
 if(action==='onboarding.vpn'){
 const link=String(payload?.link||'').trim();if(!/^vless:\/\/|^sudoku:\/\//.test(link)||link.length>16384)throw Error('Введите ключ VLESS или Sudoku.');
 const sandbox=Cu.Sandbox(Services.scriptSecurityManager.getSystemPrincipal());sandbox.window=sandbox;sandbox.URL=URL;sandbox.atob=atob;Services.scriptloader.loadSubScript('chrome://sona/content/ui/vpn-key.js',sandbox);const parsed=Cu.waiveXrays(sandbox).sonaParseVpnKey(link);const row=JSON.parse(JSON.stringify(parsed));const c=structuredClone(shared.config),id=Services.uuid.generateUUID().toString();row.id=id;row.name=row.region&&row.region!=='Не указан'?row.region:row.address;
 const existing=c.vpn.profiles.find(p=>p.link===row.link);if(!existing)c.vpn.profiles.push(row);c.vpn.defaultProfileId=existing?.id||id;for(const field of ['link','protocol','address','region'])c.vpn[field]=row[field];
 const result=await base('settings.save',c,source);if(!result.ok)throw Error(result.error);return {ok:true};
 }
 if(action==='onboarding.default')return Sona.dispatch('settings.defaultBrowser',null,source);
 if(action==='onboarding.finish'){current.done=true;current.skipped=!!payload?.skip;await save();Sona.native.navigate('sona://home');return true;}
 throw Error('Unknown welcome action');
};
let welcomeRedirectPending=false;gBrowser.addTabsProgressListener({onLocationChange(browser,_progress,_request,uri){if(isPrivate||!shared.isNewProfile||flow().done||welcomeRedirectPending||browser!==gBrowser.selectedBrowser||!['about:home','about:newtab',Sona.native.homeURL].includes(uri.spec))return;welcomeRedirectPending=true;window.setTimeout(()=>{welcomeRedirectPending=false;if(!flow().done&&browser===gBrowser.selectedBrowser)Sona.showOnboarding();},0);}});
const ensureWelcome=()=>{if(!isPrivate&&!flow().done&&['about:blank','about:newtab','about:home',Sona.native.homeURL].includes(gBrowser.selectedBrowser.currentURI.spec))Sona.showOnboarding();};
if(gBrowserInit.delayedStartupFinished)Promise.resolve(Sona.startupReady).then(ensureWelcome).catch(console.error);else{const ready=subject=>{if(subject!==window)return;Services.obs.removeObserver(ready,'browser-delayed-startup-finished');Promise.resolve(Sona.startupReady).then(ensureWelcome).catch(console.error);};Services.obs.addObserver(ready,'browser-delayed-startup-finished');window.addEventListener('unload',()=>{try{Services.obs.removeObserver(ready,'browser-delayed-startup-finished');}catch{}},{once:true});}
})();
