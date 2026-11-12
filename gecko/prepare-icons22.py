"""Install canonical, checked-in exports; never distort or regenerate old art."""
from pathlib import Path
import shutil, subprocess, sys
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(root/'scripts/verify-branding.py')],check=True)
source=root/'ui';target=root/'gecko-out/engine/soulu/chrome/ui'
if target.parent.exists():
 target.mkdir(exist_ok=True)
 for path in source.iterdir():
  if path.is_file() and path.name in __import__('json').loads((source/'branding/manifest.json').read_text())['aliases'] + ['browser-icon.svg']:shutil.copyfile(path,target/path.name)
 shutil.copytree(source/'branding',target/'branding',dirs_exist_ok=True)
 for name in ['soulu-petals.png','soulu-wave.png']:
  dst=target.parent/'branding'/name;dst.parent.mkdir(exist_ok=True)
  shutil.copyfile(source/'soulu-icon.png',dst)
 for folder in ['chrome/icons/default','browser/chrome/icons/default']:
  dst=root/'gecko-out/engine'/folder;dst.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(source/'soulu-icon.ico',dst/'main-window.ico')
 # Replace historical top-level ICO aliases carried by the base installer too.
 for path in target.glob('*.ico'):shutil.copyfile(source/'soulu-icon.ico',path)
 from PIL import Image
 for folder in ['chrome/icons/default','browser/chrome/icons/default']:
  for path in (root/'gecko-out/engine'/folder).glob('*.ico'):
   shutil.copyfile(source/'soulu-icon.ico',path)
 # Windows Start tile artwork is separate from PE/shortcut icon resources.
 for path in (root/'gecko-out/engine/browser/VisualElements').glob('*.png'):
  old=Image.open(path);art=Image.open(source/'soulu-icon.png').convert('RGBA')
  art.thumbnail(old.size,Image.Resampling.HAMMING)
  canvas=Image.new('RGBA',old.size)
  canvas.alpha_composite(art,((old.width-art.width)//2,(old.height-art.height)//2))
  canvas.save(path)
