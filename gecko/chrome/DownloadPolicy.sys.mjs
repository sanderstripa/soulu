import {state} from 'chrome://sona/content/shared.sys.mjs';
import {Integration} from 'resource://gre/modules/Integration.sys.mjs';
import {PrivateBrowsingUtils} from 'resource://gre/modules/PrivateBrowsingUtils.sys.mjs';
let installed=false;
export function install(){if(installed)return;installed=true;Integration.downloads.register(base=>({__proto__:base,async shouldBlockForParentalControls(download){
 if(await base.shouldBlockForParentalControls(download))return true;
 let host='';try{host=new URL(download.source.referrerInfo?.originalReferrer?.spec||download.source.url).hostname;}catch{}
 const value=state.config?.rules.sites[host]?.downloads??state.config?.rules.defaults.downloads??1;if(Number(value)===0)return false;if(Number(value)===2)return true;
 const win=[...Services.wm.getEnumerator('navigator:browser')].find(w=>!w.closed&&PrivateBrowsingUtils.isWindowPrivate(w)===!!download.source.isPrivate);if(!win)return true;
 return !Services.prompt.confirm(win,'Sona — загрузка файла','Разрешить загрузку файла с '+host+'?');
}}));}
