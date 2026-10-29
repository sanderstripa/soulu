const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..'),bootstrap=fs.readFileSync(path.join(root,'ui/video-runtime.js'),'utf8');
const {webcrypto}=require('node:crypto');
const tick=()=>new Promise(r=>setImmediate(r));
async function test(enabled){
 let api,cache={responseLanguage:'ru'},watch;const calls=[];
 const context=vm.createContext({console,Promise,Blob,Headers,TextDecoder,TextEncoder,ArrayBuffer,Uint8Array,structuredClone,atob,btoa,setTimeout,clearTimeout,URL,URLSearchParams,crypto:webcrypto,window:{}});
 context.window.__souluVideoNative=(raw,callback)=>{const data=JSON.parse(raw);calls.push(data);if(data.op==='watch'){watch=callback;return;}let result={ok:true};
  if(data.op==='init')result={ok:true,enabled,values:cache,version:'1.12.3'};
  if(data.op==='set')cache[data.key]=data.value;
  if(data.op==='xhr')result={ok:true,status:200,body:btoa('translated'),url:data.url,headers:'Content-Type: text/plain',contentType:'text/plain'};
  callback(JSON.stringify(result));
 };
 vm.runInContext('('+bootstrap+')',context)(function(GM,...rest){api={GM,rest}});
 await tick();assert.equal(!!api,enabled);assert.equal(context.window.__souluVideoNative,undefined);
 if(!enabled){assert.equal(calls.length,1);return}
 assert.equal(await api.GM.getValue('responseLanguage'),'ru');await api.GM.setValue('autoTranslate',true);assert.equal(cache.autoTranslate,true);
 let remote;api.GM.addValueChangeListener('responseLanguage',(k,old,value,flag)=>{remote={old,value,flag}});
 watch(JSON.stringify({ok:true,values:{...cache,responseLanguage:'en'}}));assert.equal(await api.GM.getValue('responseLanguage'),'en');assert.deepEqual(remote,{old:'ru',value:'en',flag:true});
 const r=await api.GM.xmlHttpRequest({url:'https://api.browser.yandex.ru/test',method:'POST',data:new Uint8Array([0,255,128]).buffer,responseType:'arraybuffer'});
 assert.equal(new TextDecoder().decode(r.response),'translated');const req=calls.find(c=>c.op==='xhr');assert.equal(req.data,'AP+A');assert.equal(req.binary,true);
 await api.GM.deleteValue('autoTranslate');assert.equal(await api.GM.getValue('autoTranslate',false),false);
}
(async()=>{
 for(const name of ['settings-video.js','settings-weather.js','settings-components.js','home.js','settings.js','renderer.js','vpn/popup.js'])new vm.Script(fs.readFileSync(path.join(root,'ui',name),'utf8'),{filename:name});
 new vm.Script('(function(GM,GM_getValue,GM_setValue,GM_deleteValue,GM_listValues,GM_addStyle,GM_info,GM_xmlhttpRequest,GM_notification){'+fs.readFileSync(path.join(root,'ui/third_party/vot/vot.user.js'),'utf8')+'})');
 await test(false);await test(true);console.log('PASS: pinned VOT parses; runtime enable gate, private GM storage, remote changes and binary network payload');
})().catch(e=>{console.error(e);process.exitCode=1});
