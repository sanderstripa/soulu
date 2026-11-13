"""Replace the complete engine with the pinned official 160.0 distribution."""
from pathlib import Path
import configparser,hashlib,shutil,subprocess,urllib.request
root=Path(__file__).resolve().parents[1]
engine=root/'gecko-out/engine'; cache=root/'gecko-cache';cache.mkdir(exist_ok=True)
archive=cache/'runtime-160.0.exe'
if not archive.exists():
    with urllib.request.urlopen('https://archive.mozilla.org/pub/firefox/releases/160.0/win64/ru/Firefox%20Setup%20160.0.exe',timeout=180) as source,archive.open('wb') as target:shutil.copyfileobj(source,target)
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='9aca6af4a633546ce9908894d735b0518c36b6a54f108566e517225983cf5173'
extracted=cache/'runtime160';shutil.rmtree(extracted,ignore_errors=True)
subprocess.run(['7z','x',str(archive),'-o'+str(extracted),'-y'],check=True,stdout=subprocess.DEVNULL)
fresh=extracted/'core'
for name in ['sona','sona.cfg','defaults/pref/autoconfig.js','distribution','chrome']:
    src=engine/name;dst=fresh/name
    if src.is_dir():shutil.copytree(src,dst,dirs_exist_ok=True)
    else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
(fresh/'firefox.exe').rename(fresh/'SonaEngine.exe')
ini=configparser.ConfigParser();ini.optionxform=str;ini.read(fresh/'application.ini')
assert ini['App']['Version']=='160.0'
for k in ['Name','Vendor','RemotingName']:ini['App'][k]='Sona'
for target in [fresh/'application.ini',fresh/'browser/application.ini']:
    with target.open('w') as f:ini.write(f,space_around_delimiters=False)
shutil.rmtree(engine);shutil.move(str(fresh),engine)
# Normalize Mozilla's optimized JAR index while retaining all file offsets.
import struct,zipfile,io
for archive in [engine/'omni.ja',engine/'browser/omni.ja']:
    raw=archive.read_bytes();begin=raw.find(b'PK\x01\x02');assert begin>=0
    end=begin;count=0
    while raw[end:end+4]==b'PK\x01\x02':
        name,extra,comment=struct.unpack_from('<HHH',raw,end+28)
        end+=46+name+extra+comment;count+=1
    central=raw[begin:end]
    normalized=raw+central+struct.pack('<4s4H2IH',b'PK\x05\x06',0,0,count,count,len(central),len(raw),0)
    temporary=archive.with_suffix('.normal')
    with zipfile.ZipFile(io.BytesIO(normalized)) as source,zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():target.writestr(name,source.read(name))
    temporary.replace(archive)

# Override cached engine directory keys before application services start.
bootstrap=engine/'sona.cfg'
source=bootstrap.read_text(encoding='utf-8')
injection="""
  const local=Cc['@mozilla.org/file/local;1'].createInstance(Ci.nsIFile);
  local.initWithPath(Services.env.get('LOCALAPPDATA'));local.append('Sona');
  for(const [key,leaf] of [['UAppData','ApplicationData'],['ULocalAppData','ApplicationData'],['UpdRootD','Updates'],['OldUpdRootD','Updates']]){
    const directory=local.clone();directory.append(leaf);
    if(!directory.exists())directory.create(Ci.nsIFile.DIRECTORY_TYPE,0o700);
    try{Services.dirsvc.undefine(key);}catch{}
    Services.dirsvc.set(key,directory);
  }
"""
source=source.replace('  const app = Services.dirsvc.get',injection+'\n  const app = Services.dirsvc.get')
bootstrap.write_text(source,encoding='utf-8')
