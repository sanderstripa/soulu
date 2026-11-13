const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync(require('node:path').join(__dirname,'../chrome/updates.js'),'utf8');
const tag='sona-preview-1.160.32',name='Sona-1.160.32-Preview-x64.exe';
const asset={id:1,name,size:100,digest:'sha256:'+'a'.repeat(64),browser_download_url:`https://github.com/sanderstripa/sona/releases/download/${tag}/${name}`};
let metadata={id:1367247790,full_name:'sanderstripa/sona'};
const calls=[],Sona={backend:{},dispatch:()=>{}};
vm.runInNewContext(code,{Sona,Services:{appinfo:{version:'160.0'}},AbortSignal,Date,URL,console,ChromeUtils:{importESModule(url){return url.includes('build-info')?{version:[1,160,31],name:'Sona Preview 1.160.31'}:{Downloads:{}};}},fetch:async url=>{calls.push(url);return {ok:true,json:async()=>metadata,text:async()=>JSON.stringify([{draft:false,tag_name:tag,assets:[asset]}])};}});
(async()=>{
 const result=await Sona.dispatch('browser.update.check');assert.equal(result.available.url,asset.browser_download_url);
 assert.equal(calls[0],'https://api.github.com/repositories/1367247790');assert.equal(calls[1],'https://api.github.com/repos/sanderstripa/sona/releases?per_page=50');
 assert.equal(Sona.updateCandidate([{draft:false,tag_name:tag,assets:[{...asset,browser_download_url:asset.browser_download_url.replace('/sanderstripa/','/foreign/')}]}]),null);
 metadata={id:999,full_name:'sanderstripa/sona'};await assert.rejects(()=>Sona.dispatch('browser.update.check'));
 console.log('PASS repository rename, immutable identity and foreign asset rejection');
})().catch(error=>{console.error(error);process.exitCode=1;});
