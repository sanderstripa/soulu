"""Bundle the unchanged signed XPI; runtime installation requires user consent."""
import hashlib,json,pathlib,urllib.request,sys
root=pathlib.Path(__file__).resolve().parent.parent;out=root/(sys.argv[1] if len(sys.argv)>1 else 'gecko-out');pin=json.loads((root/'gecko/vot-pin.json').read_text());target=out/'runtime/sona/optional';target.mkdir(parents=True,exist_ok=True)
with urllib.request.urlopen(pin['url'],timeout=90) as r:data=r.read(20*1024*1024)
assert hashlib.sha256(data).hexdigest()==pin['sha256'];(target/'vot-1.12.6.xpi').write_bytes(data)
with urllib.request.urlopen('https://raw.githubusercontent.com/ilyhalight/voice-over-translation/1.12.6/LICENSE',timeout=30) as r:(target/'VOT-LICENSE.txt').write_bytes(r.read())
(target/'VOT-PROVENANCE.json').write_text(json.dumps(pin,indent=2),encoding='utf-8')
