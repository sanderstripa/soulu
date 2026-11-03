"""Export unchanged reference UI assets; this does not build a browser."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def export(output: Path) -> dict:
    root = Path(__file__).resolve().parents[1]
    source = root / "ui"
    output = output.resolve()
    if output == root or root in output.parents:
        raise ValueError("Output must be outside the source checkout")
    if output.exists():
        raise ValueError("Output must be a new directory")
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("UI symlinks are not supported")
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    # Record working-tree modifications: a commit hash alone is not provenance.
    dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--", "ui"], cwd=root, text=True
    ).strip())
    hashes = {
        path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    output.mkdir(parents=True)
    shutil.copytree(source, output / "ui")
    for relative, expected in hashes.items():
        actual = hashlib.sha256((output / "ui" / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Source changed while exporting: {relative}")
    manifest = {
        "kind": "reference-ui-assets-only",
        "browser_built": False,
        "native_chromium_bridge_implemented": False,
        "source_commit": sha,
        "ui_worktree_modified": dirty,
        "files": hashes,
    }
    (output / "UI-PROVENANCE.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = export(args.output)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"UI export failed: {error}\n")
    print(f"Verified {len(result['files'])} unchanged UI assets; no browser built.")
