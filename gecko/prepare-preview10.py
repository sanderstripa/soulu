"""Overlay only Preview 10 fixes onto the verified Preview 8 artifact."""
import hashlib,json,pathlib,shutil,subprocess
root=pathlib.Path(__file__).resolve().parents[1];out=root/'gecko-out';runtime=out/'runtime'
assert (out/'BUILD.json').is_file(), 'Preview 8 build artifact missing'
build=json.loads((out/'BUILD.json').read_text());assert build['name']=='Soulu Gecko Preview 8',build
# Never run the Mozilla installer. Reuse the exact already-extracted Preview 8
# runtime and auxiliary components; only Soulu resources/launcher are updated.
for p in (root/'gecko/chrome').rglob('*'):
 if p.is_file():
  target=runtime/'soulu/chrome'/p.relative_to(root/'gecko/chrome');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
shutil.copyfile(root/'gecko/soulu.cfg',runtime/'soulu.cfg')
for source,target in [('integration-ui.js','integration-ui.js'),('onboarding-ui.js','onboarding.js')]:shutil.copyfile(root/'gecko/chrome'/source,runtime/'soulu/chrome/ui'/target)
for page in ['onboarding.html','settings.html']:
 p=runtime/'soulu/chrome/ui'/page;text=p.read_text(encoding='utf-8');text=text.replace('</body>','<script src="import-ui.js"></script></body>');p.write_text(text,encoding='utf-8')
shutil.copyfile(root/'gecko/chrome/import-ui.js',runtime/'soulu/chrome/ui/import-ui.js')
with (runtime/'soulu/chrome/ui/gecko-frontend.css').open('a',encoding='utf-8') as f:f.write('\n.soulu-import{width:min(620px,calc(100vw - 48px));box-sizing:border-box;border:1px solid #80808040;border-radius:20px;padding:28px;background:light-dark(#f6f6f8,#15171b);color:light-dark(#191a1e,#eeeeef);font:14px Onest,Segoe UI,sans-serif;color-scheme:light dark}.soulu-import::backdrop{background:#0006;backdrop-filter:blur(8px)}.soulu-import select{width:100%;padding:10px;border-radius:10px}.soulu-import fieldset{border:0;display:flex;flex-wrap:wrap;gap:16px;margin:20px 0;padding:0}.soulu-import label{display:flex;align-items:center;gap:6px}.soulu-import-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}.soulu-import button{padding:10px 14px;border-radius:10px;border:1px solid #80808040;font:inherit}.soulu-import .primary{background:#0879e6;color:white}.soulu-import p{line-height:1.5}')
# Suppress automatic Firefox OS integration and remove registration/install tools,
# including uninstall/helper.exe, not just files in the runtime root.
for p in list(runtime.rglob('*')):
 if p.is_file() and (p.name.lower() in {'default-browser-agent.exe','maintenanceservice.exe','maintenanceservice_installer.exe','updater.exe','helper.exe'}):p.unlink()
shutil.rmtree(runtime/'uninstall',ignore_errors=True)
with (runtime/'defaults/pref/autoconfig.js').open('a',encoding='utf-8') as f:
 for key,value in {'default-browser-agent.enabled':False,'browser.shell.checkDefaultBrowser':False,'browser.startup.preXulSkeletonUI':False,'browser.startup.blankWindow':False}.items():f.write('\npref('+json.dumps(key)+','+json.dumps(value)+');')
# Product UI uses only Soulu naming; engine attribution stays in license files.
for name in ['settings.js','settings-data.js','settings-support.js']:
 p=runtime/'soulu/chrome/ui'/name
 text=p.read_text(encoding='utf-8').replace("['Firefox',state.update?.firefox]", "['Движок',state.update?.gecko]").replace('Firefox','Soulu')
 p.write_text(text,encoding='utf-8')
# The updater and Settings must agree with the installer and Windows resources.
build.update(name='Soulu Gecko Preview 10',base_preview=8,soulu_source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
(out/'BUILD.json').write_text(json.dumps(build,indent=2))
