# Soulu 1.0.72

- Stable VPN toolbar mark: no scaling/pulsing during connect or disconnect.
- Restore normal window position, size and maximized state; keep windows on an available monitor. Hide the composed host before browser children close to avoid the gray frame flash.
- Home action in both toolbars; new-tab action immediately beside the address. Show only the website host until the address field receives focus, then reveal the complete URL.
- Reuse unchanged tab/sidebar/bookmark nodes and batch shell state rendering per animation frame. Home no longer recreates favorite icons or reloads the provider image on every state refresh, and its tab has no permanent page-loading indicator.
- Compact bookmark manager with explicit close action, smaller text, favicon recovery, folders, search and editing. Learned favicons are saved to matching bookmarks; changing a bookmark URL clears its obsolete icon. Home favorites can be edited with a right click.
- A saved-login selection fills username and password together, from either login field. Suggestions are offered on a field click; same-origin, profile, private-mode, form and navigation checks still apply.
- One section heading in Settings; faster native opening animation. Tab overview has opening/closing motion and an explicit close action, with reduced-motion support.
- Downloads panel × returns to browsing without closing tabs or cancelling downloads. History deletion actions have at least 40×40 pixel hit targets.
- Tab audio/video playback indicators and one-click native audio mute. Camera/microphone indicators come from CEF's actual media-access lifecycle, not stored permissions. The playback detector covers HTML audio/video and sampled Web Audio output, including subframes. Digital silence inside an HTML media track is not measured.
- New background tabs defer HTML media playback until first activation. Standard Chromium user-activation autoplay policy provides an additional guard. Already visited tabs may continue playing in the background.
- Verified official core pins: Xray v26.10.31 and Sudoku v0.5.2-1, with archive SHA-256 checks. New upstream releases disable MPTCP; the helper also applies the upstream-recommended runtime guard to older installed cores.
- Configuration checks cover VLESS encryption, XHTTP extras/download settings, all Sudoku HTTPMask/multiplex link modes, directional ASCII, AEAD, packed downlink and table rotation. Real bundled-core client/server SOCKS round trips cover Xray TCP/WebSocket/XHTTP/gRPC and Sudoku raw/WebSocket/stream/poll.

Validation evidence is attached to the Actions run. Physical audio/GPU/DPI, authenticated third-party account sessions, and a user's configured remote VPN servers are not claimed as manually verified.
