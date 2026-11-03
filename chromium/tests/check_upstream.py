"""Validate transforms against pinned upstream files without a full checkout."""
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from prepare_source import prepare


def fetch(path):
    lock = json.loads((HERE / "source-lock.json").read_text())
    revision = lock["chromium"]["revision"]
    url = f"https://chromium.googlesource.com/chromium/src/+/{revision}/{path}?format=TEXT"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return path, base64.b64decode(response.read(), validate=True)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def main():
    hashes = json.loads((HERE / "upstream-files.json").read_text())
    with tempfile.TemporaryDirectory() as directory:
        src = Path(directory)
        with ThreadPoolExecutor(max_workers=6) as executor:
            for name, data in executor.map(fetch, hashes):
                if hashlib.sha256(data).hexdigest() != hashes[name]:
                    raise ValueError(f"Pinned upstream digest mismatch: {name}")
                path = src / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        prepare(src, check=True)
        report = prepare(src)
        report["upstream_hashes_verified"] = True
        Path("chromium-source-check.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"Prepared {len(report['files'])} files against exact upstream bytes; native compile/runtime NOT RUN.")


if __name__ == "__main__":
    main()
