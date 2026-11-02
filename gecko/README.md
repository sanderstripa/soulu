# Soulu Gecko Preview 1

Experimental Windows x64 portable distribution. Run `Soulu Gecko Preview 1.exe`.

Engine: unmodified Mozilla Firefox/Gecko. Mozilla licensing and about:license remain
in the runtime. Soulu application chrome is loaded from local, privileged resources;
websites never receive the Soulu bridge. Sandbox, Fission, certificate validation,
Safe Browsing and signed extension checks remain enabled.

The adaptive toolbar uses Firefox native tabs, address completion, permission
prompts and compositing with Soulu's Onest fonts, colors and geometry. Settings
reuse Soulu's current HTML/CSS. Right-click the toolbar to open settings.
Ctrl+H: history. Ctrl+Shift+O: bookmarks. Ctrl+Shift+P: private browsing.

Separate data: `%LOCALAPPDATA%\SouluGecko\Profiles`. Existing Soulu/Firefox profiles
are not imported or modified. Profiles are created/opened in Settings → Profiles.

VPN: add a VLESS or Sudoku connection in Settings → VPN. Select it, then use
the toolbar VPN button. The existing Soulu native helper and checksum-pinned
Xray/Sudoku cores are bundled. Only this runtime's network preferences change.
SOCKS DNS is remote; direct fallback and WebRTC are disabled while VPN is on.
A failed connection keeps proxy routing blocked until explicit Disconnect.

Ad blocking: signed full uBlock Origin plus Firefox tracking protection. Firefox's
native uBlock popup controls per-site ad exceptions. Its signed XPI is bundled and installed locally on first launch. Filter-list
updates use the network. The native extension popup provides per-site controls.

Preview limitations: this is a customized official Firefox distribution rather
than a source-built Firefox fork. Native permission prompts, history/bookmark and
password managers keep Firefox UI. Advanced CEF-only controls are omitted; the existing section structure remains.
Native Gecko managers back history, bookmark, password and site-data actions. Translation and Chrome extensions
are not included. Use Firefox extensions from addons.mozilla.org. Windows runtime
acceptance and VPN connection checks are recorded separately in acceptance.json;
packaging alone does not prove those checks passed.

Build: `python gecko/build.py --platform win64`, then compile the Windows Go
launcher and existing VPN helper, provision cores via
`scripts/prepare-vpn-components.ps1`, and package the complete directory.
