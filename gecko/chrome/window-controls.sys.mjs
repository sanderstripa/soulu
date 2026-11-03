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
 const abi=(ctypes.winapi_abi||ctypes.default_abi),user=library('user32.dll'),hwnd=handle(win),path=Services.dirsvc.get('GreD',Ci.nsIFile);for(const part of ['soulu','chrome','ui','soulu-app-icon.ico'])path.append(part);
 const load=user.declare('LoadImageW',abi,ctypes.uintptr_t,ctypes.uintptr_t,(ctypes.char16_t||ctypes.jschar).ptr,ctypes.uint32_t,ctypes.int,ctypes.int,ctypes.uint32_t);
 const send=user.declare('SendMessageW',abi,ctypes.intptr_t,ctypes.uintptr_t,ctypes.uint32_t,ctypes.uintptr_t,ctypes.intptr_t);
 iconHandles??=[load(0,path.path,1,16,16,0x10),load(0,path.path,1,32,32,0x10)];for(let i=0;i<2;i++)send(hwnd,0x80,i,ctypes.cast(iconHandles[i],ctypes.intptr_t));
 try{Cc['@mozilla.org/windows-taskbar;1'].getService(Ci.nsIWinTaskbar).setGroupIdForWindow(win,'Soulu.Gecko.Preview');}catch{}
 try{library('shell32.dll').declare('SetCurrentProcessExplicitAppUserModelID',abi,ctypes.long,(ctypes.char16_t||ctypes.jschar).ptr)('Soulu.Gecko.Preview');}catch{}
}
export function material(win,enabled){
 if(Services.appinfo.OS!=='WINNT')return {enabled,native:false};
 const dwm=library('dwmapi.dll'),set=dwm.declare('DwmSetWindowAttribute',(ctypes.winapi_abi||ctypes.default_abi),ctypes.long,ctypes.uintptr_t,ctypes.uint32_t,ctypes.voidptr_t,ctypes.uint32_t),hwnd=handle(win),value=ctypes.int(enabled?2:1),dark=ctypes.int(win.document.documentElement.hasAttribute('soulu-dark')?1:0);
 set(hwnd,20,dark.address(),ctypes.int.size);const result=set(hwnd,38,value.address(),ctypes.int.size);
 const code=Number(result.value??result);return {enabled,native:code===0,result:code};
}
