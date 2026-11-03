"""Apply the Soulu source overlay to the exact pinned Chromium revision."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"Expected exactly one upstream anchor: {before[:100]!r}")
    return text.replace(before, after, 1)


def plan(source):
    expected = json.loads((HERE / "upstream-files.json").read_text())
    previous = {}
    marker = source / "SOULU-SOURCE.json"
    if marker.exists():
        previous = json.loads(marker.read_text())["files"]
        for name, sha in previous.items():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Unsafe path in prior overlay manifest")
            if digest((source / name).read_bytes()) != sha:
                raise ValueError(f"Previously prepared source was edited: {name}")
    originals = {}
    for name, sha in expected.items():
        data = (source / name).read_bytes()
        if digest(data) != sha:
            if name not in previous:
                raise ValueError(f"Upstream file differs from lock: {name}")
            revision = json.loads((HERE / "source-lock.json").read_text())["chromium"]["revision"]
            data = subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=source)
            if digest(data) != sha:
                raise ValueError(f"Pristine git source differs from lock: {name}")
        originals[name] = data.decode()
    writes = {}
    assets = {p.relative_to(ROOT / "ui").as_posix(): p.read_bytes()
              for p in sorted((ROOT / "ui").rglob("*")) if p.is_file()}
    for p in (HERE / "ui").iterdir():
        if p.is_file():
            assets[p.name] = p.read_bytes()
    index = assets["index.html"].decode()
    index = replace_once(index, '<head>', '<head>\n  <base href="chrome://webui-browser/soulu/">\n'
        '  <script src="native-bridge.js"></script>\n'
        '  <link rel="stylesheet" href="host.css">')
    index = replace_once(index, '</body>',
        '  <script type="module" src="content-host.js"></script>\n</body>')
    index = replace_once(index, "script-src 'self' 'wasm-unsafe-eval'",
        "script-src 'self' chrome://resources 'wasm-unsafe-eval'")
    assets["index.html"] = index.encode()
    resource_dir = "chrome/browser/resources/webui_browser/"
    for name, data in assets.items():
        if not re.fullmatch(r"[A-Za-z0-9_./-]+", name):
            raise ValueError(f"Unsafe resource path: {name}")
        destination = resource_dir + "soulu/" + name
        if (source / destination).exists() and destination not in previous:
            raise ValueError(f"Refusing to replace untracked resource: {destination}")
        writes[destination] = data
    name = resource_dir + "BUILD.gn"
    text = replace_once(originals[name], '  static_files = [ "webui_browser.html" ]',
        '  static_files = [\n    "webui_browser.html",\n' +
        ''.join(f'    "soulu/{path}",\n' for path in sorted(assets)) + '  ]')
    writes[name] = text.encode()
    native_dir = "chrome/browser/ui/webui_browser/"
    for path in (HERE / "native").glob("soulu_message_handler.*"):
        writes[native_dir + path.name] = path.read_bytes()
    name = native_dir + "BUILD.gn"
    text = replace_once(originals[name], 'source_set("impl") {\n  sources = [',
        'source_set("impl") {\n  sources = [\n    "soulu_message_handler.cc",\n    "soulu_message_handler.h",')
    text = replace_once(text, '    "//components/omnibox/browser:vector_icons",',
        '    "//components/omnibox/browser:vector_icons",\n'
        '    "//components/prefs",\n    "//components/url_formatter",\n    "//net",')
    writes[name] = text.encode()
    name = native_dir + "webui_browser_ui.cc"
    text = replace_once(originals[name], '#include <array>',
        '#include <array>\n#include "chrome/browser/ui/webui_browser/soulu_message_handler.h"')
    text = replace_once(text, '  browser_ = webui_browser_window->browser();',
        '  browser_ = webui_browser_window->browser();\n'
        '  web_ui->AddMessageHandler(std::make_unique<SouluMessageHandler>(browser_));')
    text = replace_once(text, '                              IDR_WEBUI_BROWSER_WEBUI_BROWSER_HTML);',
        '                              IDR_WEBUI_BROWSER_SOULU_INDEX_HTML);')
    writes[name] = text.encode()
    name = "chrome/common/chrome_features.cc"
    writes[name] = replace_once(originals[name],
        'BASE_FEATURE(kWebium, base::FEATURE_DISABLED_BY_DEFAULT);',
        'BASE_FEATURE(kWebium, base::FEATURE_ENABLED_BY_DEFAULT);').encode()
    name = "chrome/common/chrome_paths_win.cc"
    old = '*result = result->Append(install_static::GetChromeInstallSubDirectory());'
    if originals[name].count(old) != 2:
        raise ValueError("Expected both local and roaming product roots")
    writes[name] = originals[name].replace(old, '*result = result->Append(L"SouluChromium");').encode()
    name = "chrome/browser/prefs/browser_prefs.cc"
    text = replace_once(originals[name],
        '  TRACE_EVENT0("browser", "chrome::RegisterProfilePrefs");',
        '  TRACE_EVENT0("browser", "chrome::RegisterProfilePrefs");\n'
        '  registry->RegisterDictionaryPref("soulu.settings");')
    writes[name] = text.encode()
    return writes


def prepare(source, check=False):
    writes = plan(source)  # Verify every anchor before changing any source.
    report = {
        "stage": "source-overlay-only",
        "chromium": json.loads((HERE / "source-lock.json").read_text())["chromium"],
        "files": {name: digest(data) for name, data in sorted(writes.items())},
        "reference_ui": {p.relative_to(ROOT / "ui").as_posix(): digest(p.read_bytes())
                         for p in sorted((ROOT / "ui").rglob("*")) if p.is_file()},
        "native_runtime_tested": False,
    }
    if not check:
        for name, data in writes.items():
            destination = source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (source / "SOULU-SOURCE.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium-src", required=True, type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        report = prepare(args.chromium_src.resolve(), args.check)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Source overlay refused: {error}\n")
    print(f"{'Checked' if args.check else 'Prepared'} {len(report['files'])} source/resource files; runtime NOT TESTED.")
