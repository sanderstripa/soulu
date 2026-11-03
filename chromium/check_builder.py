"""Inspect a Windows Chromium builder without downloading source or changing it."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

LOCK = json.loads((Path(__file__).parent / "source-lock.json").read_text())


def inspect(work_root):
    work_root = Path(work_root).resolve()
    existing = work_root
    while not existing.exists():
        existing = existing.parent
    limits = LOCK["windows_toolchain"]
    free = shutil.disk_usage(existing).free
    blockers, notes = [], []
    windows = platform.system() == "Windows"
    report = {"kind": "build-environment-only", "platform": platform.platform(),
              "work_root": str(work_root), "free_disk_bytes": free,
              "logical_cpus": os.cpu_count(), "browser_built": False,
              "runtime_acceptance": "NOT RUN", "blockers": blockers, "notes": notes}
    if not windows:
        blockers.append("Windows x64 host required for this native build configuration")
    if any(c.isspace() for c in str(work_root)) or not str(work_root).isascii():
        blockers.append("Use a short ASCII work-root without spaces, e.g. C:\\soulu-build")
    if free < limits["minimum_free_gb"] * 10**9:
        blockers.append("At least 100 GB free disk space is required before initial checkout")
    elif free < limits["recommended_free_gb"] * 10**9:
        notes.append("300 GB free SSD is recommended; 100 GB is the upstream minimum, not a guarantee")
    report["git"] = shutil.which("git")
    if not report["git"]:
        blockers.append("Git for Windows is missing")
    if windows:
        if platform.machine().lower() not in ("amd64", "x86_64"):
            blockers.append("This configuration requires Windows x64")
        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in
                ("physical", "available", "pagefile", "available_pagefile", "virtual", "available_virtual", "extended")]
        memory = Memory()
        memory.length = ctypes.sizeof(memory)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            blockers.append("Could not inspect physical RAM")
        else:
            report["ram_bytes"] = memory.physical
            if memory.physical < limits["minimum_ram_gb"] * 10**9:
                blockers.append("At least 16 GB RAM is required by this build configuration")
        fs = ctypes.create_unicode_buffer(64)
        if not ctypes.windll.kernel32.GetVolumeInformationW(
                str(work_root.anchor), None, 0, None, None, None, fs, len(fs)):
            blockers.append("Could not inspect build volume filesystem")
        elif fs.value != "NTFS":
            blockers.append("Build volume must be NTFS")
        report["filesystem"] = fs.value
        programs = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        vswhere = programs / "Microsoft Visual Studio/Installer/vswhere.exe"
        if not vswhere.is_file():
            blockers.append("Visual Studio Installer/vswhere is missing")
        else:
            command = [str(vswhere), "-products", "*", "-version", "[18.0,19.0)",
                       "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                       "Microsoft.VisualStudio.Component.VC.ATLMFC", "-format", "json", "-utf8"]
            installs = json.loads(subprocess.check_output(command, text=True, encoding="utf-8-sig"))
            report["visual_studio"] = [i["installationPath"] for i in installs]
            if not installs:
                blockers.append("Visual Studio 2026 C++ x64 tools and MFC/ATL components are required")
        sdk = programs / "Windows Kits/10/Include" / limits["sdk_version"] / "um/Windows.h"
        report["sdk_header"] = str(sdk)
        if not sdk.is_file():
            blockers.append("Windows SDK 10.0.28000.2270 (headers 10.0.28000.0) is missing")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-root", default=str(Path.cwd()))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    result = inspect(args.work_root)
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded)
    return 1 if result["blockers"] and not args.report_only else 0


if __name__ == "__main__":
    sys.exit(main())
