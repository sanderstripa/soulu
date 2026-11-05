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
 try{Cc['@mozilla.org/windows-taskbar;1'].getService(Ci.nsIWinTaskbar).setGroupIdForWindow(win,'Soulu.Preview');result.group=true;}catch(error){result.groupError=String(error);}
 try{
  const abi=(ctypes.winapi_abi||ctypes.default_abi),user=library('user32.dll'),hwnd=handle(win),path=Services.dirsvc.get('GreD',Ci.nsIFile);for(const part of ['soulu','chrome','ui','soulu-app-icon.ico'])path.append(part);
  const load=user.declare('LoadImageW',abi,ctypes.voidptr_t,ctypes.uintptr_t,(ctypes.char16_t||ctypes.jschar).ptr,ctypes.uint32_t,ctypes.int,ctypes.int,ctypes.uint32_t);
  const send=user.declare('SendMessageW',abi,ctypes.intptr_t,ctypes.uintptr_t,ctypes.uint32_t,ctypes.uintptr_t,ctypes.voidptr_t);
  iconHandles??=[load(0,path.path,1,16,16,0x10),load(0,path.path,1,32,32,0x10)];if(iconHandles.some(h=>h.isNull()))throw Error('Cannot load Soulu icons');for(let i=0;i<2;i++)send(hwnd,0x80,i,iconHandles[i]);result.icons=true;
 }catch(error){result.iconError=String(error);}
 try{library('shell32.dll').declare('SetCurrentProcessExplicitAppUserModelID',(ctypes.winapi_abi||ctypes.default_abi),ctypes.long,(ctypes.char16_t||ctypes.jschar).ptr)('Soulu.Preview');}catch(error){result.processError=String(error);}
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
 return ['http','https'].every(scheme=>{let key;try{key=Cc['@mozilla.org/windows-registry-key;1'].createInstance(Ci.nsIWindowsRegKey);key.open(Ci.nsIWindowsRegKey.ROOT_KEY_CURRENT_USER,'Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\'+scheme+'\\UserChoice',Ci.nsIWindowsRegKey.ACCESS_READ);return key.readStringValue('ProgId')==='Soulu.URL';}catch{return false;}finally{key?.close();}});
}

// Keep only the initial taskbar suppression; native window visibility owns presentation.
// A hidden/cloaked composing window must not get a transient taskbar button.
function taskbarPending(win,pending){
 if(Services.appinfo.OS!=='WINNT')return;
 const abi=ctypes.winapi_abi||ctypes.default_abi,user=library('user32.dll');
 const get=user.declare('GetWindowLongW',abi,ctypes.long,ctypes.uintptr_t,ctypes.int);
 const set=user.declare('SetWindowLongW',abi,ctypes.long,ctypes.uintptr_t,ctypes.int,ctypes.long);
 const hwnd=handle(win),style=Number(get(hwnd,-20));
 if(pending){win.__souluOriginalExStyle??=style;set(hwnd,-20,(style|0x80)&~0x40000);}
 else if(win.__souluOriginalExStyle!==undefined)set(hwnd,-20,win.__souluOriginalExStyle);
}
export function prepareStartup(win){
 if(win.__souluStartupHidden)return;
 win.__souluStartupPresentation={preparedAt:Date.now(),mode:'native'};
 try{
  taskbarPending(win,true);
  win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=false;
  win.__souluStartupHidden=true;
  // Use the early native Show path. Never wait for a GPU layer/actor acknowledgement.
  win.__souluStartupRevealTimer=win.setTimeout(()=>{
   if(win.Soulu?.ready)revealStartup(win);
   else console.error('Soulu initialization did not finish');
  },8000);
 }catch(error){win.__souluStartupPresentation.error=String(error);console.error(error);}
}
export function revealStartup(win){
 if(!win.__souluStartupHidden||win.closed)return;
 win.clearTimeout(win.__souluStartupRevealTimer);
 ChromeUtils.importESModule('chrome://soulu/content/lifecycle.sys.mjs').consolidateAutomaticStart(win);
 if(win.closed)return;
 try{
  win.document.title='Soulu';
  win.docShell.treeOwner.QueryInterface(Ci.nsIInterfaceRequestor).getInterface(Ci.nsIBaseWindow).visibility=true;
  taskbarPending(win,false);
  win.__souluStartupHidden=false;
  win.__souluStartupPresentation.presentedAt=Date.now();
  win.focus();
  // Background native filter compilation stays after the first visible paint.
  // These frames never gate native window visibility.
  win.requestAnimationFrame(()=>win.requestAnimationFrame(()=>{if(!win.closed)win.dispatchEvent(new win.Event('SouluPresented'));}));
 }catch(error){win.__souluStartupPresentation.error=String(error);console.error(error);}
}
