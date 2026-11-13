/* Route the engine's preferences entry points into Sona's existing settings. */
(()=>{
 function section(value){if(/addons/.test(value||''))return 'extensions';if(/logins/.test(value||''))return 'passwords';return /privacy|permission/i.test(value||'')?'sites':/search/i.test(value||'')?'search':'general';}
 window.openPreferences=(pane)=>Sona.settings(section(pane));
 const switchTab=window.switchToTabHavingURI;if(switchTab)window.switchToTabHavingURI=function(uri,...args){if(/^about:(?:preferences|settings|logins)(?:[?#]|$)/i.test(typeof uri==='string'?uri:uri?.spec||'')){Sona.settings(section(typeof uri==='string'?uri:uri.spec));return true;}return switchTab.call(this,uri,...args);};
 const original=window.openTrustedLinkIn;
 window.openTrustedLinkIn=function(url,where,params){if(/^about:(?:preferences|settings|logins)(?:[?#]|$)/i.test(String(url))){Sona.settings(section(String(url)));return;}return original.call(this,url,where,params);};
 gBrowser.addTabsProgressListener({onLocationChange(browser,_progress,_request,location){if(!/^about:(?:preferences|settings|logins)(?:[?#]|$)/i.test(location.spec))return;browser.stop();browser.loadURI(Services.io.newURI(Sona.native.homeURL),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});Sona.settings(section(location.spec));}});
})();
