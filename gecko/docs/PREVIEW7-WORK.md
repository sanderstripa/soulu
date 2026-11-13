# Preview 7 implementation checkpoint — not a completed release

All reported items are mandatory. Do not publish a partial release or mark unfinished items as accepted limitations.

Pending evidence:
- Actual editor saves multiple existing Home favorites; stale settings cannot overwrite selection; restart persistence and real Home click while sidebar open.
- Shared weather memory/disk cache hydrates every Home before reveal without repeated geolocation/network; verify real request counts.
- Native page-glass backdrop pixels follow content, gradient and toggle; no Mica wallpaper substitution. Investigate Mozilla bug 1799334 / 2079476; root clipping workaround remains an experiment pending Windows pixels.
- Single-tab animated address centers without an intermediate jump in restored/maximized/fullscreen modes; record actual coordinates throughout.
- Cold launch, functional first paint, no white/pink/Firefox frames. Initialization no longer waits for delayed startup, and Mica is disabled before window creation; verify startup frames/timing and regressions.
- Native Windows live resize captures: no black exposed bands, theme-aligned native fallback, video/CPU/GPU behavior remains accelerated.
- Extension puzzle comes from existing settings asset; switch is under toolbar elements.
- Extension settings switches enable/disable items, no obsolete pinning UI; Bitwarden removable in the accepted native add-on manager.
- VOT must actually migrate into native builtin location, preserve settings/consent and resist user-extension uninstall; do not fake this by filtering names. AMO signature validated before installation. Not yet verified.
- Legacy uBlock removal is conditioned on Rust blocker readiness; Bitwarden one-time enable only for existing installation. Confirm migrations on fixture profile.
- Preferences entry routes into Sona, including from native add-ons manager; no Firefox preferences frame flashes. Inspect native branding and all user-facing strings, retaining original licenses.
- Update comparator and Windows executable/BUILD/UI identities are consistently Preview 7; installed Preview 7 must not offer itself.
- Preserve the accepted accelerated Whisper helper and all unaffected components; no full suite after every small fix.
- Windows ZIP extraction launch and publish only after all mandatory scenarios pass.

Branch: gecko-preview. main must remain untouched.
