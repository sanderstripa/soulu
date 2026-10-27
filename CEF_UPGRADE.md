# Stable CEF update — Beta 1.0.62 candidate

Discovery: 2026-10-27. Source baseline: c21523f24d6010e0523954c29cf93e5597adccc5.

Canonical index: https://cef-builds.spotifycdn.com/index.json (Windows x64, stable).
Selected highest Chromium stable version, then latest CEF patch: 156.0.14+g4fa4ab5+chromium-156.0.8078.48.
The standard archive was published 2026-10-24; SHA-1: 7a1049f0facf3b6ce9efc4d683cf1bac72691ba6.
The minimal archive used for header inspection was independently downloaded and its SHA-1 verified:
72dc1dd1636acc2391609fa6f410aa09f09168d4.

Compared with the 154.0.33 distribution, public handler interfaces retain their signatures.
CefPreferenceRegistrar adds version-gated default preference methods. Color/command/resource
identifiers changed; the source is rebuilt against the selected distribution rather than reusing binaries.
CEF_COMMIT_NUMBER is 3659. The sandbox compatibility hash changes to 3b66cadf26145637;
Soulu retains its existing USE_SANDBOX=OFF configuration and does not reuse sandbox libraries.

Build workflow archive pins, compile-time guards, loaded-DLL guards, runtime manifests,
DevTools version assertions and product/installer versions are updated together.
The full Windows build and regression pipeline remains required. Automatic publication is authorized only by the explicit `[release 1.0.62]` source
commit marker on main for the current owner request. Ordinary pushes do not publish.
All automated test, payload-integrity, current-main and usable-public-site gates remain
required. This route records unavailable physical/authenticated checks as unverified
in release notes; it does not claim manual acceptance. Workflow dispatch retains its
existing exact-SHA manual acceptance/deferral path. This document does not assert CI success.

The first Windows run compiled and passed pre-packaging browser regressions, then
caught a stale CEF 154 allowlist in the pinned shared CONNECT installer adapter.
Soulu now specializes that single literal only after verifying the upstream adapter
source SHA-256, restores the checkout in finally, and records the specialized
adapter hash and CEF distribution in installer provenance. The adapter's installation
lifecycle and bundled-payload tests remain enabled. Added negative tests reject the
old engine, missing manifest/files and incorrect component hashes.

## Previous upgrade record

# Stable CEF update — Preview 49 candidate

Discovery date: 2026-10-03. Baseline `origin/main`:
`e440e5f263a71b24e39a8341f11f60f245dac55b` (published Preview 48).

| Item | CEF | Chromium |
| --- | --- | --- |
| Published baseline runtime | `154.0.32+g682c378+chromium-154.0.8037.58` | `154.0.8037.58` |
| Request's reference build | `154.0.33+ga03e714+chromium-154.0.8037.94` | `154.0.8037.94` |
| Latest stable Windows x64 at discovery / selected target | `154.0.33+ga03e714+chromium-154.0.8037.94` | `154.0.8037.94` |

Canonical source: https://cef-builds.spotifycdn.com/index.json, linked by the
official cef-project dependency loader. Selection sorts stable-channel Windows
x64 distributions by Chromium version, rather than taking the first index entry:
older supported branches also receive new builds. No newer stable Chromium
branch was available at discovery. The selected standard distribution's SHA-1
is `66b621e95ccae243621ecb0504803bbdbd2f0777`.

## Dependency and API compatibility

The existing official cef-project snapshot and DownloadCEF mechanism are retained.
The loader uses the selected archive checksum from the canonical index instead
of the CDN `.sha1` sidecar, which returned an empty response during validation.
Its `EXPECTED_HASH` check remains enabled, and the downloaded archive is checked
again before compilation. Dependencies and build outputs must start absent.

All headers, `libcef.lib`, the rebuilt `libcef_dll_wrapper` and the runtime come
from the same standard distribution. Comparing the old and new include trees
found only `cef_version.h` version/commit changes and date-comment changes in
`cef_api_versions.h`; interface signatures and API hashes are unchanged. No
handler, request-context, navigation, subprocess or shutdown adaptation is needed.

CEF's own `CEF_BINARY_FILES` and `CEF_RESOURCE_FILES` lists determine packaging.
For this Windows x64 distribution they contain `libcef.dll`, `chrome_elf.dll`,
`d3dcompiler_47.dll`, `dxcompiler.dll`, `dxil.dll`, `vulkan-1.dll`,
`vk_swiftshader.dll`, its ICD JSON, `v8_context_snapshot.bin`, `icudtl.dat`,
three resource packs and the locales directory. These expand to 233 files.
`verify-cef-engine.ps1` builds a SHA-256 manifest from the verified distribution
and checks every runtime component, then launches Soulu's linked-DLL version
probe. ZIP extraction and installer payload extraction repeat both checks.
Static libraries, debug symbols and the intermediate runtime file list are
excluded from the distributed package.

The native engine guard and version probe use `cef_version_info` and the actual
CEF commit hash returned by `cef_api_hash` from the loaded library, confirming
the full selected CEF build. CDP `Browser.getVersion` reports the full Chromium version; the normal
reduced User-Agent reports `Chrome/154.0.0.0`, not the complete patch number.

No changes were made to GPU flags, certificate validation, web security,
permissions policy or Windows system proxy. The pre-existing `USE_SANDBOX=OFF`
and `settings.no_sandbox=true` are unchanged; this update does not claim to
introduce a sandbox. The CEF sandbox compatibility hash is unchanged.

## Validation and release gates

The Windows workflow performs a fresh x64 Release build, runtime/manifest checks,
native history/data-clear/vault/import/settings/overlay/onboarding/default-link
tests, web-platform/media/download checks, the existing navigation/tab/popup,
storage/profile/incognito/permission/adblock/bookmark/Reader/layout suites, and
real installer interaction, launch, shortcuts and uninstall checks.
Installer packaging is restricted to current main (or its verified release tag).
The installer tests also restore the checksum-verified, published Preview 48
runtime before upgrading, verify the installed runtime manifest, repeat normal
installed launches with persistent-storage checks, reject leftover subprocesses
and remove build artifacts left by older installers.

The platform probe checks the actual CDP version and User-Agent, fetch/XHR,
WebSocket, sessionStorage, WebGL2, canvas-stream video playback/pause, file upload,
native Save As bytes/path, completion callback, repeated-download cancellation
and normal shutdown. It records the actual WebGL renderer. Canvas-stream media
success is not evidence of YouTube playback, audible audio, seek or fullscreen.

Public-site diagnostics cover YouTube, Facebook, Ozon, Google,
sanderstripa.com and apps.sanderstripa.com. A documented Ozon HTTP 403/429 is
recorded as an external service rejection, not a successful content test. The
published Preview 48 CI already recorded the same Ozon challenge page. The
other five sites served HTTP 200 during the first complete upgrade validation.

Publication remains conditional on all required checks. A dispatch with
`publish=true` must supply `manual_checks_sha` equal to the checked source SHA,
after real Google/Ozon session persistence and remaining manual regression
checks have been completed. All six public sites must have served usable content.
Tagging alone cannot bypass these gates. Release source must also equal current
`origin/main`; artifacts are built from that exact SHA.

Outstanding checks must be reported honestly: real authenticated sessions,
YouTube playback/audio/seek/fullscreen, configured VPN/Xray/Sudoku connectivity,
clipboard and drag/drop, native DPI on available displays, visual review of
composed frames and representative performance measurements. Emulated page DPI
and automated fixture sessions do not prove those real-user scenarios.

No Preview 49 should be published while required evidence is missing. Historical
feature documents and release notes describing older CEF pins remain historical;
this document records the current engine update.
