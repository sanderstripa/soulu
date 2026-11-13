# Sona Gecko Preview 5 Update 1

Windows x64 portable update to Preview 5, branch gecko-preview. This is a targeted maintenance update, not a claim that every reported issue has been eliminated.

## Changes

- Home waits for initial settings, typography and logo readiness before revealing its content. Weather still updates asynchronously.
- Existing Home tabs receive favorites changes without reloading. Favorites follow their configured order; URL captions are removed. Home settings include a favorites-button switch.
- Favorites can be reordered by dragging. Bookmark rows offer native Gecko drag data for dropping onto Home favorites. Cross-frame dragging requires device-level manual confirmation; automated state checks alone do not establish native drag reliability.
- Bookmark clicks preserve the sidebar. Sidebar entry/exit have short, cancellation-safe animations.
- Settings reopen at the main twelve-section menu without resetting values.
- The single-tab address row uses the full single-row height, including restored and maximized windows.
- Extension actions are grouped under one optional button between tab overview and Windows minimize. Native Firefox extension behavior is retained.
- Content fallback surfaces use the active Sona theme, and the theme is applied earlier during startup.
- Whisper uses a bounded encoder context for short queries. Actual offline recognition measured RU 2.69s and EN 5.20s, versus approximately 14s in Preview 5. These are CI fixture timings, not physical microphone latency guarantees.

## Unresolved and verification limits

- Mica remains a Windows desktop material. The requested live page continuation with a blurred gradient behind the browser toolbar is not implemented. A CSS filter in the separate UI document cannot sample another remote browser surface. No continuous screenshot loop or second browser has been introduced.
- Complete removal of Windows/DWM resize trails across real GPU drivers and displays is not confirmed. Matching fallback colors reduces contrast but is not proof of eliminating trails.
- Instant cold startup and elimination of every intermediate native window frame are not guaranteed. Home readiness gating is narrower than a full native startup fix.
- Physical microphone startup, permission dialogs and acoustic quality require manual testing. RU/EN prerecorded inference was actually executed.
- General subjective smoothness, closing overview animations and cross-frame native drag/drop need manual review; do not infer them from DOM state tests.
- Preview 5 limitations still apply, including unconfirmed YouTube voice-over behind YouTube's bot challenge and no automatic update installation.

## Retained components

Firefox Gecko, sandbox/Fission, Firefox/NSS passwords, Places, profiles, permissions, downloads, VPN Xray/Sudoku, Rust AdBlock and the signed optional VOT extension are retained. Existing executable/model/extension bytes remain unchanged except for the separately built and tested local speech helper. No Windows system proxy or installed Firefox configuration is changed.

The release is gated on the targeted Windows report and a launch from the extracted ZIP. Reports are attached to the release.
