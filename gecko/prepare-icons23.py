"""Generate the complete product icon family from one transparent master."""
from pathlib import Path
from PIL import Image
import hashlib,json
root=Path(__file__).resolve().parents[1];master=root/'gecko/chrome/branding/soulu-petals.png'
original=Image.open(master).convert('RGBA')
art=original.crop(original.getbbox())
scale=1014/max(art.size)
art=art.resize((round(art.width*scale),round(art.height*scale)),Image.Resampling.LANCZOS)
image=Image.new('RGBA',(1024,1024))
image.alpha_composite(art,((1024-art.width)//2,(1024-art.height)//2))
for folder in [root/'ui',root/'gecko-out/engine/soulu/chrome/ui']:
    for name in ['browser-icon.png','soulu-icon.png','soulu-icon-new.png']:
        image.resize((1024,1024),Image.Resampling.LANCZOS).save(folder/name)
    for name in ['browser-icon.ico','browser-app-icon.ico','soulu-icon.ico','soulu-app-icon.ico','soulu-installer-icon.ico','soulu-shortcut-icon.ico']:
        image.save(folder/name,format='ICO',sizes=[(n,n) for n in [16,20,24,32,40,48,64,128,256]])
    brand=folder/'branding';brand.mkdir(exist_ok=True);hashes={}
    for n in [16,20,24,32,40,48,64,128,256,512,1024]:
        p=brand/f'soulu-{n}.png';image.resize((n,n),Image.Resampling.LANCZOS).save(p);hashes[str(n)]=hashlib.sha256(p.read_bytes()).hexdigest()
    (brand/'manifest.json').write_text(json.dumps({'revision':20261110,'source':'gecko/chrome/branding/soulu-petals.png','source_sha256':hashlib.sha256(master.read_bytes()).hexdigest(),'png_sha256':hashes},indent=2))
for folder in ['chrome/icons/default','browser/chrome/icons/default']:
    dst=root/'gecko-out/engine'/folder;dst.mkdir(parents=True,exist_ok=True)
    image.save(dst/'main-window.ico',format='ICO',sizes=[(n,n) for n in [16,32,48,64,128,256]])
