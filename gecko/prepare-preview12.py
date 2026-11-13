"""Overlay only Preview 12 fixes onto the verified Preview 8 artifact."""
import hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).resolve().parents[1];out=root/'gecko-out';runtime=out/'runtime'
assert (out/'BUILD.json').is_file(), 'Preview 8 build artifact missing'
build=json.loads((out/'BUILD.json').read_text());assert build['name']=='Sona Gecko Preview 8',build
# The base archive's old launcher must not be shipped beside Soul.exe.
for obsolete in out.glob('*.exe'):obsolete.unlink()
for name in ['sona-gecko-manifest.json','gecko-manifest.json']:(out/name).unlink(missing_ok=True)
# Never run the Mozilla installer. Reuse the exact already-extracted Preview 8
# runtime and auxiliary components; only Sona resources/launcher are updated.
for p in (root/'gecko/chrome').rglob('*'):
 if p.is_file():
  target=runtime/'sona/chrome'/p.relative_to(root/'gecko/chrome');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
shutil.copyfile(root/'gecko/sona.cfg',runtime/'sona.cfg')
for source,target in [('integration-ui.js','integration-ui.js'),('onboarding-ui.js','onboarding.js'),('settings-support.js','settings-support.js'),('updates-ui.js','updates-ui.js'),('vot-ui.js','vot-ui.js')]:shutil.copyfile(root/'gecko/chrome'/source,runtime/'sona/chrome/ui'/target)
for page in ['onboarding.html','settings.html']:
 p=runtime/'sona/chrome/ui'/page;text=p.read_text(encoding='utf-8');text=text.replace('</body>','<script src="import-ui.js"></script></body>');p.write_text(text,encoding='utf-8')
shutil.copyfile(root/'gecko/chrome/import-ui.js',runtime/'sona/chrome/ui/import-ui.js')
with (runtime/'sona/chrome/ui/gecko-frontend.css').open('a',encoding='utf-8') as f:f.write('\n.sona-import{width:min(620px,calc(100vw - 48px));box-sizing:border-box;border:1px solid #80808040;border-radius:20px;padding:28px;background:light-dark(#f6f6f8,#15171b);color:light-dark(#191a1e,#eeeeef);font:14px Onest,Segoe UI,sans-serif;color-scheme:light dark}.sona-import::backdrop{background:#0006;backdrop-filter:blur(8px)}.sona-import select{width:100%;padding:10px;border-radius:10px}.sona-import fieldset{border:0;display:flex;flex-wrap:wrap;gap:16px;margin:20px 0;padding:0}.sona-import label{display:flex;align-items:center;gap:6px}.sona-import-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}.sona-import button{padding:10px 14px;border-radius:10px;border:1px solid #80808040;font:inherit}.sona-import .primary{background:#0879e6;color:white}.sona-import p{line-height:1.5}')
# Suppress automatic Firefox OS integration and remove registration/install tools,
# including uninstall/helper.exe, not just files in the runtime root.
for p in list(runtime.rglob('*')):
 if p.is_file() and (p.name.lower() in {'default-browser-agent.exe','maintenanceservice.exe','maintenanceservice_installer.exe','updater.exe','helper.exe','private_browsing.exe'}):p.unlink()
shutil.rmtree(runtime/'uninstall',ignore_errors=True)
with (runtime/'defaults/pref/autoconfig.js').open('a',encoding='utf-8') as f:
 for key,value in {'default-browser-agent.enabled':False,'browser.shell.checkDefaultBrowser':False,'browser.startup.preXulSkeletonUI':False,'browser.startup.blankWindow':False}.items():f.write('\npref('+json.dumps(key)+','+json.dumps(value)+');')
# Product UI uses only Sona naming; engine attribution stays in license files.
for name in ['settings.js','settings-data.js','settings-support.js']:
 p=runtime/'sona/chrome/ui'/name
 text=p.read_text(encoding='utf-8').replace("['Firefox',state.update?.firefox]", "['Движок',state.update?.gecko]").replace("['Gecko',state.update?.gecko],",'').replace('Firefox','Soul')
 p.write_text(text,encoding='utf-8')
# The updater and Settings must agree with the installer and Windows resources.
build.update(name='Sona Gecko Preview 12',base_preview=8,sona_source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
(out/'BUILD.json').write_text(json.dumps(build,indent=2))

navigation=runtime/'sona/chrome/ui/navigation.js';text=navigation.read_text(encoding='utf-8')
old="add('Удалить','Delete',()=>{const ids=descendants(row.id);if(row.type==='folder'&&ids.size>1&&!confirm(en?'Delete folder and its bookmarks?':'Удалить папку со всеми закладками?'))return;return persist(rows.filter(r=>!ids.has(r.id)));});"
new="add('Удалить','Delete',async()=>{const ids=descendants(row.id);if(row.type==='folder'&&ids.size>1&&!await window.sonaConfirmBookmarkDelete(row.title))return;return persist(rows.filter(r=>!ids.has(r.id)));});"
assert text.count(old)==1,'Bookmark confirmation patch mismatch'
navigation.write_text(text.replace(old,new),encoding='utf-8')
with (runtime/'sona/chrome/ui/gecko-frontend.css').open('a',encoding='utf-8') as f:f.write('\n.sona-bookmark-confirm{border:1px solid #80808040;border-radius:18px;background:#f6f6f8;color:#191a1e;padding:24px;width:min(440px,calc(100vw - 48px));font:14px Onest,Segoe UI,sans-serif}.sona-bookmark-confirm::backdrop{background:#0006;backdrop-filter:blur(6px)}.sona-bookmark-confirm div{display:flex;gap:10px;justify-content:flex-end}.sona-bookmark-confirm button{font:inherit;padding:10px 18px;border:1px solid #80808040;border-radius:10px}.sona-bookmark-confirm .primary{background:#0879e6;color:white}body[data-theme=dark] .sona-bookmark-confirm{background:#15171b;color:#eeeeef}')

import configparser,zipfile
runtime.rename(out/'engine');runtime=out/'engine'
(runtime/'firefox.exe').rename(runtime/'SoulEngine.exe')
ini=configparser.ConfigParser();ini.optionxform=str;ini.read(runtime/'application.ini');ini['App']['Name']='Soul';ini['App']['Vendor']='Soul';ini['App']['RemotingName']='Soul'
with (runtime/'application.ini').open('w') as f:ini.write(f,space_around_delimiters=False)
# XRE uses the ini's parent as application directory; browser/ contains its omni.ja.
shutil.copyfile(runtime/'application.ini',runtime/'browser/application.ini')
# Hide stock browser chrome in the document itself, before any startup script.
archive=runtime/'browser/omni.ja';temporary=archive.with_suffix('.tmp')
# Mozilla optimized JARs place the central directory before file data.
# Append a conventional directory/EOCD without moving any local file offsets.
import struct,io
raw=archive.read_bytes();begin=raw.find(b'PK\x01\x02');assert begin>=0
end=begin;count=0
while raw[end:end+4]==b'PK\x01\x02':
 name,extra,comment=struct.unpack_from('<HHH',raw,end+28);end+=46+name+extra+comment;count+=1
central=raw[begin:end];normalized=raw+central+struct.pack('<4s4H2IH',b'PK\x05\x06',0,0,count,count,len(central),len(raw),0)
with zipfile.ZipFile(io.BytesIO(normalized)) as src,zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as dst:
 for info in src.infolist():
  data=src.read(info.filename)
  if info.filename.endswith('browser.xhtml'):
   text=data.decode();import re;match=re.search(r'</(?:html:)?head>',text);assert match;at=match.start();data=(text[:at]+'<html:style>#navigator-toolbox,#titlebar,#sidebar-main{display:none!important}</html:style>'+text[at:]).encode()
  dst.writestr(info.filename,data)
temporary.replace(archive)
for p in (runtime/'sona/chrome').rglob('*'):
 if p.is_file() and p.suffix in ['.js','.mjs','.html','.css','.ftl','.properties'] and 'third_party' not in p.parts:
  text=p.read_text(encoding='utf-8');text=text.replace('Sona Gecko','Soul').replace('SonaGecko','Soul').replace('Sona.Gecko','Soul').replace('Добро пожаловать в Sona','Добро пожаловать в Soul').replace('Welcome to Sona','Welcome to Soul').replace('Мастер Gecko','Мастер Soul').replace('в Sona','в Soul').replace('Sona браузером','Soul браузером').replace('Sona the default','Soul the default').replace('Открыть Sona','Открыть Soul');p.write_text(text,encoding='utf-8')
shutil.copyfile(root/'gecko/chrome/home-permission-ui.js',runtime/'sona/chrome/ui/home-permission-ui.js')
p=runtime/'sona/chrome/ui/home.html';p.write_text(p.read_text(encoding='utf-8').replace('</body>','<script src="home-permission-ui.js"></script></body>'),encoding='utf-8')
build.update(name='Soul 0.12.0 Preview');(out/'BUILD.json').write_text(json.dumps(build,indent=2))

for name in ['branding/brand.properties','locales/ru/branding/brand.ftl','locales/en-US/branding/brand.ftl']:
 p=runtime/'sona/chrome'/name;p.write_text(p.read_text(encoding='utf-8').replace('Sona','Soul'),encoding='utf-8')

# Unpackaged desktop applications use the browser's network geolocation provider.
with (runtime/'defaults/pref/autoconfig.js').open('a',encoding='utf-8') as f:f.write('\npref("geo.provider.ms-windows-location",false);')

# Product document titles and labels use the installed product name.
for p in (runtime/'sona/chrome/ui').glob('*.html'):
 p.write_text(p.read_text(encoding='utf-8').replace('Sona Gecko','Soul').replace('Sona','Soul'),encoding='utf-8')
