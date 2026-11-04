/**
 * Soulu integration bridge (Gecko preview).
 * Exposes the CEF-compatible Soulu API to the runtime and wires cefQuery to
 * the pinned Firefox implementation.
 */
const Soulu = window.Soulu = {
  version: 'gecko-preview',
  tabs: {
    create: function(o){ o = o || {}; const url = o.url || 'about:blank';
      try { gBrowser.addTab(url); return {id: Date.now()}; } catch(e){ console.error('Soulu tabs.create failed', e); return {id: 0}; } },
    update: function(id, o){ try { gBrowser.selectedTab = gBrowser.tabs[parseInt(id,10) || 0]; return {ok:true}; } catch(e){ return {ok:false}; } },
    remove: function(id){ try { gBrowser.removeTab(gBrowser.tabs[parseInt(id,10) || 0]); return {ok:true}; } catch(e){ return {ok:false}; } },
    query: function(){ try { return gBrowser.tabs.map(function(t, i){ return {id: i, url: t.linkedBrowser.currentURI.spec, title: t.label}; }); } catch(e){ return []; } }
  },
  window: {
    minimize: function(){ try { window.minimize(); } catch(e){} },
    maximize: function(){ try { if (window.windowState === window.STATE_MAXIMIZED) { window.restore(); } else { window.maximize(); } } catch(e){} },
    close: function(){ try { window.close(); } catch(e){} },
    fullscreen: function(){ try { BrowserFullScreen(); } catch(e){} }
  },
  settings: function(path, params){ try { const win = Services.wm.getMostRecentWindow('mozilla:browser'); if (win) { win.openPreferences(path || '', params || {}); } } catch(e){ console.error('Soulu settings open failed', e); } },
  import: function(){ return cefQuery({request: JSON.stringify({action:'browser.import.native'})}); },
  privacy: { clearBrowsingData: function(o){ try { Sanitizer.sanitize(o && o.since ? ['history','cache','cookies'] : ['history','cache','cookies']); return {ok:true}; } catch(e){ return {ok:false, error:String(e)}; } } }
};

// ---- Soulu dispatch layer -------------------------------------------------
Soulu.dispatch = function(request, sender) {
  const action = request && request.action;
  const respond = function(payload) { return payload; };
  switch (action) {
      case 'runtime.info':{const info={soulu:{version:'gecko-preview'},app:{name:'Soulu',version:Services.appinfo.version},os:{name:Services.appinfo.OS}};return respond(info);}
      case 'browser.focused':{return respond({focused:document.hasFocus()});}
      case 'browser.quit':{try{goQuitApplication();}catch(error){}return respond({ok:true});}
      case 'browser.version':{return respond({version:'9',channel:'preview',impl:'gecko'});}
      case 'browser.state':{const s=Soulustate||null;return respond({state:s});}
      case 'tabs.query':{const arr=[];try{gBrowser.tabs.forEach(t=>{arr.push({id:t._tabId,title:t.label,url:t.linkedBrowser.currentURI.spec});});}catch(error){}return respond({tabs:arr});}
      case 'tabs.create':{try{openWebLinkIn((request.url||'about:blank'),'tab');}catch(error){}return respond({ok:true});}
      case 'tabs.close':{try{const n=parseInt(request.id,10);if(!isNaN(n)&&gBrowser.tabs[n])gBrowser.removeTab(gBrowser.tabs[n]);}catch(error){}return respond({ok:true});}
      case 'tabs.update':{try{const n=parseInt(request.id,10);if(!isNaN(n)&&gBrowser.tabs[n]){gBrowser.selectedTab=gBrowser.tabs[n];}}catch(error){}return respond({ok:true});}
      case 'window.open':{try{openWebLinkIn((request.url||'about:blank'),'window');}catch(error){}return respond({ok:true});}
      case 'window.state':{return respond({state:window.windowState===window.STATE_MAXIMIZED?'maximized':'normal'});}
      case 'window.minimize':{try{window.minimize();}catch(error){}return respond({ok:true});}
      case 'window.maximize':{try{window.maximize();}catch(error){}return respond({ok:true});}
      case 'window.close':{try{window.close();}catch(error){}return respond({ok:true});}
      case 'settings.open':{Soulu.settings('paneGeneral');return respond({ok:true});}
      case 'settings.open.path':{Soulu.settings(request.path||'');return respond({ok:true});}
      case 'search.query':{try{const url='https://duckduckgo.com/?q='+encodeURIComponent(request.query||'');openWebLinkIn(url,'tab');}catch(error){}return respond({ok:true});}
      case 'search.default':{try{Services.search.default=Services.search.getEngineByName(request.name||'DuckDuckGo');}catch(error){}return respond({ok:true});}
      case 'downloads.open':{try{Downloads.getDownloads().then(list=>{const win=BrowserWindowTracker.getTopWindow();if(win)win.DownloadsPanel.showPanel();});}catch(error){}return respond({ok:true});}
      case 'downloads.list':{return respond({downloads:[]});}
      case 'privacy.clear':{try{Sanitizer.sanitize(['history','cache','cookies']);}catch(error){}return respond({ok:true});}
      case 'adblock.state':{return respond({enabled:!!(window.SouluAdblock&&window.SouluAdblock.enabled)});}
      case 'adblock.set':{try{if(window.SouluAdblock)window.SouluAdblock.enabled=!!request.enabled;}catch(error){}return respond({ok:true});}
      case 'profile.list':{return respond({profiles:[]});}
      case 'profile.current':{return respond({profile:{name:'default',path:PathUtils.profileDir}});}
      case 'updates.check':{try{if(window.SouluUpdates)window.SouluUpdates.check(true);}catch(error){}return respond({ok:true});}
      case 'updates.state':{return respond({state:(window.SouluUpdates&&window.SouluUpdates.state)||'idle'});}
      case 'speech.transcribe':{return respond({ok:false,error:'not-available'});}
      case 'vpn.state':{return respond({enabled:false});}
      case 'extension.list':{return respond({extensions:[]});}
      case 'extension.enable':{return respond({ok:true});}
      case 'extension.disable':{return respond({ok:true});}
      case 'browser.import.native':{
        // Preview 9: verify the wizard window actually opened and focus it; a
        // lost dialog reads as a dead import button that just returns to Settings.
        const {MigrationUtils}=ChromeUtils.importESModule('moz-src:///browser/components/migration/MigrationUtils.sys.mjs');
        const known=new Set([...Services.wm.getEnumerator(null)]);
        const focusWizard=()=>{for(const w of Services.wm.getEnumerator(null)){if(known.has(w))continue;const uri=w.document?String(w.document.documentURI||''):'';if(uri.startsWith('chrome://browser/content/migration/')){try{w.focus();}catch(error){}return true;}}return false;};
        try{MigrationUtils.showMigrationWizard(window,{entrypoint:MigrationUtils.MIGRATION_ENTRYPOINTS.UNKNOWN});}catch(error){console.error('Soulu migration wizard',String(error));}
        window.setTimeout(()=>{if(!focusWizard()){try{MigrationUtils.showMigrationWizard(window,{entrypoint:MigrationUtils.MIGRATION_ENTRYPOINTS.UNKNOWN});}catch(error){console.error('Soulu migration wizard retry',String(error));}window.setTimeout(()=>focusWizard(),1500);}},500);
        return respond({opened:true});
      }
      default:{return respond({ok:false,error:'unknown-action'});}
  }
};

// Bridge cefQuery to the dispatch layer so the Soulu UI can call native code
// through the same protocol used by the CEF build.
(function(){
  window.cefQuery = function(o) {
    try {
      const request = JSON.parse(o.request);
      const result = Soulu.dispatch(request);
      if (o.onSuccess) { o.onSuccess(JSON.stringify(result)); }
      if (o.onFailure) { o.onFailure(0, ''); }
    } catch(e) {
      if (o.onFailure) { o.onFailure(-1, String(e)); }
    }
    return 0;
  };
})();

// Keep the Soulu UI in sync with the browser state.
(function(){
  window.addEventListener('load', function(){
    console.log('Soulu integration online');
  });
})();
