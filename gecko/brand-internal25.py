"""Brand native documents without changing security handlers or engine namespaces."""
from pathlib import Path
import base64,io,json,re,zipfile
from PIL import Image
root=Path(__file__).resolve().parents[1];engine=root/'gecko-out/engine'
# Force policy on existing profiles as well as new installations.
bootstrap=engine/'soulu.cfg'
s=bootstrap.read_text(encoding='utf-8')
inject='''
  // Soulu starts only when explicitly opened, never at Windows sign-in/restart.
  for(const name of ['browser.startup.windowsLaunchOnLogin.defaultEnabled','browser.startup.windowsLaunchOnLogin.enabled','toolkit.winRegisterApplicationRestart']) {
    try{Services.prefs.unlockPref(name);}catch{}
    Services.prefs.clearUserPref(name);Services.prefs.getDefaultBranch('').setBoolPref(name,false);Services.prefs.lockPref(name);
  }
  Services.prefs.getDefaultBranch('').setBoolPref('browser.startup.windowsLaunchOnLogin.disableLaunchOnLoginPrompt',true);

  for(const name of ['browser.ml.chat.enabled','browser.ml.chat.menu','browser.ml.chat.page','browser.ml.chat.shortcuts','browser.ml.chat.sidebar','browser.ml.linkPreview.enabled','browser.ml.linkPreview.optin','browser.tabs.groups.smart.userEnabled','browser.aiwindow.enabled']){
    try{Services.prefs.unlockPref(name);}catch{}
    Services.prefs.clearUserPref(name);Services.prefs.getDefaultBranch('').setBoolPref(name,false);Services.prefs.lockPref(name);
  }
  // Site compatibility, not product branding. Retain standard Gecko tokens.
  for(const name of ['general.useragent.override','general.useragent.compatMode.firefox']){try{Services.prefs.unlockPref(name);}catch{}}
  Services.prefs.clearUserPref('general.useragent.compatMode.firefox');Services.prefs.getDefaultBranch('').setBoolPref('general.useragent.compatMode.firefox',true);
  Services.prefs.clearUserPref('general.useragent.override');Services.prefs.getDefaultBranch('').setStringPref('general.useragent.override','Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) Gecko/20100101 Firefox/160.0 Soulu/1.160.29');
  Services.prefs.lockPref('general.useragent.override');
'''
s=s.replace('  const app = Services.dirsvc.get',inject+'\n  const app = Services.dirsvc.get');bootstrap.write_text(s,encoding='utf-8')
style=(root/'gecko/chrome/internal-theme25.css').read_text(encoding='utf-8')
# At the native stylesheet sources so remote about: pages inherit the theme too.
petals=base64.b64encode((engine/'soulu/chrome/ui/browser-icon.png').read_bytes()).decode()
logo_svg=('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 256 256"><image width="256" height="256" xlink:href="data:image/png;base64,'+petals+'"/></svg>').encode()
report=[]
for archive in [engine/'omni.ja',engine/'browser/omni.ja']:
 temp=archive.with_suffix('.branded')
 with zipfile.ZipFile(archive) as source,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as target:
  for name in source.namelist():
   data=source.read(name);changes=[]
   if name.endswith('/LocalModeMappings.sys.mjs'):
    text=data.decode();before='return `firefox${originIndex == 0 ? "" : originIndex}.localhost`;'
    assert before in text
    text=text.replace(before,'return `soulu${originIndex == 0 ? "" : originIndex}.localhost`;').replace('/firefox(?<origin_index>', '/(?:firefox|soulu)(?<origin_index>')
    data=text.encode();changes.append('Soulu local-development origin; legacy mappings preserved')
   if name.endswith('.svg') and (re.search(r'(?:firefox|mozilla|fox(?:y)?[-.]|[-/]fox[-.]|kit-)',Path(name).name,re.I) or ('/illustrations/' in name and Path(name).name in {'no-connection.svg','security-error.svg','error-malformed-url.svg'})):
    data=logo_svg;changes.append('replaced mascot with Soulu petals')
   if name.endswith(('.png','.webp')) and re.search(r'(?:firefox|mozilla|fox[-.]|[-/]fox[-.])',Path(name).name,re.I):
    old=Image.open(io.BytesIO(data));art=Image.open(engine/'soulu/chrome/ui/browser-icon.png').convert('RGBA');art.thumbnail(old.size,Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',old.size);canvas.alpha_composite(art,((old.width-art.width)//2,(old.height-art.height)//2));output=io.BytesIO();canvas.save(output,format='WEBP' if name.endswith('.webp') else 'PNG');data=output.getvalue();changes.append('Soulu raster branding')
   if '/branding/' in name and name.endswith('.svg'):
    if 'wordmark' in name:
     data=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 50"><text x="0" y="38" font-family="Inter, sans-serif" font-size="40" fill="context-fill">Soulu</text></svg>'
    else:data=logo_svg
    changes.append('Soulu vector branding')
   if name.endswith(('/in-content/common.css','/aboutNetError.css')):
    data+=('\n'+style).encode();changes.append('Soulu native palette and error artwork')
   # Only human-readable translations; never alter resource IDs, URLs or licenses.
   if ('/localization/' in '/'+name or name.startswith('localization/')) and name.endswith(('.ftl','.properties')) and not any(part in name.lower() for part in ['license','rights','credits']):
    text=data.decode('utf-8');lines=[]
    for line in text.splitlines(keepends=True):
     if (not line.lstrip().startswith(('#','!')) and '=' in line) or line.startswith((' ','\t')):
      if '://' not in line and 'Mozilla Public License' not in line:
       line=re.sub(r'\b(?:Mozilla Firefox|Firefox|Mozilla)\b','Soulu',line)
     lines.append(line)
    updated=''.join(lines).encode()
    if updated!=data:changes.append('visible product strings');data=updated
   target.writestr(name,data)
   if changes:report.append({'archive':archive.relative_to(engine).as_posix(),'resource':name,'changes':changes})
 temp.replace(archive)
# User sheet covers native dialogs and DevTools, never ordinary site content.
with (engine/'soulu/chrome/early.css').open('a',encoding='utf-8') as f:
 f.write('\n@-moz-document url-prefix("about:"),url-prefix("chrome://browser/"),url-prefix("chrome://global/"),url-prefix("chrome://devtools/"){\n'+style+'\n}\n')
(root/'gecko-out/internal-branding-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert any(x['resource'].endswith('aboutNetError.css') for x in report)
