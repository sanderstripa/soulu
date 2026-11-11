"""Manifest every shipped file; no unverified extra payload entries are permitted."""
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]); manifest=root/'soulu-engine-manifest.json'
manifest.unlink(missing_ok=True)
files=[{'path':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*')) if p.is_file()]
manifest.write_text(json.dumps({'name':'Soulu Preview 1.160.26','files':files},indent=2),encoding='utf-8')
