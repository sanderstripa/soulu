/* Use the unchanged, AMO-signed Firefox VOT extension, enabled only by consent. */
(()=>{
const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');
const {shared,save}=Soulu.backend,id='vot-ext@firefox',base=Soulu.dispatch;
async function candidate(){const file=Services.dirsvc.get('GreD',Ci.nsIFile);for(const p of ['soulu','optional','vot-1.12.6.xpi'])file.append(p);if(!file.exists())throw Error('Компонент VOT отсутствует в сборке.');const install=await AddonManager.getInstallForFile(file);if(install.addon?.id!==id||install.addon?.version!=='1.12.6'||install.addon?.signedState<2)throw Error('Подпись или версия VOT не прошла проверку Firefox.');return install;}
Soulu.dispatch=async(action,payload,source)=>{
 if(action==='browser.vot.status'){const addon=await AddonManager.getAddonByID(id);return {installed:!!addon,enabled:!!addon?.isActive,version:addon?.version||'1.12.6',externalService:'Яндекс / серверы VOT',permissions:addon?.userPermissions||((await candidate()).addon.userPermissions)};}
 if(action==='browser.vot.install'){
  if(Soulu.backend.isPrivate)throw Error('Установка выполняется в обычном окне.');if(!payload?.consent||!source?.gesture||Date.now()-source.gesture.at>2000)throw Error('Подтвердите разрешения VOT кнопкой установки.');
  const install=await candidate();const result=await new Promise((resolve,reject)=>{install.addListener({onInstallEnded(_i,addon){resolve(addon);},onInstallFailed(i){reject(Error('Firefox отказал в установке VOT: '+i.error));},onDownloadFailed(i){reject(Error('Не удалось прочитать VOT: '+i.error));}});install.install();});
  shared.config.settings.videoTranslationEnabled=!!result.isActive;await save();return {installed:true,version:result.version};
 }
 if(action==='browser.vot.setEnabled'){const addon=await AddonManager.getAddonByID(id);if(!addon)throw Error('Сначала установите VOT и подтвердите разрешения.');payload.enabled?await addon.enable():await addon.disable();shared.config.settings.videoTranslationEnabled=!!addon.isActive;await save();return {enabled:addon.isActive};}
 if(action==='settings.save'){
  const addon=await AddonManager.getAddonByID(id);const enabled=!!payload.settings?.videoTranslationEnabled;
  if(enabled&&!addon)throw Error('Сначала установите VOT через «Настройки перевода YouTube».');
  const result=await base(action,payload,source);if(result.ok&&addon&&enabled!==addon.isActive){enabled?await addon.enable():await addon.disable();}return result;
 }
 return base(action,payload,source);
};
})();
