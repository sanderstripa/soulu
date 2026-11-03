# Soulu Chromium Preview 1 — port preparation

**Status: not implemented, not built, not accepted for release.**
This directory is preparation for a Chromium source port. It does not contain
a working alternative browser. There is no Chromium Preview 1 binary to download.
Neither the existing CEF package nor the Gecko package qualifies as this build.

## Inspected baseline

CEF reference: `f3a4ae3fc1f15487c95811de8010524ab95b311b` (main,
Soulu Beta 1.0.76). On 2026-11-03, a fresh fetch and
`git ls-remote --heads --tags origin '*[Cc]hromium*'` found no existing
Chromium preview branch or tag. The experimental alternative in the repository
is `gecko-preview`; it is not a Chromium implementation.

## Reuse and required integration

| Requirement | Existing source | Chromium work still required |
| --- | --- | --- |
| Exact adaptive toolbar, animations, themes | `ui/index.html`, `adaptive-toolbar.*`, `motion.*`, `theme.css`, `geometry.*`, `fonts/` | Embed the original UI as a trusted WebUI surface in the browser Views hierarchy; expose only adaptive layout |
| Home | `ui/home.*`, `home-i18n.js` | Trusted new-tab WebUI and native home handlers |
| Settings, all existing sections | `ui/settings*` | Replace CEF settings sessions with profile-scoped Chromium handlers; preserve the current structure |
| Tabs, address, loading, media activity | `ui/cef-bridge.js`, `ui/renderer.js`, `cef/soulu/browser_window.*` | Bridge to Chromium tab model and WebContents observers |
| VPN Xray/Sudoku | `vpn/helper/`, `cef/soulu/vpn_helper.*`, `vpn_routing.h` | Adapt helper IPC, process lifetime and profile-specific proxy settings; test real tunnels |
| Own ad blocker | `cef/soulu/adblock/`, `adblock_bridge.*`, `adblock_cosmetic.h` | Integrate Rust engine with request interception and cosmetic injection, preserving network security |
| History/bookmarks | `history_store.*`, `profile_data.*`, `ui/history.*` | Map original contracts to Chromium history/bookmark services |
| Profiles/incognito | `profile_data.*`, `main.cc` | Chromium ProfileManager and off-the-record profiles with isolated product data root |
| Permissions/privacy | `browser_client.*`, `profile_data.*`, `SITE_CONTROLS.md` | Content settings, permission controller and privacy prefs |
| Safe storage | `protected_store.*`, `profile_data.cc`, `DATA_SECURITY.md` | Use Chromium OS crypt services and product-specific storage; do not reuse CEF credential stores |

The CEF shell is not just HTML: `ShellSurface` derives from `CefRenderHandler`,
and `BrowserWindow`, history, VPN wrappers and settings use CEF types. Copying
these files into a standalone Chromium executable does not remove that dependency.
Renaming the CEF executable or launching stock Chromium in app mode does not
implement this port.

## Preparation tools

`python chromium/prepare_ui.py --output <new-directory>` copies the original
UI byte-for-byte and creates SHA-256 provenance. It deliberately does not modify
the design or claim that assets alone implement browser functions. The output
still contains the CEF bridge until a native Chromium replacement is implemented.

`python chromium/preflight.py` checks the local Windows build prerequisites.
This is an environment check, not a browser acceptance test. A successful check
would not mean the port exists.

## Build blocker observed in this session

The available host is Linux, with approximately 58 GiB free disk and no Windows
runtime. The official Windows source-build instructions require Windows 10 or
newer and at least 100 GB free on NTFS, plus the applicable Visual Studio/SDK:
https://chromium.googlesource.com/chromium/src/+/main/docs/windows_build_instructions.md

A suitable Windows source-build and interactive test machine is needed. Its
availability alone does not complete the missing native Chromium integration.
No cloud runner, paid infrastructure or remote Windows desktop was provisioned.

## Non-negotiable implementation constraints

* Native Chromium `chrome` source target: no CEF, Electron or WebView2 runtime.
* Keep sandbox, site isolation, multiprocess content and hardware acceleration.
* Use the Chromium compositor; do not copy video frames through the UI process.
* Privileged bridge available only to explicitly registered local trusted WebUI;
  never to ordinary tabs, frames or arbitrary navigations.
* Proposed product root: `%LOCALAPPDATA%\SouluChromium\User Data`, distinct from
  Soulu CEF, Chromium and Google Chrome. This path is a requirement, not yet code.
* Do not resize WebContents when only toolbar hover, suggestions or popovers change.
* Unsupported actions must report errors rather than simulated success.

## Acceptance status

All requested runtime checks remain **NOT RUN**: equal-size CEF/Chromium screen
comparisons (light/dark and UI states), tabs, address entry, YouTube playback,
Xray/Sudoku tunnels controlled by the UI, actual network/cosmetic ad blocking,
history/bookmarks, independent profiles/incognito, permission requests, settings
persistence and frame smoothness. Translation and extension integration are also
not ported. No runnable ZIP or release should be published until the mandatory
implementation and Windows acceptance checks exist and pass.
