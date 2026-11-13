/* Unprivileged application document. The actor accepts only four installed file URLs. */
(() => {
 if(location.protocol!=='file:')throw Error('Sona local UI required');
 let serial=0;const pending=new Map();
 window.cefQuery=({request,onSuccess,onFailure})=>{const id=++serial;pending.set(id,{onSuccess,onFailure});window.dispatchEvent(new CustomEvent('SonaRequest',{bubbles:true,detail:JSON.stringify({id,request})}));};
 window.addEventListener('SonaResponse',event=>{const {id,value,error}=JSON.parse(event.detail);const call=pending.get(id);if(!call)return;pending.delete(id);error?call.onFailure(1,error):call.onSuccess(JSON.stringify(value??null));});
 window.addEventListener('SonaEmit',event=>{const {name,value}=JSON.parse(event.detail);if(name==='dismissSuggestions')document.querySelectorAll('.suggestions.visible').forEach(n=>n.classList.remove('visible'));if(name==='voicePhase')window.sonaHomeVoicePhase?.(value);window.__sonaEmit?.(name,value);if(name==='extensions')window.dispatchEvent(new CustomEvent('SonaExtensionsChanged',{detail:value}));if(name==='home')window.sonaHomeApply?.(value);if(name==='pageGlass'){const apply=()=>document.body?.toggleAttribute('data-native-page-glass',!!value);if(document.body)apply();else addEventListener('DOMContentLoaded',apply,{once:true});}});
})();

addEventListener('DOMContentLoaded',async()=>{if(!location.pathname.endsWith('/index.html'))return;const close=document.querySelector('.overview-close');if(close)close.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg>';await window.sonaInitialStateReady;await window.sonaTypographyReady;document.documentElement.getBoundingClientRect();window.cefQuery({request:JSON.stringify({action:'window.frontendReady'}),onSuccess(){},onFailure(){}});},{once:true});
