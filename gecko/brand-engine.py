import ctypes as c,pathlib
from ctypes import wintypes as w
root=pathlib.Path(__file__).resolve().parents[1]/'gecko-out';k=c.WinDLL('kernel32',use_last_error=True)
k.LoadLibraryExW.argtypes=[w.LPCWSTR,w.HANDLE,w.DWORD];k.LoadLibraryExW.restype=w.HMODULE
k.FindResourceW.argtypes=[w.HMODULE,c.c_void_p,c.c_void_p];k.FindResourceW.restype=w.HANDLE
k.SizeofResource.argtypes=[w.HMODULE,w.HANDLE];k.SizeofResource.restype=w.DWORD
k.LoadResource.argtypes=[w.HMODULE,w.HANDLE];k.LoadResource.restype=w.HANDLE
k.LockResource.argtypes=[w.HANDLE];k.LockResource.restype=c.c_void_p
k.BeginUpdateResourceW.argtypes=[w.LPCWSTR,w.BOOL];k.BeginUpdateResourceW.restype=w.HANDLE
k.UpdateResourceW.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,w.WORD,c.c_void_p,w.DWORD];k.UpdateResourceW.restype=w.BOOL
k.EndUpdateResourceW.argtypes=[w.HANDLE,w.BOOL];k.EndUpdateResourceW.restype=w.BOOL
h=k.LoadLibraryExW(str(root/'Soul.exe'),None,2);assert h
callback=c.WINFUNCTYPE(w.BOOL,w.HMODULE,c.c_void_p,c.c_void_p,c.c_ssize_t)
k.EnumResourceNamesW.argtypes=[w.HMODULE,c.c_void_p,callback,c.c_ssize_t];k.EnumResourceNamesW.restype=w.BOOL
resources=[]
for kind in [16,3,14]:
 @callback
 def collect(module,type_id,name,param):
  identifier=int(name) if int(name)<=65535 else c.wstring_at(name)
  resource=k.FindResourceW(module,name,type_id);size=k.SizeofResource(module,resource)
  resources.append((kind,identifier,c.string_at(k.LockResource(k.LoadResource(module,resource)),size)))
  return True
 assert k.EnumResourceNamesW(h,c.c_void_p(kind),collect,0)
for target in (root/'engine').glob('*.exe'):
 update=k.BeginUpdateResourceW(str(target),False);assert update
 for kind,identifier,data in resources:
  name=c.c_void_p(identifier) if isinstance(identifier,int) else c.cast(c.c_wchar_p(identifier),c.c_void_p)
  buf=c.create_string_buffer(data)
  assert k.UpdateResourceW(update,c.c_void_p(kind),name,0x409,buf,len(data))
 assert k.EndUpdateResourceW(update,False)
