"""Apply Preview 13 changes to the exact accepted Preview 12 payload."""
import pathlib,json,hashlib,io,zipfile,re,shutil,subprocess,struct,configparser
root=pathlib.Path(__file__).resolve().parents[1];out=root/'gecko-out';binary=root/'preview12-input/Soul-0.12.0-Preview-Setup-win64.exe'
meta=json.loads(pathlib.Path(str(binary)+'.build.json').read_text(encoding='utf-8-sig'))
assert meta['sourceCommit']=='10d65165e4b899c2b742cef78ee6508c4edd9b3b'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==meta['installerSHA256']
raw=binary.read_bytes();found=None
for match in re.finditer(b'PK\x05\x06',raw):
 pos=match.start()
 try:
  size,offset=struct.unpack_from('<II',raw,pos+12);comment=struct.unpack_from('<H',raw,pos+20)[0];start=pos-size-offset
  if start<0 or raw[start:start+4]!=b'PK\x03\x04':continue
  z=zipfile.ZipFile(io.BytesIO(raw[start:pos+22+comment]));names=z.namelist()
  if 'BUILD.json' not in names or 'engine/SoulEngine.exe' not in names:continue
  assert json.loads(z.read('BUILD.json'))['name']=='Soul 0.12.0 Preview';found=z;break
 except (ValueError,zipfile.BadZipFile,struct.error):continue
assert found,'Verified application payload not found'
out.mkdir(exist_ok=True)
for name in found.namelist():assert not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
found.extractall(out)
for old in out.glob('*.exe'):old.unlink()
(out/'soul-engine-manifest.json').unlink(missing_ok=True)
engine=out/'engine';(engine/'SoulEngine.exe').rename(engine/'SouluEngine.exe')
for p in (root/'gecko/chrome').rglob('*'):
 if p.is_file():
  destination=engine/'soulu/chrome'/p.relative_to(root/'gecko/chrome');destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,destination)
shutil.copyfile(root/'gecko/soulu.cfg',engine/'soulu.cfg')
ui=engine/'soulu/chrome/ui'
for source,dest in [('onboarding-ui.js','onboarding.js'),('import-ui.js','import-ui.js'),('settings-support.js','settings-support.js'),('updates-ui.js','updates-ui.js'),('extensions-ui.js','extension-toolbar.js'),('home-permission-ui.js','home-permission-ui.js')]:shutil.copyfile(root/'gecko/chrome'/source,ui/dest)
for name in ['settings-vpn.js','vpn-key.js']:shutil.copyfile(root/'ui'/name,ui/name)
p=ui/'settings.js';s=p.read_text(encoding='utf-8');s=s.replace("function openSection(id,target,fromCard=false){","function openSection(id,target,fromCard=false){$('dataMessage').textContent='';$('dataMessage').classList.remove('error');$('sectionError')?.remove();");p.write_text(s,encoding='utf-8')
# The welcome uses the same parser and complete VPN row schema as Settings.
p=ui/'onboarding.html';s=p.read_text(encoding='utf-8').replace('content="light"','content="light dark"');p.write_text(s,encoding='utf-8')
for p in (engine/'soulu/chrome').rglob('*'):
 if p.is_file() and p.suffix in ['.js','.mjs','.html','.css','.properties','.ftl'] and 'third_party' not in p.parts:
  s=p.read_text(encoding='utf-8');s=re.sub(r'\bSoul\b','Soulu',s).replace('SoulEngine','SouluEngine').replace('0.12.0','0.13.0');p.write_text(s,encoding='utf-8')
for name in ['branding/brand.properties','locales/ru/branding/brand.ftl','locales/en-US/branding/brand.ftl']:
 p=engine/'soulu/chrome'/name;p.write_text(p.read_text(encoding='utf-8').replace('Soulu','Soulu'),encoding='utf-8')
ini=configparser.ConfigParser();ini.optionxform=str;ini.read(engine/'application.ini');ini['App']['Name']='Soulu';ini['App']['Vendor']='Soulu';ini['App']['RemotingName']='Soulu'
for p in [engine/'application.ini',engine/'browser/application.ini']:
 with p.open('w') as f:ini.write(f,space_around_delimiters=False)
archive=engine/'browser/omni.ja';temp=archive.with_suffix('.new');removed=[]
with zipfile.ZipFile(archive) as original,zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as updated:
 for item in original.infolist():
  data=original.read(item.filename)
  if item.filename.endswith('default-bookmarks.html'):
   removed.append(item.filename);data=b'<!DOCTYPE NETSCAPE-Bookmark-file-1><META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8"><TITLE>Bookmarks</TITLE><H1>Bookmarks</H1><DL><p></DL><p>'
  updated.writestr(item.filename,data)
temp.replace(archive)
(out/'default-bookmarks-audit.json').write_text(json.dumps({'disabled':removed}))
with (engine/'defaults/pref/autoconfig.js').open('a') as f:f.write('\npref("browser.privateWindowSeparation.enabled",false);\npref("browser.bookmarks.restore_default_bookmarks",false);')
# Fully themed native form controls, plus a single-field VPN setup card.
with (ui/'gecko-frontend.css').open('a',encoding='utf-8') as f:f.write('''
body[data-theme=dark]{color-scheme:dark}body[data-theme=light]{color-scheme:light}
body[data-theme=dark] #controls :is(select,input:not([type=checkbox]),textarea){appearance:none;background:#303337;color:#f4f5f7;border-color:#555b65}
#controls select{appearance:none;min-width:160px;border:1px solid #cfd3da;border-radius:12px;padding:10px 14px;color:inherit;background:Canvas}
.welcome-themes{display:flex;gap:12px}.welcome-themes button{flex:1;min-width:0;border-radius:14px;background:#80808015;color:inherit}.welcome-themes button[aria-pressed=true]{background:#0879e6;color:#fff;border-color:#0879e6}
.card:has(.welcome-vpn) .content{padding:18px 30px}.card:has(.welcome-vpn) .hero{height:120px}.card:has(.welcome-vpn) .brand{top:28px}.card:has(.welcome-vpn) #art{transform:scale(.6)}
.welcome-vpn{display:grid;gap:8px;width:100%;padding:12px;border:1px solid #80808035;border-radius:20px;background:#80808008}
.welcome-vpn textarea{display:block;resize:vertical;width:100%;min-height:64px;box-sizing:border-box;padding:16px;border:1px solid #80808060;border-radius:14px;font:inherit;color:inherit;background:Canvas;line-height:1.5}
.welcome-vpn button{justify-self:end;background:#0879e6;color:#fff;border-color:transparent}.welcome-vpn p:empty{display:none}.welcome-vpn-success{margin:0;padding:8px 12px;background:#15936518;border:1px solid #15936560;border-radius:12px;color:light-dark(#126844,#9be6bf)}
.soulu-import-actions button.primary:only-of-type::after{content:none}.soulu-import-actions button[hidden]{display:none!important}
''')
build=json.loads((out/'BUILD.json').read_text());build.update(name='Soulu 0.13.0 Preview',base_preview=12,soulu_source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip());(out/'BUILD.json').write_text(json.dumps(build,indent=2))
