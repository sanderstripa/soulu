"""Export a rendered SVG master to every shipped Sona icon alias.

Render ui/branding/sona-master.svg with a standards-compliant SVG renderer at
4096px or above, then run: python scripts/export-branding.py rendered-master.png
Requires Pillow. The source alpha is preserved; resizing uses premultiplied
alpha to prevent light/dark fringes. Never reuse the previous logo.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
PNG_ALIASES = ('sona-icon.png', 'sona-icon-new.png', 'browser-icon.png')
ICO_ALIASES = ('sona-icon.ico', 'sona-app-icon.ico', 'sona-installer-icon.ico',
               'sona-shortcut-icon.ico', 'browser-icon.ico', 'browser-app-icon.ico', 'sona-app-1.160.24.ico', 'sona-app-1.160.29.ico', 'sona-app-1.160.31.ico')

def export(source):
    image = Image.open(source).convert('RGBA')
    box = image.getchannel('A').getbbox()
    if not box:
        raise ValueError('Master has no visible symbol')
    image = image.crop(box)
    # Full-size circular silhouette, including taskbar frames; no inset padding.
    def frame(size):
        margin = 0
        available = size - 2 * margin
        ratio = available / max(image.size)
        dims = tuple(max(1, round(v * ratio)) for v in image.size)
        # Positive Hamming kernel avoids Lanczos overshoot (white/cyan ringing
        # at opaque edges), particularly noticeable in 16px shell icons.
        symbol = image.convert('RGBa').resize(dims, Image.Resampling.HAMMING).convert('RGBA')
        canvas = Image.new('RGBA', (size, size))
        canvas.alpha_composite(symbol, ((size - dims[0]) // 2, (size - dims[1]) // 2))
        return canvas
    destination = ROOT / 'ui' / 'branding'
    destination.mkdir(exist_ok=True)
    for size in (*SIZES, 512, 1024):
        frame(size).save(destination / f'sona-{size}.png')
    master = frame(1024)
    for alias in PNG_ALIASES:
        master.save(ROOT / 'ui' / alias)
    # Build explicit PNG-backed ICO entries so 20/24/40 are not dropped by a
    # library's default icon-size selection. Windows Vista+ supports these.
    chunks = [(size, (destination / f'sona-{size}.png').read_bytes()) for size in SIZES]
    offset = 6 + 16 * len(chunks)
    entries = []
    for size, data in chunks:
        entries.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    ico = struct.pack('<HHH', 0, 1, len(chunks)) + b''.join(entries) + b''.join(data for _, data in chunks)
    for alias in ICO_ALIASES:
        (ROOT / 'ui' / alias).write_bytes(ico)
    manifest = {'revision': 20261113, 'source': 'ui/branding/sona-master.svg',
                'source_sha256': hashlib.sha256((ROOT / 'ui/branding/sona-master.svg').read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
                'png_sha256': {str(size): hashlib.sha256((destination / f'sona-{size}.png').read_bytes()).hexdigest() for size in (*SIZES, 512, 1024)},
                'sizes': list(SIZES), 'png_sizes': [*SIZES, 512, 1024],
                'margin': '0px; full optical diameter at every resolution',
                'ico_sha256': hashlib.sha256(ico).hexdigest(),
                'aliases': [*PNG_ALIASES, *ICO_ALIASES]}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest))

if __name__ == '__main__':
    export(sys.argv[1])
