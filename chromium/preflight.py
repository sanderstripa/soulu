"""Report local prerequisites. Never reports browser acceptance."""
import json
import os
from pathlib import Path
import platform
import shutil
import sys


def inspect() -> dict:
    free = shutil.disk_usage(Path.cwd()).free
    windows = platform.system() == "Windows"
    tools = {name: shutil.which(name) for name in ("git", "gclient", "gn", "autoninja")}
    blockers = []
    if not windows:
        blockers.append("Native Windows build/test host unavailable")
    if free < 100_000_000_000:
        blockers.append("Less than the documented minimum 100 GB free disk space")
    for name, path in tools.items():
        if not path:
            blockers.append(f"Missing depot/build tool: {name}")
    # Toolchain and filesystem cannot be inferred from a host platform name.
    blockers.append("Visual Studio, SDK and NTFS availability need separate verification")
    return {
        "kind": "environment-preflight-only",
        "platform": platform.platform(),
        "free_disk_bytes": free,
        "logical_cpus": os.cpu_count(),
        "tools": tools,
        "blockers": blockers,
        "browser_built": False,
        "runtime_acceptance": "NOT RUN",
    }


if __name__ == "__main__":
    report = inspect()
    print(json.dumps(report, indent=2))
    sys.exit(1 if report["blockers"] else 0)
