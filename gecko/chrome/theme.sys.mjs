// One application theme, including file-process UI and native chrome.
export function resolveTheme(setting='system'){
 if(setting==='dark'||setting==='light')return setting;
 if(Services.appinfo.OS==='WINNT'){let key;try{
  key=Cc['@mozilla.org/windows-registry-key;1'].createInstance(Ci.nsIWindowsRegKey);
  key.open(Ci.nsIWindowsRegKey.ROOT_KEY_CURRENT_USER,'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',Ci.nsIWindowsRegKey.ACCESS_READ);
  return key.readIntValue('AppsUseLightTheme')===0?'dark':'light';
 }catch{}finally{key?.close();}}
 return Services.prefs.getIntPref('ui.systemUsesDarkTheme',0)===1?'dark':'light';
}
