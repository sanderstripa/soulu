"""Install canonical, checked-in exports; never distort or regenerate old art."""
from pathlib import Path
import shutil, subprocess, sys
root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(root/'scripts/verify-branding.py')],check=True)
source=root/'ui';target=root/'gecko-out/engine/soulu/chrome/ui'
if target.parent.exists():
 target.mkdir(exist_ok=True)
 for path in source.glob('*icon*'):
  if path.is_file() and path.suffix in {'.png','.ico','.svg'}:shutil.copyfile(path,target/path.name)
 shutil.copytree(source/'branding',target/'branding',dirs_exist_ok=True)
 for name in ['soulu-petals.png','soulu-wave.png']:
  dst=target.parent/'branding'/name;dst.parent.mkdir(exist_ok=True)
  shutil.copyfile(source/'soulu-icon.png',dst)
 for folder in ['chrome/icons/default','browser/chrome/icons/default']:
  dst=root/'gecko-out/engine'/folder;dst.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(source/'soulu-icon.ico',dst/'main-window.ico')
