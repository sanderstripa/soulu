"""Overlay only audited small resource fixes on the full accepted candidate."""
import hashlib,json,os,pathlib,subprocess,zipfile
root=pathlib.Path(__file__).resolve().parents[2];source='c09a46573870d3eea0adf15015b1d15e6dc9abe2'
changed=set(subprocess.check_output(['git','diff','--name-only',source,'HEAD'],text=True).splitlines())
allowed={'.github/workflows/build-gecko4.yml','.github/workflows/finalize-gecko4.yml','gecko/chrome/browser.js','gecko/chrome/adblock.sys.mjs','gecko/chrome/integration-ui.js','gecko/chrome/settings-support.js','gecko/tests/preview4.py','gecko/tests/final4.py','gecko/tests/prepare-final4.py','gecko/docs/PREVIEW4-RESULTS.md'}
assert changed<=allowed,changed-allowed
archive=root/'candidate/Soulu-Gecko-Preview-4-win64.zip';expected=(root/'candidate/SHA256SUMS.txt').read_text(encoding='utf-8-sig').split()[0];assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
out=root/'gecko-out'
with zipfile.ZipFile(archive) as z:z.extractall(out)
metadata=json.loads((out/'BUILD.json').read_text(encoding='utf-8'));assert metadata['soulu_source']==source
report=json.loads((out/'preview4.json').read_text(encoding='utf-8'));assert report['passed'] and len(report['checks'])>=66 and all(c['passed'] for c in report['checks'].values())
assert json.loads((root/'gecko4-baseline/zip-smoke.json').read_text(encoding='utf-8'))['passed']
assert json.loads((out/'visual-comparison.json').read_text(encoding='utf-8'))['passed']
def binaries():return {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.suffix.lower() in ['.exe','.dll']}
before=binaries();patches={}
for name in ['browser.js','adblock.sys.mjs','settings-support.js','integration-ui.js']:
 content=(root/'gecko/chrome'/name).read_bytes()
 for path in [out/'runtime/soulu/chrome'/name,*([out/'runtime/soulu/chrome/ui'/name] if name in ['settings-support.js','integration-ui.js'] else [])]:path.write_bytes(content);patches[str(path.relative_to(out))]=hashlib.sha256(content).hexdigest()
assert binaries()==before,'Executable components changed'
metadata.update(soulu_source=os.environ['GITHUB_SHA'],base_source=source,base_windows_run=41653080983,resource_overlay=patches,unchanged_executable_components=len(before),verification='Full 66-check Windows candidate + targeted final resource checks + final CEF comparison + final extracted ZIP launch. See release reports for YouTube/physical GPU limitations.')
(out/'BUILD.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
(out/'docs/PREVIEW4-RESULTS.md').write_bytes((root/'gecko/docs/PREVIEW4-RESULTS.md').read_bytes())
print('Verified candidate and unchanged executable components:',len(before))
