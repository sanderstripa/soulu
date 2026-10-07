"""Read the real Windows MSAA menu model through its native accessibility provider."""
import ctypes
class GUID(ctypes.Structure):
    _fields_=[('a',ctypes.c_ulong),('b',ctypes.c_ushort),('c',ctypes.c_ushort),('d',ctypes.c_ubyte*8)]
from comtypes.automation import VARIANT as Variant
def rows(hwnd):
    ole=ctypes.windll.ole32;ole.CoInitialize(None)
    iid=GUID();ole.CLSIDFromString('{618736E0-3C3D-11CF-810C-00AA00389B71}',ctypes.byref(iid))
    accessible=ctypes.c_void_p()
    acc=ctypes.windll.oleacc
    acc.AccessibleObjectFromWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p)]
    result=acc.AccessibleObjectFromWindow(hwnd,0xFFFFFFFC,ctypes.byref(iid),ctypes.byref(accessible))
    assert result==0 and accessible.value,f'Menu accessibility provider unavailable: {result:#x}'
    vtable=ctypes.cast(accessible,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    def method(index,*args):return ctypes.WINFUNCTYPE(ctypes.c_long,ctypes.c_void_p,*args)(vtable[index])
    count=ctypes.c_long();assert method(8,ctypes.POINTER(ctypes.c_long))(accessible,ctypes.byref(count))==0
    output=[]
    for index in range(count.value):
        child=Variant(index+1)
        name=ctypes.c_void_p();assert method(10,Variant,ctypes.POINTER(ctypes.c_void_p))(accessible,child,ctypes.byref(name))==0
        label=ctypes.wstring_at(name) if name.value else ''
        ctypes.windll.oleaut32.SysFreeString.argtypes=[ctypes.c_void_p];ctypes.windll.oleaut32.SysFreeString(name)
        role=Variant();state=Variant()
        role_result=method(13,Variant,ctypes.POINTER(Variant))(accessible,child,ctypes.byref(role))
        method(14,Variant,ctypes.POINTER(Variant))(accessible,child,ctypes.byref(state))
        bounds=[ctypes.c_long() for _ in range(4)]
        assert method(22,*([ctypes.POINTER(ctypes.c_long)]*4),Variant)(accessible,*(ctypes.byref(v) for v in bounds),child)==0
        output.append({'label':label,'role':role.value,'state':state.value,'role_result':role_result,'role_type':role.vt,'rect':[v.value for v in bounds]})
    ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vtable[2])(accessible)
    ole.CoUninitialize();return output
