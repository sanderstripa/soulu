"""Exercise the real Rust async atomic installer, including rejected corrupt input."""
import ctypes,json,pathlib,shutil,sys,tempfile,time
root=pathlib.Path(__file__).resolve().parents[2]
lib=ctypes.CDLL(str(pathlib.Path(sys.argv[1]).resolve()))
lib.soulu_ab_init.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_bool];lib.soulu_ab_init.restype=ctypes.c_bool
lib.soulu_ab_install_files.argtypes=[ctypes.c_char_p,ctypes.c_char_p];lib.soulu_ab_install_files.restype=ctypes.c_bool
lib.soulu_ab_updating.restype=ctypes.c_bool;lib.soulu_ab_status.restype=ctypes.c_void_p;lib.soulu_ab_free.argtypes=[ctypes.c_void_p]
def status():
 p=lib.soulu_ab_status()
 try:return json.loads(ctypes.string_at(p))
 finally:lib.soulu_ab_free(p)
def finish():
 deadline=time.time()+60
 while lib.soulu_ab_updating():
  if time.time()>deadline:raise AssertionError('Rust worker timed out')
  time.sleep(.05)
with tempfile.TemporaryDirectory(prefix='Soulu Rust filters ') as tmp:
 d=pathlib.Path(tmp);cache=d/'cache.json';assert lib.soulu_ab_init(str(cache).encode(),b'',False)
 good=d/'good';good.mkdir()
 for i,name in enumerate(['easylist.txt','easyprivacy.txt','ruadlist.txt']):shutil.copyfile(root/'cef/soulu/adblock/filters'/name,good/(str(i)+'.txt'))
 assert lib.soulu_ab_install_files(str(good).encode(),str(cache).encode());finish();first=status();assert first['lastSuccessfulUpdate']>0 and first['lastUpdateError']=='',first
 preserved=cache.read_bytes();bad=d/'bad';bad.mkdir()
 for i in range(3):(bad/(str(i)+'.txt')).write_text('<html>upstream error</html>')
 assert lib.soulu_ab_install_files(str(bad).encode(),str(cache).encode());finish();after=status()
 assert after['lastUpdateError'] and after['networkRules']==first['networkRules'] and after['cosmeticRules']==first['cosmeticRules'] and cache.read_bytes()==preserved,after
 report={'passed':True,'valid_atomic_install':True,'corrupt_update_preserves_cache_and_engine':True,'networkRules':after['networkRules'],'cosmeticRules':after['cosmeticRules']}
 pathlib.Path(sys.argv[2]).write_text(json.dumps(report,indent=2),encoding='utf-8');print(report)
