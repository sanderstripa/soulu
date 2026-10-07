"""Obtain the pinned MIT-licensed multilingual model for the offline Home button."""
import hashlib
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = '5359861c739e955e79d9a303bcbc70fb988958b1'
SHA256 = 'be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21'
URL = f'https://huggingface.co/ggerganov/whisper.cpp/resolve/{REVISION}/ggml-tiny.bin'
MODEL = ROOT / 'ui/speech/ggml-tiny.bin'

def verified(path):
    return path.is_file() and path.stat().st_size == 77691713 and hashlib.sha256(path.read_bytes()).hexdigest() == SHA256

if not verified(MODEL):
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    pending = MODEL.with_suffix('.download')
    try:
        with urllib.request.urlopen(URL, timeout=120) as source, pending.open('wb') as output:
            size = 0
            while block := source.read(1024 * 1024):
                size += len(block)
                if size > 77691713:
                    raise RuntimeError('Speech model exceeds approved size')
                output.write(block)
        if not verified(pending):
            raise RuntimeError('Speech model integrity verification failed')
        pending.replace(MODEL)
    finally:
        pending.unlink(missing_ok=True)
print('PASS: integrity-pinned multilingual speech model; audio inference is local')
