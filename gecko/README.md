# Soulu Gecko Preview 2

Extract the complete ZIP and run `Soulu Gecko Preview 2.exe` (Windows x64).

Preview 2 uses the original Soulu HTML/CSS/SVG/fonts for the adaptive toolbar,
Home page, bookmark management, history and all 12 settings sections. Gecko
renders normal websites in its native isolated processes; no website receives
the application bridge. The bridge is restricted to four exact installed file
URLs and validates the sending principal in the parent process.

Data is stored separately in `%LOCALAPPDATA%\SouluGecko\Profiles`.
Firefox Places stores history and bookmarks. Native NSS protects passwords and
saved VPN keys; the JSON settings file does not contain plaintext VPN links.
Existing Soulu CEF and installed Firefox profiles are not modified.

VPN: add and select a VLESS/Sudoku connection in Settings → VPN. Use the original
Soulu toolbar button to connect. Only Gecko's proxy changes. SOCKS DNS is remote,
direct fallback is disabled, and WebRTC is disabled while connected. A failed
connection remains blocked until the user disconnects.

The original Soulu CEF Rust adblock engine (adblock-rust 0.13.3) is built as a DLL
with the same EasyList/EasyPrivacy/RuAdList baseline. It cancels real requests in
Gecko's parent network observer and applies cosmetic selectors through an
isolated actor. Per-site exceptions use Soulu's original site menu.

See bundled `acceptance.json` and `visual-comparison.json` for Windows evidence.
Visual evidence compares the actual released CEF binary at the same client
size, rather than a mock image. CI does not certify a physical GPU, physical
multi-monitor DPI, or the quality of the user's external VPN service.

Known unavailable/limited features: page/YouTube translation; CEF-style reader;
Chrome CRX installation; voice search; CEF-specific background-tab suspension;
automatic Rust subscription refresh. Those optional controls must report their
availability explicitly. Firefox extensions use the native Firefox manager.
The native Gecko permission prompt may differ from the CEF prompt. Desktop
backdrop material depends on the OS compositor. None of these limitations is
proof of a working control; acceptance tests exercise actual effects.

Engine provenance and source commit: `BUILD.json`. Mozilla licenses remain in
the unmodified Firefox runtime (`about:license`). Rust notices are in
`runtime/soulu/adblock/notices`.
