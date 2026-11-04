"""Apply resource changes to the accepted Preview 5 binaries without rebuilding them."""
import difflib,hashlib,json,pathlib,subprocess,shutil
root=pathlib.Path(__file__).resolve().parents[2];out=root/'gecko-out';runtime=out/'runtime/soulu/chrome';base='d245de1bf601a9045df219296ebd36c255f502fc'
def hashes():return {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.suffix.lower() in ['.exe','.dll','.bin','.xpi']}
before=hashes()
changed=subprocess.check_output(['git','diff','--name-only',base,'HEAD'],text=True).splitlines()
for name in changed:
 if name.startswith('ui/'):
  p=root/name;target=runtime/name
  original=subprocess.check_output(['git','show',base+':'+name]).decode();updated=p.read_text(encoding='utf-8');text=target.read_text(encoding='utf-8')
  groups=list(difflib.SequenceMatcher(None,original,updated,autojunk=False).get_grouped_opcodes(24))
  for group in reversed(groups):
   a,b=group[0][1],group[-1][2];c,d=group[0][3],group[-1][4];old=original[a:b];new=updated[c:d]
   assert text.count(old)==1,(name,old)
   text=text.replace(old,new,1)
  target.write_text(text,encoding='utf-8')
for p in (root/'gecko/chrome').rglob('*'):
 if p.is_file():
  target=runtime/p.relative_to(root/'gecko/chrome');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
for source,target in [('extensions-ui.js','extension-toolbar.js'),('bridge.js','gecko-bridge.js'),('frontend.css','gecko-frontend.css'),('integration-ui.js','integration-ui.js'),('settings-support.js','settings-support.js')]:shutil.copyfile(root/'gecko/chrome'/source,runtime/'ui'/target)
shutil.copyfile(root/'gecko/soulu.cfg',out/'runtime/soulu.cfg')
shutil.copyfile(root/'gecko/chrome.manifest',out/'runtime/soulu/chrome.manifest')
assert before==hashes(),'Existing executable components must remain byte-identical'
build=json.loads((out/'BUILD.json').read_text());build['name']='Soulu Gecko Preview 7';build['channel']='gecko-preview';build['platform']='win64';build['resource_source']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();(out/'BUILD.json').write_text(json.dumps(build,indent=2))
