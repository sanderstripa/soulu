/* Soulu import service. Only native data migrators run behind this interface. */
(()=>{
const {shared,isPrivate}=Soulu.backend;
const {MigrationUtils}=ChromeUtils.importESModule('moz-src:///browser/components/migration/MigrationUtils.sys.mjs');
const names={chrome:'Google Chrome','chrome-beta':'Google Chrome Beta',chromium:'Chromium','chromium-edge':'Microsoft Edge',brave:'Brave',opera:'Opera','opera-gx':'Opera GX',vivaldi:'Vivaldi',firefox:'Другой браузер Mozilla'};
const labels={BOOKMARKS:'Закладки',HISTORY:'История',PASSWORDS:'Пароли',FORMDATA:'Автозаполнение',COOKIES:'Файлы cookie',SESSION:'Открытые вкладки',PAYMENT_METHODS:'Платёжные данные',EXTENSIONS:'Расширения',OTHERDATA:'Другие данные'};
let sources=new Map(),busy=false;
async function discover(){
 if(isPrivate)throw Error('Импорт недоступен в инкогнито.');
 const result=[];sources.clear();
 for(const key of MigrationUtils.availableMigratorKeys){
  if(key.includes('internal-testing')||key.includes('selectable-profile'))continue;
  try{
   const migrator=await MigrationUtils.getMigrator(key);if(!migrator||migrator.startupOnlyMigrator)continue;
   const profiles=await migrator.getSourceProfiles();
   for(const profile of profiles?.length?profiles:[null]){
    const mask=await migrator.getMigrateData(profile),types=Object.keys(labels).filter(type=>mask&MigrationUtils.resourceTypes[type]);if(!types.length)continue;
    const id=Services.uuid.generateUUID().toString();sources.set(id,{migrator,profile,mask});
    result.push({id,name:names[key]||key.replace(/firefox/ig,'Soulu'),profile:profile?.name||profile?.id||'Основной',types:types.map(key=>({key,label:labels[key]}))});
   }
  }catch(error){console.error('Soulu import source',key,String(error));}
 }
 return {sources:result};
}
const base=Soulu.dispatch;
Soulu.dispatch=async(action,payload,source)=>{
 if(action==='browser.import.sources'||action==='browser.import.browsers'||action==='browser.import.native')return discover();
 if(action!=='browser.import.run')return base(action,payload,source);
 if(isPrivate)throw Error('Импорт недоступен в инкогнито.');
 if(busy)throw Error('Дождитесь завершения текущего импорта.');
 const entry=sources.get(payload?.id);if(!entry)throw Error('Выберите браузер заново.');
 if(!Array.isArray(payload.types)||!payload.types.length||payload.types.some(t=>!Object.hasOwn(labels,t)))throw Error('Выберите данные для импорта.');
 const mask=payload.types.reduce((v,t)=>v|MigrationUtils.resourceTypes[t],0)&entry.mask;if(!mask)throw Error('Выбранные данные недоступны.');
 busy=true;const results=[];
 try{
  await entry.migrator.migrate(mask,false,entry.profile,(type,success,detail,available)=>{results.push({type:Object.keys(labels).find(k=>MigrationUtils.resourceTypes[k]===type),success:!!success,available});});
  await Soulu.bookmarks('invalidate');await Soulu.dispatch('browser.bookmarks.get');
  return {ok:results.length>0&&results.every(r=>r.success),results};
 }finally{busy=false;}
};
})();
