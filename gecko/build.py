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
shutil.copy(ROOT/'gecko/chrome/translation-gecko-ui.js',runtime/'soulu/chrome/ui/translation-gecko-ui.js')
shutil.copy(ROOT/'gecko/chrome/frontend.css',runtime/'soulu/chrome/ui/gecko-frontend.css')
shutil.copy(ROOT/'gecko/chrome/extensions-ui.js',runtime/'soulu/chrome/ui/extension-toolbar.js')
shutil.copy(ROOT/'gecko/chrome/integration-ui.js',runtime/'soulu/chrome/ui/integration-ui.js')
shutil.copy(ROOT/'gecko/chrome/tab-preview-ui.js',runtime/'soulu/chrome/ui/tab-preview-ui.js')
shutil.copy(ROOT/'gecko/chrome/vot-ui.js',runtime/'soulu/chrome/ui/vot-ui.js')
shutil.copy(ROOT/'gecko/chrome/updates-ui.js',runtime/'soulu/chrome/ui/updates-ui.js')
shutil.copy(ROOT/'gecko/chrome/onboarding-ui.js',runtime/'soulu/chrome/ui/onboarding.js')
# Install the bridge before the unchanged frontend scripts run.
for page in ['index.html','settings.html','home.html','history.html','onboarding.html']:
 path=runtime/'soulu/chrome/ui'/page
 content=path.read_text(encoding='utf-8')
 if page=='index.html':
  import re
  content=re.sub(r'<script src="(?:third_party/bergamot-runtime.js|third_party/tinyld.js|translation-models.js|translation-service.js|translation-ui.js)"></script>','',content)
 if page=='index.html':content=content.replace('</body>','<script src="translation-gecko-ui.js"></script><script src="integration-ui.js"></script><script src="tab-preview-ui.js"></script></body>')
 content=content.replace('<head>','<head><link rel="stylesheet" href="gecko-frontend.css"><script src="gecko-bridge.js"></script>',1)
 path.write_text(content,encoding='utf-8')
js=runtime/'soulu/chrome/ui/settings.js';text=js.read_text(encoding='utf-8')
text=text.replace('Автоматическое определение использует разрешённую геолокацию Windows.','Автоматическое определение использует разрешённую геолокацию браузера.')
# Only the adaptive Soulu toolbar is exposed.
text=text.replace(",opt('compact','Компактная','Compact')",'')
text=text.replace("['CEF',state.update?.cef],['Chromium',state.update?.chromium]","['Gecko',state.update?.gecko],['Firefox',state.update?.firefox]")
text=text.replace("['Firefox',state.update?.firefox]","['Firefox',state.update?.firefox],['Xray',state.update?.xray],['Sudoku',state.update?.sudoku],['Adblock',state.update?.adblock]")
# Avoid rebuilding an embedded Chrome page; use Firefox's actual manager/store.
start=text.index("          n.classList.add('long');n.replaceChildren();card.querySelector('h3')?.remove();")
end=text.index("        if(r.key==='defaultBrowser')",start)
text=text[:start]+"          n.classList.add('long');n.replaceChildren();const controls=el('div',undefined,'extension-controls');controls.append(button(t('Установленные расширения','Installed extensions'),()=>browserShell.extensions('manage',{profile:state.activeProfileId})),button('Каталог расширений',()=>browserShell.openTab('https://addons.mozilla.org/firefox/')));n.append(controls,el('p',t('Расширения устанавливаются из Каталог расширений. Локальные подписанные XPI можно установить через менеджер расширений.','Install extensions from Каталог расширений. Local signed XPI packages can be installed in the extension manager.'),'note'));const pins=el('div',undefined,'extension-pin-list');pins.id='extensionPins';n.append(pins);renderExtensionPins(pins);card.append(n);continue;\n        }\n"+text[end:]
text=text.replace("setInterval(()=>{const host=$('extensionPins');if(current&&section==='extensions'&&host)renderExtensionPins(host);},3000);","window.addEventListener('SouluExtensionsChanged',()=>{const host=$('extensionPins');if(current&&section==='extensions'&&host)renderExtensionPins(host);});")
text=text.replace("search.focus();","search.blur();")
text=text.replace("[{opacity:0,transform:reduced?'none':'translateY(5px)'},{opacity:1,transform:'none'}]","[{opacity:.94},{opacity:1}]").replace("duration:reduced?90:320,delay:reduced?0:45","duration:reduced?60:140,delay:0")
text=text.replace("...(id?[document.querySelector('aside')]:[])","...[]")
text=text.replace("$('settingsSearch').focus();","$('settingsSearch').blur();")
js.write_text(text,encoding='utf-8')
renderer=runtime/'soulu/chrome/ui/renderer.js';text=renderer.read_text(encoding='utf-8').replace('const disconnect=vpnState==="connected"','const disconnect=vpnState==="connected"||vpnState==="error"').replace('function renderTabs(){renderClassicTabs();renderCompactTabs();}', 'function renderTabs(){if(state.settings.layout==="compact")renderCompactTabs();else renderClassicTabs();}');text=text.replace(' data-tooltip="${attributeTitle}"','').replace("['aria-selected','aria-label','data-tooltip']","['aria-selected','aria-label']");renderer.write_text(text,encoding='utf-8')
data=runtime/'soulu/chrome/ui/settings-data.js';text=data.read_text(encoding='utf-8')
text=text.replace('Пароли активного профиля защищены учётной записью Windows.','Пароли активного профиля защищены хранилищем NSS Firefox.').replace('Passwords for the active profile are protected by your Windows account.','Passwords for the active profile are protected by the Firefox NSS store.')
text=text.replace('Пароль скопирован. Пока Soulu запущен, буфер очистится через 30 секунд, если его содержимое не изменится.','Пароль скопирован.').replace('Password copied. While Soulu runs, the clipboard clears after 30 seconds if its content stays unchanged.','Password copied.')
text=text.replace("n.append(text,actionButton('Открыть'","n.dataset.profileId=p.id;n.append(text,actionButton('Открыть'")
text=text.replace('let rows=await api.getPasswords()', 'let editing=null;let rows=await api.getPasswords()').replace('origin.n.value=item.origin;', 'editing=item.id;origin.n.value=item.origin;').replace('api.addPassword({origin:', 'api.addPassword({id:editing,origin:').replace("secret.n.value='';draw();message","editing=null;secret.n.value='';draw();message")
data.write_text(text,encoding='utf-8')
navigation=runtime/'soulu/chrome/ui/navigation.js';text=navigation.read_text(encoding='utf-8').replace('renderOverview();search.focus();','renderOverview();search.blur();overview.tabIndex=-1;overview.focus({preventScroll:true});');start=text.index('  function renderOverview(){');end=text.index('  function render(){',start);text=text[:start]+(ROOT/'gecko/chrome/overview-renderer.inc.js').read_text(encoding='utf-8')+text[end:];navigation.write_text(text,encoding='utf-8')
home=runtime/'soulu/chrome/ui/home.js';text=home.read_text(encoding='utf-8').replace("invoke('home.weather')","invoke('home.weather',{interactive:force})").replace('12000))','25000))').replace("el('p',t('unavailable'),'weather-note')","el('p',weather.error||t('unavailable'),'weather-note')");text=text.replace('await navigate(result.text);', "$('query').focus();");text+="\nwindow.souluHomeVoicePhase=phase=>{document.getElementById('status').textContent=phase==='processing'?'Распознавание на этом компьютере…':'Говорите… Нажмите микрофон ещё раз для отмены.';};\n";home.write_text(text,encoding='utf-8')
# Optional engine-specific features keep their sections and report availability explicitly.
shutil.copy(ROOT/'gecko/chrome/settings-support.js',runtime/'soulu/chrome/ui/settings-support.js')
path=runtime/'soulu/chrome/ui/settings.html';text=path.read_text(encoding='utf-8').replace('</body>','<script src="settings-support.js"></script><script src="integration-ui.js"></script><script src="vot-ui.js"></script><script src="updates-ui.js"></script></body>');path.write_text(text,encoding='utf-8')
(runtime/'distribution').mkdir(exist_ok=True)
policy={'policies':{'DisableTelemetry':True,'DisableFirefoxStudies':True,'DontCheckDefaultBrowser':True,'NoDefaultBookmarks':True,'OverrideFirstRunPage':'','OverridePostUpdatePage':'','Preferences':{'browser.shell.checkDefaultBrowser':False,'browser.newtabpage.enabled':False,'browser.tabs.warnOnClose':False,'browser.aboutwelcome.enabled':False,'datareporting.policy.dataSubmissionEnabled':False,'privacy.globalprivacycontrol.enabled':True,'network.proxy.failover_direct':False,'fission.autostart':True,'browser.safebrowsing.malware.enabled':True,'browser.safebrowsing.phishing.enabled':True,'browser.startup.preXulSkeletonUI':False,'browser.startup.blankWindow':False,'widget.windows.overlay-scrollbars.enabled':False,'browser.shell.defaultBrowserCheckCount':9999,'browser.newtabpage.activity-stream.asrouter.providers.onboarding':json.dumps({'id':'onboarding','type':'local','localProvider':'OnboardingMessageProvider','enabled':False}),'browser.newtabpage.activity-stream.asrouter.providers.messaging-experiments':json.dumps({'id':'messaging-experiments','type':'remote-experiments','enabled':False})}}}
# Firefox 159 ServiceRequest assumes active policies are an array, while its
# EnterprisePolicies API returns an object. Use distribution defaults so native
# Remote Settings/model downloads are not broken by our own Preferences policy.
(runtime/'distribution/policies.json').write_text(json.dumps({'policies':{}}))
defaults=dict(policy['policies']['Preferences'])
defaults.update({'termsofuse.bypassNotification':True,'datareporting.policy.dataSubmissionPolicyBypassNotification':True,'datareporting.healthreport.uploadEnabled':False,'datareporting.usage.uploadEnabled':False,'browser.preonboarding.enabled':False,'toolkit.telemetry.enabled':False,'app.shield.optoutstudies.enabled':False,'browser.newtabpage.activity-stream.feeds.telemetry':False,'browser.translations.automaticallyPopup':False,'browser.translations.enable':True,'browser.startup.homepage_override.mstone':'ignore'})
with (runtime/'defaults/pref/autoconfig.js').open('a',encoding='utf-8') as f:
 for key,value in defaults.items():f.write('\n'+'pref('+json.dumps(key)+','+json.dumps(value)+');')

provenance={'channel':'gecko-preview','name':'Soulu Gecko Preview 8','firefox':version,'platform':platform,'mozilla_archive':base+'/'+rel,'mozilla_sha256':digest,'adblock':'Same Rust source and bundled filters as Soulu CEF','soulu_source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
(out/'BUILD.json').write_text(json.dumps(provenance,indent=2))
shutil.copy(ROOT/'gecko/README.md',out/'README.md')
print('Prepared',out,flush=True)
