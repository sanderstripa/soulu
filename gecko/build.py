#!/usr/bin/env python3
"""Assemble an unmodified, integrity-checked Mozilla runtime plus Soulu chrome."""
import argparse, hashlib, json, pathlib, shutil, subprocess, urllib.request, tarfile, zipfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--platform',choices=['win64','linux-x86_64'],default='win64');p.add_argument('--output',default='gecko-out');args=p.parse_args()
out=ROOT/args.output;cache=ROOT/'gecko-cache';cache.mkdir(exist_ok=True)
def fetch(url,path):
 if not path.exists():
  print('Download',url,flush=True)
  with urllib.request.urlopen(url,timeout=180) as response,path.open('wb') as f:shutil.copyfileobj(response,f)
 return path
pin=json.loads((ROOT/'gecko/runtime-pin.json').read_text(encoding='utf-8'))
version=pin['version'];platform=args.platform
base=f'https://archive.mozilla.org/pub/firefox/releases/{version}'
checks=fetch(base+'/SHA256SUMS',cache/f'{version}-SHA256SUMS')
rel=pin['archives'][platform]['path']
archive=fetch(base+'/'+urllib.request.quote(rel),cache/(platform+'-'+rel.split('/')[1]+'-'+pathlib.Path(rel).name))
expected=pin['archives'][platform]['sha256']
assert next(line.split()[0] for line in checks.read_text(encoding='utf-8').splitlines() if line.split(maxsplit=1)[1].lstrip('*')==rel)==expected
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
if digest!=expected:raise RuntimeError('Mozilla runtime checksum mismatch')
if out.exists():shutil.rmtree(out)
out.mkdir(parents=True);runtime=out/'runtime'
if platform=='win64':
 extracted=cache/'expanded';shutil.rmtree(extracted,ignore_errors=True)
 subprocess.run(['7z','x',str(archive),'-o'+str(extracted),'-y'],check=True,stdout=subprocess.DEVNULL)
 shutil.copytree(extracted/'core',runtime)
else:
 with tarfile.open(archive) as t:t.extractall(out,filter='data')
 (out/'firefox').rename(runtime)
shutil.copytree(ROOT/'gecko/chrome',runtime/'soulu/chrome')
shutil.copytree(ROOT/'ui',runtime/'soulu/chrome/ui')
if platform=='win64':
 for icons in [runtime/'chrome/icons/default',runtime/'browser/chrome/icons/default']:
  icons.mkdir(parents=True,exist_ok=True);shutil.copy(ROOT/'ui/soulu-app-icon.ico',icons/'main-window.ico')
shutil.copy(ROOT/'gecko/chrome.manifest',runtime/'soulu/chrome.manifest')
shutil.copy(ROOT/'gecko/soulu.cfg',runtime/'soulu.cfg')
(runtime/'defaults/pref').mkdir(parents=True,exist_ok=True)
shutil.copy(ROOT/'gecko/defaults/pref/autoconfig.js',runtime/'defaults/pref/autoconfig.js')
shutil.copy(ROOT/'gecko/chrome/bridge.js',runtime/'soulu/chrome/ui/gecko-bridge.js')
# Install the bridge before the unchanged frontend scripts run.
for page in ['index.html','settings.html','home.html','history.html']:
 path=runtime/'soulu/chrome/ui'/page
 content=path.read_text(encoding='utf-8')
 if page=='index.html':
  import re
  content=re.sub(r'<script src="(?:third_party/bergamot-runtime.js|third_party/tinyld.js|translation-models.js|translation-service.js|translation-ui.js)"></script>','',content)
 content=content.replace('<head>','<head><script src="gecko-bridge.js"></script>',1)
 path.write_text(content,encoding='utf-8')
js=runtime/'soulu/chrome/ui/settings.js';text=js.read_text(encoding='utf-8')
text=text.replace("opt('adaptive','Основная','Main'),opt('compact','Компактная','Compact')","opt('adaptive','Основная','Main')")
text=text.replace("['CEF',state.update?.cef],['Chromium',state.update?.chromium]","['Gecko',state.update?.gecko],['Firefox',state.update?.firefox]")
js.write_text(text,encoding='utf-8')
renderer=runtime/'soulu/chrome/ui/renderer.js';text=renderer.read_text(encoding='utf-8').replace('function renderTabs(){renderClassicTabs();renderCompactTabs();}','function renderTabs(){renderClassicTabs();}');renderer.write_text(text,encoding='utf-8')
data=runtime/'soulu/chrome/ui/settings-data.js';text=data.read_text(encoding='utf-8')
text=text.replace('Пароли активного профиля защищены учётной записью Windows.','Пароли активного профиля защищены хранилищем NSS Firefox.').replace('Passwords for the active profile are protected by your Windows account.','Passwords for the active profile are protected by the Firefox NSS store.')
text=text.replace('Пароль скопирован. Пока Soulu запущен, буфер очистится через 30 секунд, если его содержимое не изменится.','Пароль скопирован.').replace('Password copied. While Soulu runs, the clipboard clears after 30 seconds if its content stays unchanged.','Password copied.')
data.write_text(text,encoding='utf-8')
# Optional engine-specific features keep their sections and report availability explicitly.
shutil.copy(ROOT/'gecko/chrome/settings-support.js',runtime/'soulu/chrome/ui/settings-support.js')
path=runtime/'soulu/chrome/ui/settings.html';text=path.read_text(encoding='utf-8').replace('</body>','<script src="settings-support.js"></script></body>');path.write_text(text,encoding='utf-8')
(runtime/'distribution').mkdir(exist_ok=True)
policy={'policies':{'DisableTelemetry':True,'DisableFirefoxStudies':True,'DontCheckDefaultBrowser':True,'NoDefaultBookmarks':True,'OverrideFirstRunPage':'','OverridePostUpdatePage':'','Preferences':{'browser.shell.checkDefaultBrowser':False,'browser.newtabpage.enabled':False,'browser.tabs.warnOnClose':False,'browser.aboutwelcome.enabled':False,'datareporting.policy.dataSubmissionEnabled':False,'privacy.globalprivacycontrol.enabled':True,'network.proxy.failover_direct':False,'fission.autostart':True,'browser.safebrowsing.malware.enabled':True,'browser.safebrowsing.phishing.enabled':True,'browser.startup.preXulSkeletonUI':False}}}
(runtime/'distribution/policies.json').write_text(json.dumps(policy,indent=2))
provenance={'name':'Soulu Gecko Preview 2','firefox':version,'platform':platform,'mozilla_archive':base+'/'+rel,'mozilla_sha256':digest,'adblock':'Same Rust source and bundled filters as Soulu CEF','soulu_source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
(out/'BUILD.json').write_text(json.dumps(provenance,indent=2))
shutil.copy(ROOT/'gecko/README.md',out/'README.md')
print('Prepared',out,flush=True)
