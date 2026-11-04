/**
 * Settings support hooks for the Soulu Gecko preview.
 * These patches run inside every browser window and repair integration
 * points that a stock Firefox does not expose.
 */
(function(){
  // Force the Settings search to include hidden Soulu categories.
  const restore=()=>{try{const s=document.getElementById('categories');if(s&&!s.hidden&&s.querySelectorAll('.category[hidden]').length){s.querySelectorAll('.category[hidden]').forEach(n=>n.hidden=false);}}catch{}};
  restore();setInterval(restore,1000);
})();
(function(){
  // Make the Settings search field respond to Enter with a search engine.
  const restore=()=>{try{const f=document.getElementById('searchInput');if(f&&!f.__souluEnter){f.__souluEnter=true;f.addEventListener('keydown',ev=>{if(ev.key==='Enter'){ev.preventDefault();try{let q=f.value||'';if(!q)return;const se=Services.search.defaultEngine;const u=se.getSubmission(q,null,'homepage');if(u)openWebLinkIn(u.uri.spec,'tab');}catch{}}});}}catch{}};
  restore();setInterval(restore,1000);
})();
(function(){
  // Preview 9: the Settings import entry must always open the native wizard.
  // The previous hook called a browserShell method that never existed in the
  // Gecko build, so the click silently failed and bounced back to Settings.
  let hooked=false;
  const hook=()=>{
    if(hooked)return;
    const s=window.souluBrowserImport;
    if(!s||s.__souluNativeImport)return;
    s.__souluNativeImport=true;
    s.open=()=>cefQuery({request:JSON.stringify({action:'browser.import.native'}),onSuccess:()=>{},onFailure:(_,e)=>{const n=document.getElementById('actionMessage');if(n)n.textContent=String(e);}});
    hooked=true;
  };
  hook();setInterval(hook,500);
})();
