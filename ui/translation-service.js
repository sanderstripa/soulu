(() => {
  'use strict';
  const normalize=lang=>String(lang||'').toLowerCase().split(/[-_]/)[0];
  const registry=window.SouluTranslationModels;
  const pairs=registry.pairs;
  const resolve=(from,to)=>{
    from=normalize(from);to=normalize(to);
    if(from===to)return [];
    const find=(a,b)=>pairs.find(p=>p.from===a&&p.to===b);
    const direct=find(from,to);if(direct)return [direct];
    const first=find(from,'en'),second=find('en',to);
    if(first&&second)return [first,second];
    throw Error('unsupported');
  };
  let database;
  function db(){return database??=new Promise((resolve,reject)=>{
    const request=indexedDB.open('soulu-translation-models',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('models');
    request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(Error('cache'));
  });}
  async function cached(key){const database=await db();return new Promise((resolve,reject)=>{
    const request=database.transaction('models').objectStore('models').get(key);
    request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(Error('cache'));
  });}
  async function store(key,value){const database=await db();return new Promise((resolve,reject)=>{
    const tx=database.transaction('models','readwrite');tx.objectStore('models').put(value,key);
    tx.oncomplete=()=>resolve();tx.onerror=()=>reject(Error('cache'));
  });}
  async function verify(bytes,file){
    if(!(bytes instanceof ArrayBuffer)||bytes.byteLength!==file.size)return false;
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
    return hash===file.sha256;
  }
  async function load(file,signal,status){
    let bytes=await cached(file.sha256);
    if(bytes&&await verify(bytes,file))return bytes;
    if(signal.aborted)throw Error('cancelled');
    const url=new URL(file.url);
    if(url.protocol!=='https:'||url.hostname!=='storage.googleapis.com'||
       !url.pathname.startsWith('/moz-fx-translations-data--303e-prod-translations-data/models/'))throw Error('registry');
    status('downloading');
    const response=await fetch(url,{credentials:'omit',referrerPolicy:'no-referrer',signal});
    if(!response.ok||Number(response.headers.get('Content-Length'))>100000000)throw Error('download');
    bytes=await response.arrayBuffer();
    const head=new Uint8Array(bytes,0,Math.min(2,bytes.byteLength));
    if(head[0]===0x1f&&head[1]===0x8b){
      const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
      bytes=await new Response(stream).arrayBuffer();
    }
    if(signal.aborted)throw Error('cancelled');
    if(!await verify(bytes,file))throw Error('integrity');
    await store(file.sha256,bytes);return bytes;
  }
  class Backing extends window.SouluBergamot.TranslatorBacking {
    constructor(signal,status){super({cacheSize:4096,pivotLanguage:'en',useNativeIntGemm:false});this.signal=signal;this.status=status;}
    async loadModelRegistery(){return pairs;}
    async loadTranslationModel({from,to}){
      const pair=pairs.find(p=>p.from===from&&p.to===to);if(!pair)throw Error('unsupported');
      const buffers=await Promise.all(['model','lexicalShortlist','vocab'].map(key=>load(pair.files[key],this.signal,this.status)));
      return {model:buffers[0],shortlist:buffers[1],vocabs:[buffers[2]],config:{}};
    }
  }
  class LocalTranslator {
    constructor(status=()=>{}){
      this.controller=new AbortController();this.status=status;
      this.engine=new window.SouluBergamot.BatchTranslator({workers:1,batchSize:8},new Backing(this.controller.signal,status));
    }
    async translate(from,to,text,jobKey){
      if(this.controller.signal.aborted)throw Error('cancelled');
      resolve(from,to);if(normalize(from)===normalize(to))return text;
      const result=await this.engine.translate({from:normalize(from),to:normalize(to),text,html:false,jobKey});
      if(this.controller.signal.aborted)throw Error('cancelled');return result.target.text;
    }
    cancel(jobKey){this.engine.remove(request=>request.jobKey===jobKey);}
    delete(){this.controller.abort();this.engine.delete();}
  }
  function detect(text,hint=''){
    if(String(text).trim().length<40)return normalize(hint);
    const results=window.SouluLanguage.detectAll(text);
    return results.length&&results[0].accuracy>=0.2?results[0].lang:'';
  }
  window.SouluTranslate={normalize,resolve,verify,detect,LocalTranslator,pairs};
})()
