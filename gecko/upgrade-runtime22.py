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
for name in ['soulu','soulu.cfg','defaults/pref/autoconfig.js','distribution','chrome']:
    src=engine/name;dst=fresh/name
    if src.is_dir():shutil.copytree(src,dst,dirs_exist_ok=True)
    else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
(fresh/'firefox.exe').rename(fresh/'SouluEngine.exe')
ini=configparser.ConfigParser();ini.optionxform=str;ini.read(fresh/'application.ini')
assert ini['App']['Version']=='160.0'
for k in ['Name','Vendor','RemotingName']:ini['App'][k]='Soulu'
for target in [fresh/'application.ini',fresh/'browser/application.ini']:
    with target.open('w') as f:ini.write(f,space_around_delimiters=False)
shutil.rmtree(engine);shutil.move(str(fresh),engine)
