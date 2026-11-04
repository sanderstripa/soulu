/* Route the engine's preferences entry points into Soulu's existing settings. */
(()=>{
 function section(value){return /privacy|permission/i.test(value||'')?'sites':/search/i.test(value||'')?'search':'general';}
 window.openPreferences=(pane)=>Soulu.settings(section(pane));
 const switchTab=window.switchToTabHavingURI;if(switchTab)window.switchToTabHavingURI=function(uri,...args){if(/^about:preferences(?:[?#]|$)/i.test(typeof uri==='string'?uri:uri?.spec||'')){Soulu.settings(section(typeof uri==='string'?uri:uri.spec));return true;}return switchTab.call(this,uri,...args);};
 const original=window.openTrustedLinkIn;
 window.openTrustedLinkIn=function(url,where,params){if(/^about:preferences(?:[?#]|$)/i.test(String(url))){Soulu.settings(section(String(url)));return;}return original.call(this,url,where,params);};
 gBrowser.addTabsProgressListener({onLocationChange(browser,_progress,_request,location){if(!/^about:preferences(?:[?#]|$)/i.test(location.spec))return;browser.stop();browser.loadURI(Services.io.newURI(Soulu.native.homeURL),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});Soulu.settings(section(location.spec));}});
})();
