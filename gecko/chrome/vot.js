/* Use the unchanged, AMO-signed Firefox VOT extension, enabled only by consent. */
(()=>{
const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');
const {shared,save}=Sona.backend,id='vot-ext@firefox',base=Sona.dispatch;
async function builtin(){await candidate();await AddonManager.installBuiltinAddon('resource://sona-vot/');const addon=await AddonManager.getAddonByID(id);if(!addon?.isBuiltin)throw Error('Компонент перевода не зарегистрирован как встроенный.');return addon;}
async function candidate(){const file=Services.dirsvc.get('GreD',Ci.nsIFile);for(const p of ['sona','optional','vot-1.12.6.xpi'])file.append(p);if(!file.exists())throw Error('Компонент VOT отсутствует в сборке.');const install=await AddonManager.getInstallForFile(file);if(install.addon?.id!==id||install.addon?.version!=='1.12.6'||install.addon?.signedState<2)throw Error('Подпись или версия VOT не прошла проверку Sona.');return install;}
Sona.votReady=(async()=>{const existing=await AddonManager.getAddonByID(id);const enabled=existing?!existing.userDisabled:shared.config.settings.videoTranslationEnabled!==false;const component=existing?.isBuiltin?existing:await builtin();if(enabled&&component.userDisabled)await component.enable();if(!enabled&&!component.userDisabled)await component.disable();if(shared.config.settings.videoTranslationEnabled!==enabled){shared.config.settings.videoTranslationEnabled=enabled;await save();}})().catch(error=>{Sona.votError=String(error);console.error(error);});
Sona.dispatch=async(action,payload,source)=>{
 if(action.startsWith('browser.vot.'))await Sona.votReady;
 if(action==='browser.vot.status'){const addon=await AddonManager.getAddonByID(id);return {installed:!!addon,enabled:!!addon?.isActive,version:addon?.version||'1.12.6',externalService:'Яндекс / серверы VOT',permissions:addon?.userPermissions||((await candidate()).addon.userPermissions)};}
 if(action==='browser.vot.install'){
  if(Sona.backend.isPrivate)throw Error('Установка выполняется в обычном окне.');if(!payload?.consent||!source?.gesture||Date.now()-source.gesture.at>2000)throw Error('Подтвердите разрешения VOT кнопкой установки.');
  const result=await builtin();
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
