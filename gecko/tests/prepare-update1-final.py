"""Keep accepted binaries/core; apply only the final keyed-button resource fix."""
import hashlib,json,os,pathlib,subprocess,zipfile
root=pathlib.Path(__file__).resolve().parents[2];base='23a4542a84f2c53772c7a3400e89a354c4138da3'
changed=set(subprocess.check_output(['git','diff','--name-only',base,'HEAD'],text=True).splitlines())
allowed={'gecko/chrome/extensions-ui.js','gecko/tests/extensions.py','gecko/tests/extensions-signed.py','gecko/tests/prepare-update1-final.py','gecko/docs/UPDATE1-RESULTS.md','.github/workflows/build-gecko4-update1.yml','.github/workflows/finalize-gecko4-update1.yml'}
assert changed<=allowed,changed-allowed
archive=root/'candidate/Sona-Gecko-Preview-4-Update-1-win64.zip';expected=(root/'candidate/SHA256SUMS.txt').read_text(encoding='utf-8-sig').split()[0];assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
out=root/'gecko-out'
with zipfile.ZipFile(archive) as z:z.extractall(out)
metadata=json.loads((out/'BUILD.json').read_text(encoding='utf-8'));assert metadata['sona_source']==base
for name,count in [('preview4.json',68),('final4.json',14),('extensions.json',35)]:
 r=json.loads((out/name).read_text(encoding='utf-8'));assert r['passed'] and len(r['checks'])>=count and all(c['passed'] for c in r['checks'].values())
assert json.loads((out/'visual-comparison.json').read_text(encoding='utf-8'))['passed']
def binaries():return {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.suffix.lower() in ['.dll','.exe']}
before=binaries();content=(root/'gecko/chrome/extensions-ui.js').read_bytes()
for path in [out/'runtime/sona/chrome/extensions-ui.js',out/'runtime/sona/chrome/ui/extension-toolbar.js']:path.write_bytes(content)
assert binaries()==before
metadata.update(sona_source=os.environ['GITHUB_SHA'],base_source=base,base_windows_run=41663449503,frontend_patch_sha256=hashlib.sha256(content).hexdigest(),unchanged_executable_components=len(before))
(out/'BUILD.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
(out/'docs/UPDATE1-RESULTS.md').write_bytes((root/'gecko/docs/UPDATE1-RESULTS.md').read_bytes())
print('Accepted base and unchanged executable components:',len(before))
