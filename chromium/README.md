# Soulu Chromium Preview 1 — port preparation

**Status: native source port started; not compiled or accepted for release.**
The source overlay embeds the original Soulu shell in Chromium's own Webium
WebUI browser. This directory does not yet contain a working alternative browser. There is no Chromium Preview 1 binary to download.
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

## Implemented in source, awaiting native compilation

* Chromium 156.0.8078.48 and depot_tools pinned to immutable Git commits.
* Original Soulu resources registered in Chromium's trusted WebUI resource build;
  the adaptive panel is selected by the backend. Upstream `ui/` is unchanged.
* Native tab model snapshots and handlers for new/close/select/pin, back/reload,
  HTTP(S) navigation, basic Google search, incognito windows and window controls.
* Chromium's native tab content surfaces remain attached when toolbar state
  updates; the adapter does not capture video or rebuild content per hover.
* `soulu.settings` profile preference stores validated theme/language choices.
* Default local and roaming data paths use `SouluChromium/User Data`.
* Unsupported commands return errors; capabilities explicitly mark missing ports.

These are source changes, **not verified runtime features**. Webium itself is an
upstream experimental UI. Compatibility, native permission/menu anchoring,
fullscreen, animations and smoothness require Windows compilation and testing.
History is handled by Chromium's existing engine but is not integrated with Soulu's
history page. Home, full settings sessions, bookmarks, profile management UI,
VPN, the own ad blocker, translation and extensions toolbar remain unported.
Chromium WebUI Trusted Types enforcement is preserved. Adapting the original
dynamic HTML writes to that enforcement is still required before UI acceptance;
the source preparation checks do not exercise those DOM writes.

## Reproducible remote build

See [BUILDING.md](BUILDING.md) for Windows prerequisites, separate runner setup,
repository variables and exact commands. The workflow in
`.github/workflows/chromium-preview.yml` runs only on `chromium-preview`.

The standard hosted Windows job checks source preparation and transport and
records its actual machine prerequisites. Native compilation is a separate job
which is skipped until an existing capable runner is configured. No paid runner
has been purchased or enabled. No runtime acceptance or release is implied by
passing source checks.

`prepare_source.py` verifies six pinned upstream file digests and all replacement
anchors before writing the source overlay. A manifest records generated hashes
and the original reference asset hashes. Reruns permit only unchanged previously
generated files and refuse to overwrite user modifications. `prepare_ui.py` from
the earlier preparation remains available for byte-for-byte reference export.

## Non-negotiable implementation constraints

* Native Chromium `chrome` source target: no CEF, Electron or WebView2 runtime.
* Keep sandbox, site isolation, multiprocess content and hardware acceleration.
* Use the Chromium compositor; do not copy video frames through the UI process.
* Privileged bridge available only to explicitly registered local trusted WebUI;
  never to ordinary tabs, frames or arbitrary navigations.
* Source-enforced default product root: `%LOCALAPPDATA%\SouluChromium\User Data`, distinct from
  Soulu CEF, Chromium and Google Chrome. Custom command-line data roots remain subject to Chromium's normal behavior.
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
