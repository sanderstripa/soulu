/* Remove the obsolete prototype blocker only after native Rust AdBlock is ready. */
(()=>{
 const {AddonManager}=ChromeUtils.importESModule('resource://gre/modules/AddonManager.sys.mjs');
 const {shared,save}=Soulu.backend;
 Soulu.extensionMigration=(async()=>{
  if(!Soulu.adblock?.status()?.ready)return;
  const legacy=await AddonManager.getAddonByID('uBlock0@raymondhill.net');
  if(legacy){await legacy.uninstall();shared.config.settings.legacyBlockerRemoved=true;await save();}
  if(!shared.config.settings.extensionMenuMigration){const bitwarden=await AddonManager.getAddonByID('{446900e4-71c2-419f-a6a7-df9c091e268b}');if(bitwarden&&bitwarden.userDisabled)await bitwarden.enable();shared.config.settings.extensionMenuMigration=true;await save();}
 })().catch(error=>{Soulu.extensionMigrationError=String(error);console.error(error);});
})();
