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
resource=k.FindResourceW(h,c.c_void_p(1),c.c_void_p(16));assert resource
size=k.SizeofResource(h,resource);data=c.string_at(k.LockResource(k.LoadResource(h,resource)),size);buf=c.create_string_buffer(data)
update=k.BeginUpdateResourceW(str(root/'engine/SoulEngine.exe'),False);assert update
assert k.UpdateResourceW(update,c.c_void_p(16),c.c_void_p(1),0x409,buf,len(data));assert k.EndUpdateResourceW(update,False)
