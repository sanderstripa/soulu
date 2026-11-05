import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const [candidate,baseline]=process.argv.slice(2),report={passed:false,checks:{}};
function check(name,value){report.checks[name]=!!value;console.log(name,!!value);assert.ok(value,name);}
function chrome(root,file){return fs.readFileSync(path.join(root,'engine/soulu/chrome',file),'utf8');}
function build(root){return JSON.parse(fs.readFileSync(path.join(root,'BUILD.json'),'utf8'));}
async function presentsWithoutGPU(root){
 const source=chrome(root,'window-controls.sys.mjs');
 const program=source.slice(source.indexOf('export function prepareStartup(')).replaceAll('export function ','function ');
 const native={visible:false,cloaked:false,queries:0};
 const win={closed:false,Soulu:{ready:true},__souluStartupPresentation:{},setTimeout(){return 1;},clearTimeout(){},focus(){},Event:class{},dispatchEvent(){},document:{documentElement:{hasAttribute(){return true;}},getElementById(){return {frameLoader:{remoteTab:{renderLayers:false,hasLayers:false}},browsingContext:{currentWindowGlobal:{getActor(){return {sendQuery(){native.queries++;return new Promise(()=>{});}};}}}};}}};
 win.docShell={treeOwner:{QueryInterface(){return {getInterface(){return {set visibility(value){native.visible=value;}};}};}}};
 const timers={setTimeout(fn){return 1;},clearTimeout(){}};
 const context={win,console,Date,Promise,Ci:{nsIInterfaceRequestor:1,nsIBaseWindow:2},Services:{appinfo:{OS:'WINNT'}},taskbarPending(){},cloak(_win,enabled){native.cloaked=enabled;return {};},ChromeUtils:{importESModule(uri){return uri.includes('lifecycle')?{consolidateAutomaticStart(){}}:timers;}}};
 vm.runInNewContext(program+'\nprepareStartup(win);revealStartup(win);',context);
 await Promise.resolve();await Promise.resolve();
 return {...native,presented:native.visible&&!native.cloaked&&!win.__souluStartupHidden};
}
function updater(root,info){
 const source=chrome(root,'updates.js'),Soulu={backend:{IOUtils:{},PathUtils:{}},dispatch(){}};
 vm.runInNewContext(source,{Soulu,ChromeUtils:{importESModule(uri){return uri.includes('build-info')?info:{Downloads:{}};}},Services:{appinfo:{version:'159.0'}},console,Date,URL,AbortSignal,Uint8Array,DataView});
 return Soulu.updateCandidate;
}
function release(minor,patch=0){const tag=`soulu-preview-${minor}${patch?'-update-'+patch:''}`,name=`Soulu-0.${minor}.${patch}-Preview-Setup-win64.exe`;return {draft:false,tag_name:tag,assets:[{id:minor*100+patch,name,size:271000000,digest:'sha256:'+'a'.repeat(64),browser_download_url:`https://github.com/sanderstripa/soulu/releases/download/${tag}/${name}`}],body:''};}
try{
 const old=await presentsWithoutGPU(baseline),next=await presentsWithoutGPU(candidate);
 check('preview15_stalls_when_compositor_never_acknowledges',!old.presented&&old.queries>0);
 check('preview16_presents_without_compositor_acknowledgement',next.presented&&next.queries===0);
 const info=await import(pathToFileURL(path.resolve(candidate,'engine/soulu/chrome/build-info.sys.mjs')).href);
 const expected=[...build(candidate).name.match(/0\.(\d+)\.(\d+)/)].slice(1).map(Number);
 check('updater_uses_exact_package_version',info.name===build(candidate).name&&JSON.stringify(info.version)===JSON.stringify(expected));
 const select=updater(candidate,info),minor=info.version[0],patch=info.version[1];
 const oldSelect=updater(baseline,{name:build(baseline).name,version:[15,0]});
 check('preview15_reproduces_self_update_offer',oldSelect([release(15)])!==null);
 check('same_version_is_not_an_update',select([release(minor,patch)])===null);
 check('older_version_is_not_an_update',select([release(minor-1)])===null);
 check('newer_preview_is_an_update',select([release(minor+1)])?.tag===`soulu-preview-${minor+1}`);
 check('newer_patch_is_an_update',select([release(minor,patch+1)])?.version[1]===patch+1);
 report.passed=true;
}finally{
 fs.mkdirSync('soulu16-checks',{recursive:true});fs.writeFileSync('soulu16-checks/regressions16.json',JSON.stringify(report,null,2));
}
