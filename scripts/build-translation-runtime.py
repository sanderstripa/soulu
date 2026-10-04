from pathlib import Path
import json,base64,hashlib,tarfile,io,urllib.request
ROOT=Path(__file__).resolve().parents[1]
PACKAGES=[('bergamot','https://registry.npmjs.org/@browsermt/bergamot-translator/-/bergamot-translator-0.4.9.tgz','sha512-bNuuCwM/JnsIYQCKXcYKFT4Qc5vLMoB8Nbvz8ReIgs7xzebK8Sa+R8iEK8mLvNBe/WaZ6zrPaUQilLsRT/ea8Q=='),('tinyld','https://registry.npmjs.org/tinyld/-/tinyld-1.3.4.tgz','sha512-u26CNoaInA4XpDU+8s/6Cq8xHc2T5M4fXB3ICfXPokUQoLzmPgSZU02TAkFwFMJCWTjk53gtkS8pETTreZwCqw==')]
def package(url,integrity):
 data=urllib.request.urlopen(url,timeout=120).read()
 assert 'sha512-'+base64.b64encode(hashlib.sha512(data).digest()).decode()==integrity,'Package integrity failure'
 with tarfile.open(fileobj=io.BytesIO(data)) as archive:
  return {m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
b=package(*PACKAGES[0][1:]);t=package(*PACKAGES[1][1:])
worker=b['package/worker/translator-worker.js'].decode();glue=b['package/worker/bergamot-translator-worker.js'].decode();wasm=base64.b64encode(b['package/worker/bergamot-translator-worker.wasm']).decode()
bootstrap='const wasm=Uint8Array.from(atob('+json.dumps(wasm)+'),c=>c.charCodeAt(0));\nself.fetch=async()=>new Response(wasm,{headers:{"Content-Type":"application/wasm"}});\nself.importScripts=()=>{(0,eval)('+json.dumps(glue)+');};\n'+worker
main=b['package/translator.js'].decode().replace('export class ','class ')
main=main.replace("new Worker(new URL('./worker/translator-worker.js', import.meta.url))",'new Worker(workerURL)')
main=main.replace("new URL(","new URL(")
assert 'import.meta' not in main
out=ROOT/'ui/third_party/bergamot-runtime.js'
out.write_text('// Generated from integrity-pinned official @browsermt/bergamot-translator 0.4.9. MPL-2.0.\n(()=>{const workerURL=URL.createObjectURL(new Blob(['+json.dumps(bootstrap)+'],{type:"text/javascript"}));\n'+main+'\nwindow.SouluBergamot={BatchTranslator,TranslatorBacking,CancelledError};})();\n',encoding='utf-8')
language=t['package/dist/tinyld.normal.browser.js'].decode()
start=language.rfind('export {');assert start!=-1
language=language[:start]+'window.SouluLanguage={detect,detectAll};'
(ROOT/'ui/third_party/tinyld.js').write_text('(()=>{'+language+'})();',encoding='utf-8')
(ROOT/'ui/third_party/tinyld.LICENSE').write_bytes(t['package/license'])
manifest=json.loads((ROOT/'ui/translation-models.json').read_text())
(ROOT/'ui/translation-models.js').write_text('window.SouluTranslationModels='+json.dumps(manifest)+';\n',encoding='utf-8')
print('Built integrity-pinned translation runtime:',out.stat().st_size)
