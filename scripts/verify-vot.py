import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'ui'/'third_party'/'vot'
pin=json.loads((root/'UPSTREAM.json').read_text(encoding='utf-8'))
payload=(root/'vot.user.js').read_bytes()
git=hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()
assert git==pin['upstreamGitBlob'],'Pinned VOT distribution differs from its upstream Git blob'
assert pin['tag']=='1.12.3' and pin['commit']=='f32ee1670f6b7b26e5cdeffc0010a03842c960b2'
assert 'MIT License' in (root/'LICENSE').read_text(encoding='utf-8')
print('PASS: pinned VOT',pin['tag'],pin['commit'],git)
