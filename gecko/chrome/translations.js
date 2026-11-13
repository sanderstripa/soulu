/* Native, local Gecko translation. Web pages receive no privileged bridge. */
(()=>{
 const base=Sona.dispatch;
 Sona.dispatch=async(action,payload,source)=>{
  if(!action.startsWith('browser.translate.'))return base(action,payload,source);
  const op=action.slice('browser.translate.'.length),browser=gBrowser.selectedBrowser;
  if(!/^https?:/.test(browser.currentURI.spec))throw Error('Перевод доступен для веб-страниц.');
  if(payload?.url&&payload.url!==browser.currentURI.spec)throw Error('Страница изменилась.');
  Services.prefs.setBoolPref('browser.translations.enable',true);
  let actor;
  try{actor=browser.browsingContext.currentWindowGlobal.getActor('Translations');}
  catch(error){
   // A file Home tab can retain a non-browsers message-manager group when it
   // becomes a web tab. Register the stock actors for isolated web documents,
   // without the legacy message-manager group restriction. No custom DOM bridge.
   if(!String(error).includes('No such JSWindowActor'))throw error;
   ChromeUtils.unregisterWindowActor('Translations');
   ChromeUtils.registerWindowActor('Translations',{parent:{esModuleURI:'resource://gre/actors/TranslationsParent.sys.mjs'},child:{esModuleURI:'resource://gre/actors/TranslationsChild.sys.mjs'},matches:['http://*/*','https://*/*'],allFrames:true,safeForUntrustedWebProcess:true});
   actor=browser.browsingContext.currentWindowGlobal.getActor('Translations');
  }
  if(op==='probe'||op==='status'){
   const languages=await actor.getLangTags(),state=actor.languageState;
   return {lang:languages?.docLangTag?.language||languages?.docLangTag||languages?.htmlLangAttribute||'',translated:!!state?.requestedLanguagePair,visible:!!state?.hasVisibleChange,error:state?.error?.message||null};
  }
  if(op==='translate'){
   const from=String(payload.from||''),to=String(payload.to||'ru');
   if(!/^[a-z]{2,3}(-[A-Za-z]{2,4})?$/.test(from)||!['ru','en'].includes(to))throw Error('Выберите язык страницы и перевода.');
   await actor.translate({sourceLanguage:from,targetLanguage:to},false);return {ok:true};
  }
  if(op==='restore'){actor.restorePage();return {ok:true};}
  throw Error('Unsupported translation command');
 };
})();
