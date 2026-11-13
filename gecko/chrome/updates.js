/* Voluntary Gecko-channel release checks. Download/verify only; never replace live files. */
(()=>{
const {IOUtils,PathUtils}=Sona.backend,{Downloads}=ChromeUtils.importESModule('resource://gre/modules/Downloads.sys.mjs');
let available=null,checkedAt=0,busy=false;const base=Sona.dispatch,{version:current,name:currentName}=ChromeUtils.importESModule('chrome://sona/content/build-info.sys.mjs'),repo='https://api.github.com/repos/sanderstripa/soulu';
function candidate(releases){
 const newer=(a,b)=>{for(let i=0;i<3;i++){if(a[i]!==b[i])return a[i]>b[i];}return false;};
 const choices=[];
 for(const r of releases){
  if(r.draft)continue;
  const modern=r.tag_name?.match(/^sona-preview-(\d+)\.(\d+)\.(\d+)$/);
  const legacy=r.tag_name?.match(/^sona-preview-(\d+)(?:-update-(\d+))?$/);
  if(!modern&&!legacy)continue;
  const version=modern?modern.slice(1).map(Number):[0,+legacy[1],+(legacy[2]||0)];
  if(!newer(version,current))continue;
  const stem=modern?'Sona-'+version.join('.')+'-Preview':`Sona-0.${version[1]}.${version[2]}-Preview`;
  const asset=r.assets?.find(a=>a.name===stem+'-x64.exe')||r.assets?.find(a=>a.name===stem+'-Setup-win64.exe')||r.assets?.find(a=>a.name===stem+'-win64.zip');
  if(!asset||asset.size<=0||asset.size>450*1024*1024||!/^sha256:[a-f0-9]{64}$/.test(asset.digest||''))continue;
  const name=asset.name,expected='https://github.com/sanderstripa/soulu/releases/download/'+r.tag_name+'/'+name;
  if(asset.browser_download_url!==expected)continue;
  choices.push({id:asset.id,tag:r.tag_name,version,name,kind:name.endsWith('.exe')?'installer':'zip',size:asset.size,digest:asset.digest.slice(7),url:expected,notes:String(r.body||'').slice(0,5000),release:'https://github.com/sanderstripa/soulu/releases/tag/'+r.tag_name});
 }
 return choices.sort((a,b)=>newer(a.version,b.version)?-1:newer(b.version,a.version)?1:0)[0]||null;
}

async function check(){const response=await fetch(repo+'/releases?per_page=50',{headers:{Accept:'application/vnd.github+json'},credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(15000)});if(!response.ok)throw Error('GitHub: HTTP '+response.status);const text=await response.text();if(text.length>3*1024*1024)throw Error('Слишком большой ответ GitHub');available=candidate(JSON.parse(text));checkedAt=Date.now();return {current:currentName,gecko:Services.appinfo.version,available};}
Sona.updateCandidate=candidate;
Sona.dispatch=async(action,payload,source)=>{
 if(action==='browser.update.check')return check();
 if(action==='browser.update.download'){
  if(busy)throw Error('Обновление уже загружается.');if(!source?.gesture||Date.now()-source.gesture.at>2000||!payload?.consent)throw Error('Подтвердите загрузку обновления.');
  if(Date.now()-checkedAt>600000)await check();if(!available||payload.id!==available.id)throw Error('Список обновлений изменился. Повторите проверку.');const item={...available};busy=true;
  const directory=await IOUtils.createUniqueDirectory(PathUtils.tempDir,'Sona-Update-'),target=PathUtils.join(directory,item.name);
  try{const d=await Downloads.createDownload({source:{url:item.url,isPrivate:Sona.backend.isPrivate},target});await (await Downloads.getList(Downloads.ALL)).add(d);await d.start();
   if((await IOUtils.stat(target)).size!==item.size||await IOUtils.computeHexDigest(target,'sha256')!==item.digest)throw Error('Контрольная сумма GitHub не совпала.');
   if(item.kind==='installer'){
    const header=await IOUtils.read(target,{maxBytes:64});if(header.length!==64||header[0]!==77||header[1]!==90)throw Error('Некорректный установщик Windows.');
    const offset=new DataView(header.buffer,header.byteOffset,header.byteLength).getUint32(60,true);if(offset<64||offset>item.size-26)throw Error('Некорректный PE-заголовок.');
    const bytes=await IOUtils.read(target,{offset,maxBytes:26}),pe=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);if(bytes.length!==26||pe.getUint32(0,true)!==0x4550||pe.getUint16(4,true)!==0x8664||pe.getUint16(24,true)!==0x20b)throw Error('Установщик не предназначен для Windows x64.');
    return {verified:true,name:item.name,path:target,kind:'installer',automaticInstall:false};
   }
   const file=Cc['@mozilla.org/file/local;1'].createInstance(Ci.nsIFile);file.initWithPath(target);const zip=Cc['@mozilla.org/libjar/zip-reader;1'].createInstance(Ci.nsIZipReader);zip.open(file);
   try{const stream=zip.getInputStream('BUILD.json'),input=Cc['@mozilla.org/scriptableinputstream;1'].createInstance(Ci.nsIScriptableInputStream);input.init(stream);const bytes=input.read(65536);input.close();const build=JSON.parse(bytes);if(build.channel!=='gecko-preview'||build.platform!=='win64'||build.name!==`Sona Preview ${item.version.join(".")}`)throw Error('Неподходящий канал или платформа пакета.');}finally{zip.close();}
   return {verified:true,name:item.name,path:target,automaticInstall:false};
  }catch(error){await IOUtils.remove(target,{ignoreAbsent:true}).catch(()=>{});throw error;}finally{busy=false;}
 }
 return base(action,payload,source);
};
})();

