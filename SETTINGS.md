# Settings 2.0

Settings is a native overlay, separate from tabs. Compact Home expands when entering a section and returns to intrinsic height on Home. The fixed nine sections are General, Interface, Startup and home, Search, Privacy and security, VPN, Reading and translation, Profiles and import, and About Soulu.

General owns language, default browser and downloads. Interface owns theme, matte, toolbar and bookmarks-bar controls. Startup and home owns independent startup/new-tab/home modes and URLs, last-tab behavior, Home widgets, favorites and weather. Privacy owns permissions, ad blocking/exceptions, history/clearing, passwords and site data. Existing VPN, Reader, translation, profile and import actions retain their working backends.

## Immediate persistence

Ordinary controls commit through `settings.save`: toggles/selects/segments on change; text on change/blur; Enter blurs text. Custom page mode and URL commit together. There is no global Apply/Cancel, staged preview dictionary, dirty footer or close confirmation. Close blurs the field and flushes pending saves; profile actions also flush before switching.

`settings.begin` returns a canonical snapshot. `settings.save` returns `{ok,error,persisted}`, including actual groups committed before a later writer failure. The UI restores persisted values and shows errors. Native validation retains existing URL, directory, Reader, Home and VPN constraints. Profile identity is checked, edited keys rebase on live settings, and conflicting concurrent changes are rejected.

## Existing stores and scopes

- Profile browser settings: `Profiles/<id>/soulu-settings.json`.
- Permission/ad-block policy: profile `soulu-site-rules.json`.
- Reader preferences: profile `soulu-reader.json`.
- VPN retains the existing global settings and helper profile stores.
- Password vault, bookmarks, history, imports, translation rules, cookies and cache retain existing backends/scopes.

Legacy migration and templates are preserved. Incognito Settings edits the ordinary active profile, as before; private browsing data retains its existing scope. Saving VPN does not connect or alter Windows system proxy settings.

## Visual system

`ui/settings-icons.js` owns the new monochrome 24×24 vectors with 1.5px stroke, rounded caps/joins and neutral active states. Settings uses bundled Onest 400/500/600 and canonical typography tokens; there are no colored category backplates. Search is a pill aligned with the right Home column. Close has a 42px target and a circular 32px red hover surface. The header divider is removed. Content scrolls independently; narrow layouts collapse the rail and grid. Light, Dark and System remain supported.

Search indexes bilingual labels, descriptions, group names and synonyms. Results open the canonical section and highlight its control. Ctrl+F focuses search; Escape/Ctrl+W closes; Alt+Left returns Home; keyboard focus stays inside the active surface/dialog.

## Verification

Settings acceptance covers real CEF controls, disk writes, invalid input, writer recovery, restart/migration, languages/DPI, profiles and incognito. Native overlay acceptance covers ownership/focus, backdrop blocking, live background page/media, subviews, resize and close/reopen. Motion, typography, storage, Home, toolbar and broader browser suites remain in Windows CI. Preview helpers live outside the repository and are never shipped.

CEF 154.0.33 / Chromium 154.0.8037.94 remain pinned.
