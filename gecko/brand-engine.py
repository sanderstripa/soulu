"""Replace every version/icon language and original icon group with Sona branding."""
import ctypes as c,pathlib,json,hashlib
from ctypes import wintypes as w
root=pathlib.Path(__file__).resolve().parents[1]/'gecko-out';k=c.WinDLL('kernel32',use_last_error=True)
for name,args,result in [('LoadLibraryExW',[w.LPCWSTR,w.HANDLE,w.DWORD],w.HMODULE),('FreeLibrary',[w.HMODULE],w.BOOL),('FindResourceExW',[w.HMODULE,c.c_void_p,c.c_void_p,w.WORD],w.HANDLE),('SizeofResource',[w.HMODULE,w.HANDLE],w.DWORD),('LoadResource',[w.HMODULE,w.HANDLE],w.HANDLE),('LockResource',[w.HANDLE],c.c_void_p),('BeginUpdateResourceW',[w.LPCWSTR,w.BOOL],w.HANDLE),('UpdateResourceW',[w.HANDLE,c.c_void_p,c.c_void_p,w.WORD,c.c_void_p,w.DWORD],w.BOOL),('EndUpdateResourceW',[w.HANDLE,w.BOOL],w.BOOL)]:
 fn=getattr(k,name);fn.argtypes=args;fn.restype=result
N=c.WINFUNCTYPE(w.BOOL,w.HMODULE,c.c_void_p,c.c_void_p,c.c_ssize_t);L=c.WINFUNCTYPE(w.BOOL,w.HMODULE,c.c_void_p,c.c_void_p,w.WORD,c.c_ssize_t)
k.EnumResourceNamesW.argtypes=[w.HMODULE,c.c_void_p,N,c.c_ssize_t];k.EnumResourceLanguagesW.argtypes=[w.HMODULE,c.c_void_p,c.c_void_p,L,c.c_ssize_t]
def pointer(value):return c.c_void_p(value) if isinstance(value,int) else c.cast(c.c_wchar_p(value),c.c_void_p)
def scan(path):
 h=k.LoadLibraryExW(str(path),None,2);assert h;result=[]
 for kind in [16,3,14]:
  @N
  def names(module,typ,name,_):
   identifier=int(name) if int(name)<=65535 else c.wstring_at(name)
   @L
   def languages(module,typ,name,lang,_):
    resource=k.FindResourceExW(module,typ,name,lang);size=k.SizeofResource(module,resource);result.append((kind,identifier,lang,c.string_at(k.LockResource(k.LoadResource(module,resource)),size)));return True
   k.EnumResourceLanguagesW(module,typ,name,languages,0);return True
  k.EnumResourceNamesW(h,c.c_void_p(kind),names,0)
 k.FreeLibrary(h);return result
source=scan(root/'Sona.exe');group=next(data for kind,_,_,data in source if kind==14)
audit=[]
for target in (root/'engine').glob('*.exe'):
 old=scan(target);groups={ident for kind,ident,_,_ in old if kind==14};update=k.BeginUpdateResourceW(str(target),False);assert update
 for kind,ident,lang,_ in old:assert k.UpdateResourceW(update,pointer(kind),pointer(ident),lang,None,0)
 resources={(kind,ident):data for kind,ident,_,data in source}
 for ident in groups:resources[(14,ident)]=group
 for (kind,ident),data in resources.items():
  buf=c.create_string_buffer(data)
  for lang in [0,0x409]:assert k.UpdateResourceW(update,pointer(kind),pointer(ident),lang,buf,len(data))
 assert k.EndUpdateResourceW(update,False)

 after=scan(target);groups=[data for kind,_,_,data in after if kind==14];assert groups and all(data==group for data in groups)
 audit.append({'file':target.name,'groups':len(groups),'iconGroupsMatchSona':True,'iconSHA256':hashlib.sha256(group).hexdigest()})
(root/'windows-brand-audit.json').write_text(json.dumps(audit,indent=2))
