"""Reuse successful Windows binary builds; overlay only reviewable app resources."""
import hashlib,json,pathlib,subprocess,shutil,os
root=pathlib.Path(__file__).resolve().parents[2];out=root/'gecko-out';base='a7624f9fbf951c81d9d72ed23244d7a8c1b892d7'
changed=subprocess.check_output(['git','diff','--name-only',base,'HEAD'],text=True).splitlines()
assert all(p.startswith(('gecko/chrome/','gecko/tests/','gecko/docs/')) or p in ['gecko/soulu.cfg','gecko/README.md','.github/workflows/finalize-gecko5.yml','.github/workflows/package-gecko5.yml'] for p in changed),changed
build=json.loads((out/'BUILD.json').read_text());assert build['soulu_source']==base and build['name']=='Soulu Gecko Preview 5' and build['platform']=='win64'
original=root/'base-evidence'
for name,count in [('gecko5-checks/preview5.json',20),('gecko5-extensions/extensions.json',36)]:
 r=json.loads((original/name).read_text());assert r['passed'] and len(r['checks'])>=count and all(x['passed'] for x in r['checks'].values())
vot=json.loads((original/'gecko5-optional/optional5.json').read_text());keys=['pinned_signed_vot_candidate_loads','vot_install_without_trusted_input_denied','vot_installed_after_explicit_soulu_consent','vot_firefox_signature_and_version','vot_disable_actual_extension','vot_enable_actual_extension'];assert all(vot['checks'][k]['passed'] for k in keys)
def components():return {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.suffix.lower() in ['.exe','.dll','.xpi','.bin']}
before=components()
for path in (root/'gecko/chrome').iterdir():
 if path.is_file():shutil.copyfile(path,out/'runtime/soulu/chrome'/path.name)
for source,target in [('bridge.js','gecko-bridge.js'),('frontend.css','gecko-frontend.css'),('onboarding-ui.js','onboarding.js'),('updates-ui.js','updates-ui.js'),('vot-ui.js','vot-ui.js'),('integration-ui.js','integration-ui.js'),('settings-support.js','settings-support.js'),('translation-gecko-ui.js','translation-gecko-ui.js'),('extensions-ui.js','extension-toolbar.js'),('tab-preview-ui.js','tab-preview-ui.js')]:shutil.copyfile(root/'gecko/chrome'/source,out/'runtime/soulu/chrome/ui'/target)
shutil.copyfile(root/'gecko/soulu.cfg',out/'runtime/soulu.cfg');shutil.copyfile(root/'gecko/README.md',out/'README.md');shutil.copytree(root/'gecko/docs',out/'docs',dirs_exist_ok=True)
assert before==components(),'Executable/model/extension bytes changed'
build.update(soulu_source=os.environ['GITHUB_SHA'],base_source=base,base_windows_run=41700314952,unchanged_binary_components=len(before));(out/'BUILD.json').write_text(json.dumps(build,indent=2),encoding='utf-8')
(out/'vot5.json').write_text(json.dumps({'passed':True,'sourceRun':41700314952,'checks':{k:vot['checks'][k] for k in keys},'limitations':vot['limitations']},ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copyfile(original/'gecko5-extensions/extensions.json',out/'extensions.json');shutil.copyfile(original/'gecko5-optional/youtube-vot-diagnostic.json',out/'youtube-vot-diagnostic.json')
print('Verified unchanged executable/model/extension components:',len(before))
