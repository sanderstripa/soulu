"""Assemble on top of the immutable, user-installed Preview 17 release."""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import re
import shutil
import struct
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
archive = root / 'preview17-input/Soulu-0.17.0-Preview-Setup-win64.exe'
out = root / 'gecko-out'
raw = archive.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '1e45862d00e9b05f9785e21915cc1d7c284c010f9343e6885edb1ffb6b3e8a56'
for match in re.finditer(b'PK\x05\x06', raw):
    pos = match.start()
    size, offset, comment = struct.unpack_from('<IIH', raw, pos + 12)
    start = pos - size - offset
    if start < 0 or raw[start:start+4] != b'PK\x03\x04':
        continue
    with zipfile.ZipFile(io.BytesIO(raw[start:pos+22+comment])) as payload:
        if 'engine/SouluEngine.exe' not in payload.namelist():
            continue
        for entry in payload.namelist():
            path = PurePosixPath(entry)
            assert not path.is_absolute() and '..' not in path.parts and ':' not in entry
        payload.extractall(out)
        break
else:
    raise ValueError('Preview 17 payload missing')

subprocess.run(['python',str(root/'gecko/upgrade-runtime22.py')],check=True)
chrome = out / 'engine/soulu/chrome'
ui = chrome / 'ui'
for name in ['browser.js','window-controls.sys.mjs','shell-host.js','build-info.sys.mjs','updates.js']:
    source = (root / 'gecko/chrome' / name).read_text(encoding='utf-8')
    (chrome / name).write_text(re.sub(r'0\.(?:13|14)\.0 Preview','Preview 1.160.22',source),encoding='utf-8')
for path in chrome.rglob('*'):
    if path.suffix in {'.js','.html','.mjs'} and 'third_party' not in path.parts:
        source = path.read_text(encoding='utf-8')
        if '0.17.0' in source:
            path.write_text(source.replace('0.17.0','1.160.22'),encoding='utf-8')
def patch(path, before, after):
    source = path.read_text(encoding='utf-8')
    if before not in source:
        raise ValueError(f'Unexpected markup in {path.name}: {before}')
    path.write_text(source.replace(before,after),encoding='utf-8')

index = ui / 'index.html'
index.write_text(index.read_text(encoding='utf-8').replace('data-matte="true"','data-matte="false"'),encoding='utf-8')
patch(ui/'renderer.js','if(!wanted.has(id))node.remove();','if(!wanted.has(id)){souluTabExit(node);node.remove();}')
patch(ui/'renderer.js','if(container.children[index]!==node)container.insertBefore(node,container.children[index]||null);',"""
    const entering = !node.isConnected;
    if(container.children[index]!==node)container.insertBefore(node,container.children[index]||null);
    if(entering && !matchMedia('(prefers-reduced-motion:reduce)').matches){
      node.animate([{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:170});
    }""")
patch(ui/'renderer.js','function reconcileClassicTabs(','''function souluTabExit(node) {
  if(matchMedia('(prefers-reduced-motion:reduce)').matches)return;
  const r=node.getBoundingClientRect();
  if(!r.width||!r.height)return;
  const ghost=node.cloneNode(true);
  ghost.inert=true;
  ghost.setAttribute('aria-hidden','true');
  ghost.style.cssText='position:fixed;pointer-events:none;z-index:10;'+
    'left:'+r.left+'px;top:'+r.top+'px;width:'+r.width+'px;height:'+r.height+'px';
  document.body.append(ghost);
  const animation=ghost.animate([{opacity:1},{opacity:0,transform:'translateY(-5px)'}],{duration:130,fill:'both'});
  animation.finished.finally(()=>ghost.remove());
}
function reconcileClassicTabs(''')
for path in (out/'engine').rglob('*.exe'):
    if path.name.lower() in {'private_browsing.exe','firefox.exe','helper.exe','default-browser-agent.exe','maintenanceservice_installer.exe'}:
        path.unlink()
build = json.loads((out/'BUILD.json').read_text(encoding='utf-8'))
assert build['name'] == 'Soulu 0.17.0 Preview'
build.update(firefox='160.0',mozilla_archive='https://archive.mozilla.org/pub/firefox/releases/160.0/win64/ru/Firefox Setup 160.0.exe',mozilla_sha256='9aca6af4a633546ce9908894d735b0518c36b6a54f108566e517225983cf5173')
build.update(name='Soulu Preview 1.160.22',base_preview=17,soulu_source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
(out/'BUILD.json').write_text(json.dumps(build,indent=2),encoding='utf-8')

patch(ui/'renderer.js','mattePanel:true','mattePanel:false,showExtensions:false,showHome:false')
patch(ui/'renderer.js','vpnToolbarVisible:true','vpnToolbarVisible:false')
patch(ui/'navigation.js','Firefox: экспорт закладок HTML.','Для других браузеров — экспорт закладок в HTML.')
patch(ui/'settings.js','[{opacity:.94},{opacity:1}]',"[{opacity:reduced?1:0.6,transform:reduced?'none':'translateY(5px)'},{opacity:1,transform:'none'}]")
# Apply the product strings at their native resource locations before the first
# window loads, including native dialogs opened outside the browser window.
bundle = out/'engine/browser/omni.ja'
subprocess.run(['python',str(root/'gecko/prepare-icons22.py')],check=True)
temporary = bundle.with_suffix('.new')
with zipfile.ZipFile(bundle) as source, zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as target:
    for name in source.namelist():
        data = source.read(name)
        if name.endswith('default-bookmarks.html'):
            data=b'<!DOCTYPE NETSCAPE-Bookmark-file-1><TITLE>Bookmarks</TITLE><DL><p></DL><p>'
        elif name.endswith('/branding/brand.properties'):
            data = (chrome/'branding/brand.properties').read_bytes()
        elif name.endswith('/branding/brand.ftl'):
            locale = name.split('/')[-3]
            data = (chrome/'locales'/locale/'branding/brand.ftl').read_bytes()
        if '/branding/' in name and name.endswith('.png'):
            from PIL import Image
            old_image=Image.open(io.BytesIO(data))
            output=io.BytesIO()
            Image.open(root/'gecko/chrome/branding/soulu-wave.png').resize(old_image.size,Image.Resampling.LANCZOS).save(output,format='PNG')
            data=output.getvalue()
        private_page = root/'gecko/private-page'/PurePosixPath(name).name
        if name.startswith('chrome/browser/content/browser/') and private_page.is_file():
            data = private_page.read_bytes()
        target.writestr(name,data)
temporary.replace(bundle)
for name in ['firefox.VisualElementsManifest.xml','private_browsing.VisualElementsManifest.xml','firefox.exe.sig']:
    (out/'engine'/name).unlink(missing_ok=True)
shutil.copyfile(root/'gecko/chrome/early.css',chrome/'early.css')
patch(ui/'navigation.js','if(entered){closeEditor(false);closeMenu();}render();',"""if(entered){closeEditor(false);closeMenu();}render();
 if(entered&&!matchMedia('(prefers-reduced-motion:reduce)').matches){
  overview.animate([{opacity:0,transform:'translateY(6px)'},{opacity:1,transform:'none'}],{duration:180,easing:'ease-out'});
 }
""")

patch(ui/'navigation.js','renderMenu();menuSearch.focus();','renderMenu();')
shutil.copyfile(root/'ui/settings-components.js',ui/'settings-components.js')
with (ui/'gecko-frontend.css').open('a',encoding='utf-8') as css:
    css.write((root/'gecko/chrome/navigation-fixes.css').read_text(encoding='utf-8'))

# The new native tab briefly has about:blank before the home document commits.
# Never populate address suggestions with this transient startup URI.
patch(ui/'renderer.js',"input.value=state.page?.url==='soulu://home'?'':state.page?.url||'';",
      "input.value=['soulu://home','about:blank'].includes(state.page?.url)?'':state.page?.url||'';")
patch(ui/'renderer.js',"if(input&&state.page?.url==='soulu://home'){",
      "if(input&&['soulu://home','about:blank'].includes(state.page?.url)){")

patch(ui/'navigation.js', 'menu.append(menuHeading,menuSearch,contents,actions);',
      (root/'gecko/chrome/bookmark-scroll.inc.js').read_text(encoding='utf-8'))
patch(ui/'navigation.js', 'caption.append(icon(tab),title,close);', '''
 close.innerHTML='<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 5L19 19M19 5L5 19"/></svg>';
 caption.append(icon(tab),title,close);''')
# The popover lives outside the setting row. Read the trigger's actual type
# after layout so language, local theme and text scaling are respected.
patch(ui/'select-control.js','menu.showPopover();position();','''
 const type=getComputedStyle(button);
 for(const key of ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing'])
   menu.style[key]=type[key];
 menu.showPopover();position();''')
with (ui/'select-control.css').open('a', encoding='utf-8') as css:
    css.write('\n.soulu-select-menu .soulu-select-option {font:inherit;letter-spacing:inherit;padding:6px 12px}\n')

# Pin the bundled interface font and verify the bytes before packaging.
import urllib.request
font_url = 'https://raw.githubusercontent.com/google/fonts/5bb28733cec313b63fbd415b574b5ae35c8aa8b8/ofl/inter/'
font_data = urllib.request.urlopen(font_url+'Inter%5Bopsz,wght%5D.ttf',timeout=60).read()
assert hashlib.sha256(font_data).hexdigest() == '29160a80ff49ddcab2c97711247e08b1fab27a484a329ce8b813d820dc559031'
(ui/'fonts/Inter.ttf').write_bytes(font_data)
(ui/'fonts/Inter-OFL.txt').write_bytes(urllib.request.urlopen(font_url+'OFL.txt',timeout=30).read())
# Convert every owned application document, including VPN, onboarding and menus.
for path in chrome.rglob('*'):
    if path.suffix not in {'.css','.js','.mjs','.html','.json'} or 'third_party' in path.parts:
        continue
    source = path.read_text(encoding='utf-8')
    for weight in ['Regular','Medium','SemiBold']:
        source = source.replace('Onest-'+weight+'.ttf','Inter.ttf')
    source = source.replace('Onest','Inter')
    path.write_text(source,encoding='utf-8')
# Variable Inter supplies real weights throughout the interface.
with (chrome/'early.css').open('a',encoding='utf-8') as css:
    css.write("""
@-moz-document url-prefix("chrome://"), url-prefix("about:") {
 @font-face{font-family:Inter;src:url("chrome://soulu/content/ui/fonts/Inter.ttf");font-weight:100 900}
 :root,body,button,input,select,textarea,menu,menuitem,menucaption,menulist,label,description,.menu-text,.menu-iconic-text{font-family:Inter,"Segoe UI Emoji","Segoe UI Symbol",sans-serif!important}
}
""")
with (ui/'typography.css').open('a',encoding='utf-8') as css:
    css.write('\n@font-face{font-family:Inter;src:url("fonts/Inter.ttf");font-weight:100 900;font-display:block}\n')

patch(ui/'settings.js',"[['Soulu',state.update?.soulu],['Движок',state.update?.gecko],['Xray',state.update?.xray],['Sudoku',state.update?.sudoku],['Adblock',state.update?.adblock]]",
      "[['Soulu',state.update?.soulu],['Gecko',state.update?.gecko]]")
patch(ui/'settings.js',"old.updates.groups.push(group('Компоненты VPN'",
      "old.updates.groups[0].ru='Браузер';old.updates.groups[0].en='Browser';old.updates.groups[0].rows[0].ru='Soulu и Gecko';old.updates.groups[0].rows[0].en='Soulu and Gecko';old.updates.groups.push(group('Adblock','Adblock',[row('adblockManager','Блокировка рекламы','Ad blocking','adblockManager')]));old.updates.groups.push(group('Компоненты VPN'")
patch(ui/'settings.js',"if(r.type==='extensionCatalog'){","if(r.type==='adblockManager'){n.classList.add('long');const host=el('div');host.dataset.adblockManager='true';n.append(host);card.append(n);continue;}if(r.type==='extensionCatalog'){")
shutil.copyfile(root/'gecko/chrome/adblock-about.js',ui/'adblock-about.js')
patch(ui/'settings.html','</head>','<script defer src="adblock-about.js"></script></head>')
# Bootstrap readiness can precede the first remote surface composite.
# Flush both UI and host paint before revealing the native window.

subprocess.run(['python',str(root/'gecko/prepare-icons22.py')],check=True)

shutil.copyfile(root/'gecko/chrome/updates.js',chrome/'updates.js')
