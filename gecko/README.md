# Soulu Gecko Preview 4

Extract the complete ZIP and run `Soulu Gecko Preview 4.exe` (Windows x64).

Preview 4 uses the original Soulu HTML/CSS/SVG/fonts for the adaptive toolbar,
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

See bundled `preview4.json`, the release ZIP smoke report and `visual-evidence` for actual Windows checks. The helper and Rust DLL are rebuilt; pinned Xray/Sudoku cores and their licenses are reused from checksum-verified Preview 3. CI does not certify a physical GPU, physical
multi-monitor DPI, or the quality of the user's external VPN service.

Page translation uses the native local Gecko translator. Models are downloaded
on first use; page text stays on the device. Configured-city weather uses
Open-Meteo. Automatic location requires explicit permission.

Matte transparency uses the Soulu frosted surface and Windows Mica where
available. This is a native compositor material, not CEF page-glass capture.

Known unavailable/limited features: YouTube voice-over translation;
Chrome CRX installation; voice search; CEF-specific background-tab suspension;
 Unsupported controls report their
availability explicitly. Firefox extensions use the native Firefox manager.
The native Gecko permission prompt may differ from the CEF prompt. Desktop
backdrop material depends on the OS compositor. None of these limitations is
proof of a working control; acceptance tests exercise actual effects.

Engine provenance and source commit: `BUILD.json`. Mozilla licenses remain in
the unmodified Firefox runtime (`about:license`). Rust notices are in
`runtime/soulu/adblock/notices`.

Preview 4 uses native SessionStore for restore/duplicate/reorder/session persistence, Places for folders and HTML import/export, NSS LoginManager for GUID-based password editing and CSV import, the Firefox migration wizard, native Downloads for file operations and permission preflight, and native Reader View. Filter files download through Gecko (including its VPN policy), then compile and install atomically in a Rust worker; failures retain the previous engine/cache. Soulu does not run ETP URL classification alongside the same Rust EasyPrivacy lists; native cookie partitioning, Safe Browsing and process isolation remain enabled.

Each profile has its own VPN working directory and dynamically allocated SOCKS port. Firefox's native profile-removal service refuses removal of a locked profile. No system proxy change is needed. Page text translation remains local; voice-over YouTube translation is deferred. Portable default-browser registration and Soulu automatic updates are unavailable. Native reader styling uses compatible Firefox settings; CEF-only image hiding/custom fonts are not promised. Import availability depends on the source browser and operating-system protection; exported CSV files contain plaintext secrets and should be removed after import.
