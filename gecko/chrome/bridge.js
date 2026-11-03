/* Unprivileged application document. The actor accepts only four installed file URLs. */
(() => {
 if(location.protocol!=='file:')throw Error('Soulu local UI required');
 let serial=0;const pending=new Map();
 window.cefQuery=({request,onSuccess,onFailure})=>{const id=++serial;pending.set(id,{onSuccess,onFailure});window.dispatchEvent(new CustomEvent('SouluRequest',{bubbles:true,detail:JSON.stringify({id,request})}));};
 window.addEventListener('SouluResponse',event=>{const {id,value,error}=JSON.parse(event.detail);const call=pending.get(id);if(!call)return;pending.delete(id);error?call.onFailure(1,error):call.onSuccess(JSON.stringify(value??null));});
 window.addEventListener('SouluEmit',event=>{const {name,value}=JSON.parse(event.detail);if(name==='dismissSuggestions')document.querySelectorAll('.suggestions.visible').forEach(n=>n.classList.remove('visible'));window.__souluEmit?.(name,value);if(name==='home')window.souluHomeApply?.(value);});
})();
