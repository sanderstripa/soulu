// Native Windows drag, identical to the existing CEF WM_NCLBUTTONDOWN path.
const {ctypes}=ChromeUtils.importESModule('resource://gre/modules/ctypes.sys.mjs');
let native;
export function beginDrag(){if(Services.appinfo.OS!=='WINNT')return false;if(!native){const dll=ctypes.open('user32.dll'),abi=(ctypes.winapi_abi||ctypes.default_abi);native={dll,foreground:dll.declare('GetForegroundWindow',abi,ctypes.uintptr_t),pid:dll.declare('GetWindowThreadProcessId',abi,ctypes.uint32_t,ctypes.uintptr_t,ctypes.uint32_t.ptr),release:dll.declare('ReleaseCapture',abi,ctypes.bool),send:dll.declare('SendMessageW',abi,ctypes.intptr_t,ctypes.uintptr_t,ctypes.uint32_t,ctypes.uintptr_t,ctypes.intptr_t)};}const hwnd=native.foreground(),pid=ctypes.uint32_t();native.pid(hwnd,pid.address());if(pid.value!==Services.appinfo.processID)throw Error('The active window is not owned by Soulu');native.release();native.send(hwnd,0xA1,2,0);return true;}

const libraries=new Map();
function library(name){if(!libraries.has(name))libraries.set(name,ctypes.open(name));return libraries.get(name);}
function handle(win){const raw=win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).nativeHandle;return ctypes.uintptr_t(ctypes.UInt64(String(raw)));}
let iconHandles;
export function brand(win){
 if(Services.appinfo.OS!=='WINNT')return;
 const result=win.__souluBrand={group:false,icons:false};
 try{Cc['@mozilla.org/windows-taskbar;1'].getService(Ci.nsIWinTaskbar).setGroupIdForWindow(win,'Soulu.Gecko.Preview');result.group=true;}catch(error){result.groupError=String(error);}
 try{
  const abi=(ctypes.winapi_abi||ctypes.default_abi),user=library('user32.dll'),hwnd=handle(win),path=Services.dirsvc.get('GreD',Ci.nsIFile);for(const part of ['soulu','chrome','ui','soulu-app-icon.ico'])path.append(part);
  const load=user.declare('LoadImageW',abi,ctypes.voidptr_t,ctypes.uintptr_t,(ctypes.char16_t||ctypes.jschar).ptr,ctypes.uint32_t,ctypes.int,ctypes.int,ctypes.uint32_t);
  const send=user.declare('SendMessageW',abi,ctypes.intptr_t,ctypes.uintptr_t,ctypes.uint32_t,ctypes.uintptr_t,ctypes.voidptr_t);
  iconHandles??=[load(0,path.path,1,16,16,0x10),load(0,path.path,1,32,32,0x10)];if(iconHandles.some(h=>h.isNull()))throw Error('Cannot load Soulu icons');for(let i=0;i<2;i++)send(hwnd,0x80,i,iconHandles[i]);result.icons=true;
 }catch(error){result.iconError=String(error);}
 try{library('shell32.dll').declare('SetCurrentProcessExplicitAppUserModelID',(ctypes.winapi_abi||ctypes.default_abi),ctypes.long,(ctypes.char16_t||ctypes.jschar).ptr)('Soulu.Gecko.Preview');}catch(error){result.processError=String(error);}
 return result;
}
export function material(win,enabled){
 // Page translucency is rendered by WebRender, not the Windows wallpaper material.
 Services.prefs.setBoolPref('widget.windows.mica',false);
 win.document.documentElement.removeAttribute('windowsmica');
 win.document.documentElement.removeAttribute('soulu-matte');
 return {enabled:!!enabled,native:true};
}

export function isDefault(){
 if(Services.appinfo.OS!=='WINNT')return false;
 return ['http','https'].every(scheme=>{let key;try{key=Cc['@mozilla.org/windows-registry-key;1'].createInstance(Ci.nsIWindowsRegKey);key.open(Ci.nsIWindowsRegKey.ROOT_KEY_CURRENT_USER,'Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\'+scheme+'\\UserChoice',Ci.nsIWindowsRegKey.ACCESS_READ);return key.readStringValue('ProgId')==='Soulu.Gecko.URL';}catch{return false;}finally{key?.close();}});
}

// Present the native window only once its real Soulu controls and state are ready.
// This does not create a splash window or expose a nonfunctional placeholder.
function cloak(win,enabled){
 const abi=ctypes.winapi_abi||ctypes.default_abi;
 const set=library('dwmapi.dll').declare('DwmSetWindowAttribute',abi,ctypes.int32_t,ctypes.uintptr_t,ctypes.uint32_t,ctypes.voidptr_t,ctypes.uint32_t);
 const value=ctypes.int(enabled?1:0);const result=set(handle(win),13,value.address(),ctypes.int.size);
 if(Number(result)!==0)throw Error('DWM cloak failed: '+result);
 const get=library('dwmapi.dll').declare('DwmGetWindowAttribute',abi,ctypes.int32_t,ctypes.uintptr_t,ctypes.uint32_t,ctypes.voidptr_t,ctypes.uint32_t),observed=ctypes.uint32_t();const status=get(handle(win),14,observed.address(),ctypes.uint32_t.size);return {setStatus:Number(result),getStatus:Number(status),observed:Number(observed.value)};
}
// Preview 9: last-resort native fallback. If the Soulu shell never composes,
// mark the window and show the stock toolbox so it stays usable and closable
// instead of a dead gradient-colored stub.
export function nativeFallback(win){
 if(win.__souluNativeFallback)return;
 win.__souluNativeFallback=true;
 win.__souluStartupPresentation.nativeFallbackAt=Date.now();
 try{win.document.documentElement.setAttribute('soulu-native-fallback','true');}catch(error){console.error(error);}
 try{
  if(win.__souluStartupCloaked){cloak(win,false);win.__souluStartupCloaked=false;}
  else win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=true;
  win.__souluStartupHidden=false;
 }catch(error){console.error(error);}
 try{win.focus();}catch(error){console.error(error);}
}
export function prepareStartup(win){
 if(win.__souluStartupHidden)return;
 win.__souluStartupPresentation={preparedAt:Date.now()};
 try{
  win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=false;
  if(Services.appinfo.OS==='WINNT'){win.__souluStartupPresentation.native=cloak(win,true);win.__souluStartupCloaked=true;}
  else win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=false;
  win.__souluStartupHidden=true;
  win.__souluStartupRevealTimer=win.setTimeout(()=>revealStartup(win),15000);
 }catch(error){win.__souluStartupPresentation.error=String(error);console.error('Soulu initial presentation',String(error));}
}
export function revealStartup(win){
 if(!win.__souluStartupHidden||win.__souluStartupRevealing)return;
 win.__souluStartupRevealing=true;
 win.clearTimeout(win.__souluStartupRevealTimer);
 // AppWindow must be allowed to create its backing surface only after Soulu
 // is ready. Its first Show() resets DWMWA_CLOAK, so reapply it synchronously.
 win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=true;
 if(win.__souluStartupCloaked)cloak(win,true);
 const present=()=>{
  if(!win.__souluStartupHidden)return;
  try{
   if(win.__souluStartupCloaked){cloak(win,false);win.__souluStartupCloaked=false;}
   else win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=true;
   win.__souluStartupHidden=false;win.__souluStartupPresentation.presentedAt=Date.now();win.focus();
  }catch(error){console.error(error);}
 };
 // Flush the real remote UI's layer transaction once. DOM readiness alone
 // does not mean that WebRender has received the file process's controls.
 (async()=>{
  const frame=win.document.getElementById('soulu-shell-frame');
  const remote=frame?.frameLoader?.remoteTab;
  if(!remote)throw Error('Soulu UI process is not available');
  remote.renderLayers=true;
  await frame.browsingContext.currentWindowGlobal.getActor('SouluApp').sendQuery('preparePresentation');
  if(!remote.hasLayers)await new Promise((resolve,reject)=>{
   const ready=()=>{if(!remote.hasLayers)return;win.removeEventListener('MozLayerTreeReady',ready);win.clearTimeout(timer);resolve();};
   win.addEventListener('MozLayerTreeReady',ready);
   const timer=win.setTimeout(()=>{win.removeEventListener('MozLayerTreeReady',ready);reject(Error('Soulu compositor did not receive UI layers'));},3000);
   ready();
  });
  win.windowUtils.updateLayerTree();
  await new Promise(resolve=>win.requestAnimationFrame(()=>win.requestAnimationFrame(resolve)));
  win.windowUtils.updateLayerTree();
  // Do not block the UI thread on DwmFlush: GPU/driver stalls can create a
  // Windows ghost window. Gecko layer acknowledgement is the presentation gate.
  win.__souluStartupPresentation.layersReadyAt=Date.now();present();
  // Preview 9 watchdog: if the shell never reports itself ready, fall back to
  // the native toolbox rather than leaving a dead cloaked window.
  win.clearTimeout(win.__souluFallbackTimer);
  win.__souluFallbackTimer=win.setTimeout(()=>{if(win.closed)return;if(!win.document.documentElement.hasAttribute('soulu-ui-ready'))nativeFallback(win);},8000);
 })().catch(error=>{win.__souluStartupPresentation.error=String(error);console.error(error);try{nativeFallback(win);}catch{nativeFallbackWin(win);}});
}
function nativeFallbackWin(win){try{win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=true;win.__souluStartupHidden=false;win.focus();}catch(error){console.error(error);}}
