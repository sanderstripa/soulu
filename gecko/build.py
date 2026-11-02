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
pin=json.loads((ROOT/'gecko/runtime-pin.json').read_text())
version=pin['version'];platform=args.platform
base=f'https://archive.mozilla.org/pub/firefox/releases/{version}'
checks=fetch(base+'/SHA256SUMS',cache/f'{version}-SHA256SUMS')
rel=f'{platform}/en-US/Firefox Setup {version}.exe' if platform=='win64' else f'{platform}/en-US/firefox-{version}.tar.xz'
archive=fetch(base+'/'+urllib.request.quote(rel),cache/pathlib.Path(rel).name)
expected=pin['archives'][platform]['sha256']
assert next(line.split()[0] for line in checks.read_text().splitlines() if line.split(maxsplit=1)[1].lstrip('*')==rel)==expected
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
shutil.copy(ROOT/'gecko/chrome.manifest',runtime/'soulu/chrome.manifest')
shutil.copy(ROOT/'gecko/soulu.cfg',runtime/'soulu.cfg')
(runtime/'defaults/pref').mkdir(parents=True,exist_ok=True)
shutil.copy(ROOT/'gecko/defaults/pref/autoconfig.js',runtime/'defaults/pref/autoconfig.js')
# Reuse the exact current Soulu settings DOM/CSS and substitute only its backend.
settings=runtime/'soulu/chrome/ui/settings.html'
s=settings.read_text();s=s.replace('<script src="motion.js">','<script src="../bridge.js"></script><script src="motion.js">');settings.write_text(s)
js=runtime/'soulu/chrome/ui/settings.js';s=js.read_text();s=s.replace("opt('adaptive','Основная','Main'),opt('compact','Компактная','Compact')","opt('adaptive','Основная','Main')")
s=s.replace("['CEF',state.update?.cef],['Chromium',state.update?.chromium]","['Gecko',state.update?.gecko],['Firefox',state.update?.firefox]")
s=s.replace("chromewebstore.google.com","addons.mozilla.org/firefox")
# Native Firefox managers provide these actions without extracting passwords into the Soulu page.
s=s.replace("if(key==='history'||key==='clearData')", "if(key==='passwords')return window.browserShell.openTab('about:logins');if(key==='import')return window.browserShell.openTab('about:preferences#general');if(key==='siteData')return window.browserShell.openTab('about:preferences#privacy');if(key==='history'||key==='clearData')")
# Extensions run in Firefox's native, sandboxed manager rather than the CEF embedded frame.
s=s.replace("const extensions={", "const extensions={")
js.write_text(s)
import importlib.util
spec=importlib.util.spec_from_file_location('adapt',ROOT/'gecko/adapt-settings.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter);adapter.adapt(js)
(runtime/'distribution').mkdir(exist_ok=True)
# Signed full uBlock Origin, not the Chromium MV3 lite variant.
addon=fetch(pin['ublock']['url'],cache/'ublock-origin.xpi')
if hashlib.sha256(addon.read_bytes()).hexdigest()!=pin['ublock']['sha256']:raise RuntimeError('uBlock integrity mismatch')
with zipfile.ZipFile(addon) as z:
 manifest=json.loads(z.read('manifest.json'));assert manifest.get('browser_specific_settings',manifest.get('applications',{}))['gecko']['id']=='uBlock0@raymondhill.net'
shutil.copy(addon,runtime/'soulu/ublock-origin.xpi')
(runtime/'distribution/extensions').mkdir(exist_ok=True)
shutil.copy(addon,runtime/'distribution/extensions/uBlock0@raymondhill.net.xpi')
policy={'policies':{'DisableTelemetry':True,'DisableFirefoxStudies':True,'DisablePocket':True,'DontCheckDefaultBrowser':True,'NoDefaultBookmarks':True,'OverrideFirstRunPage':'','OverridePostUpdatePage':'','Preferences':{'browser.shell.checkDefaultBrowser':False,'browser.startup.homepage':'about:blank','browser.newtabpage.enabled':False,'browser.tabs.warnOnClose':False,'browser.aboutwelcome.enabled':False,'datareporting.policy.dataSubmissionEnabled':False,'privacy.globalprivacycontrol.enabled':True,'network.proxy.failover_direct':False,'fission.autostart':True,'browser.safebrowsing.malware.enabled':True,'browser.safebrowsing.phishing.enabled':True},'ExtensionSettings':{'uBlock0@raymondhill.net':{'installation_mode':'normal_installed','install_url':'https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi'}}}}
(runtime/'distribution/policies.json').write_text(json.dumps(policy,indent=2))
provenance={'name':'Soulu Gecko Preview 1','firefox':version,'platform':platform,'mozilla_archive':base+'/'+rel,'mozilla_sha256':digest,'ublock_version':manifest['version'],'ublock_sha256':hashlib.sha256(addon.read_bytes()).hexdigest(),'soulu_source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
(out/'BUILD.json').write_text(json.dumps(provenance,indent=2))
shutil.copy(ROOT/'gecko/README.md',out/'README.md')
print('Prepared',out,flush=True)
