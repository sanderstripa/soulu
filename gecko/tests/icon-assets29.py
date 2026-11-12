"""Audit every product icon alias in the assembled runtime against the master."""
from pathlib import Path
import json,sys
root=Path(__file__).resolve().parents[2]
out=Path(sys.argv[1]);ui=out/'engine/soulu/chrome/ui'
manifest=json.loads((root/'ui/branding/manifest.json').read_text())
for name in manifest['aliases']:
 assert (ui/name).read_bytes()==(root/'ui'/name).read_bytes(),name
for size in manifest['png_sizes']:
 name=f'branding/soulu-{size}.png'
 assert (ui/name).read_bytes()==(root/'ui'/name).read_bytes(),name
for path in [*ui.glob('*.ico'),*(out/'engine/chrome/icons/default').glob('*.ico'),*(out/'engine/browser/chrome/icons/default').glob('*.ico')]:
 assert path.read_bytes()==(root/'ui/soulu-icon.ico').read_bytes(),str(path)
print(json.dumps({'passed':True,'aliases':manifest['aliases'],'sizes':manifest['png_sizes']}))
