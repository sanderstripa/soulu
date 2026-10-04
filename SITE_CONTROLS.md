# Site controls and Reader appearance

Starting point: published Beta 1.0.53, main commit
`2f3264b1b52e02f60082e4039c43cbcc3296fed0`.
CEF remains `154.0.33+ga03e714`, Chromium `154.0.8037.94`.

## Interface

`ui/site-reader.js` and `ui/site-reader.css` own the trusted OSR surfaces.
The 408 DIP main panel contains identity, Reader, Find, Zoom, Site Settings and
the live per-site AdBlock switch. The local article fixture measures 378 DIP high,
without scrolling. Site Settings is a separate state, with a back action, domain,
seven compact permission rows, Clear Site Data and Reset Site Settings; its
fixture height is 502 DIP. Small windows can scroll inside a bounded panel.
Panels stay below the full toolbar: y=56 DIP in Main, y=90 DIP in Classic, plus
28 DIP when the bookmarks bar is visible. Favicon failure uses a globe fallback.

Each row opens a value picker: Default, Allow, Ask and Block. Sound preserves
Allow, Mute and Block. Default removes the override and shows the effective global
default in the picker. Escape goes back one level, then closes the panel; outside
click closes it. Controls have a focus loop, visible focus, shared 16 DIP glyphs,
Onest typography and browser light/dark/system tokens. Nested transitions use
180ms restrained motion with a reduced-motion alternative.

## Canonical permissions

The existing `SitePolicy` owns geolocation, camera, microphone, notifications,
sound, popups and downloads. Values remain 0=Allow, 1=Ask/Mute, 2=Block.
Profile defaults and domain overrides remain in `soulu-site-rules.json`.
Private decisions remain in memory. AdBlock retains its existing separate
blocking dictionary and filtering runtime.

`SyncSitePolicy` preserves Chromium origin content settings, including notification
permission and the geolocation approximate/precise dictionary. OS consent still
applies. No notification center, push-subscription manager or history is added.

CEF callbacks now wait asynchronously for a shell permission card instead of a
Windows dialog. The card is 360 DIP wide at x=12, toolbar bottom+8, bounded inside
the browser window. It shows the domain, exact requesting origin, appropriate
glyph, Allow and Block. Explicit choices are saved atomically through the existing
policy and synchronized to Chromium. Dismissal saves nothing.

At most eight requests are queued. Combined media requests share one card.
Each entry binds tab ID, URL, document generation, requesting origin and CEF
request ID. Already decided queued requests complete without duplicate prompts.
Navigation, tab switching, tab close and shutdown cancel pending requests.
Background requests cannot overlay the active document. CEF dismissal removes
its entry without completing an invalid callback twice. Stale IDs cannot grant
access. Unsupported masks are refused rather than assigned fake controls.

CEF popup creation is synchronous. An Ask popup is blocked while the card saves
the choice for the next attempt; the text asks the user to repeat the action.
Soulu does not manufacture a new tab with a different opener/context. Ordinary
user-initiated links retain their existing routing. Download callbacks can wait
asynchronously; the ordinary file-save picker is retained.

## Clear and reset

Clear Site Data now has a compact Soulu confirmation, including the existing
Settings site-data subview. The confirmed action remains bound to the original
tab, URL and generation. The unchanged `SiteStorageJob` removes localStorage,
sessionStorage, IndexedDB, Cache Storage and service workers for the exact origin
and profile context. Cookies, HTTP cache, passwords, bookmarks, history, other
origins and other profiles remain. Success waits for Chromium acknowledgement.
A live document can recreate its storage.

Reset atomically removes the current domain's permission and AdBlock overrides,
preserving global defaults and site data. Live sound/content settings update and
the panel reports success. A change in effective AdBlock also reloads resources,
matching the existing switch. Previously reset removed the exception without
reloading resources cancelled by the old policy, so the page could still look
blocked. The panel remains open through this specific reload.

## Reader

Readability extraction, isolation, sanitizer, image requests and routing remain
unchanged. The Aa palette has four working themes (light, sepia/warm, gray, dark),
one concrete font selector, A−/current size/A+, visual widths and spacings, and
an image switch. Changes apply through the existing profile preferences bridge.
Size remains 14–32px; rapid size/image changes use the latest accepted value.

Existing serif/sans/system IDs retain Georgia, Arial and the Windows system UI
family. Cambria, Calibri, Times New Roman, Palatino Linotype, Verdana and Trebuchet
MS appear only when Windows enumerates the family. Palette and Settings share the
native list/validation. No macOS fonts are invented or downloaded. Invalid or
unavailable stored choices use the existing serif default and CSS fallback.
Article font selection never changes the Onest controls.

Preferences remain in `soulu-reader.json` with atomic writes. Private preferences
remain in memory and disappear with the last private tab.

## Checks

`test-cef-site-surfaces.py` covers actual notification/media callbacks, origin
binding, dismissal, stale navigation, background requests, serialization,
persistence, reset, themes, layouts and emulated raster scales. Fake media
devices do not bypass permission UI. `test-cef-site-reader.py` retains extraction,
sanitizer, links/images, storage cleanup, profile/origin isolation and incognito
checks, replacing obsolete UI assumptions. Public Reader checks cover four themes.
The existing Windows workflow retains AdBlock, Settings, typography, toolbar,
motion, history, storage, profile and navigation checks.

Actual results belong in the release report. Authenticated Google/Ozon sessions,
OS location consent, physical camera/microphone hardware, physical monitor DPI
and a real VPN connection require the corresponding environment; controlled
fixtures and screenshots cannot attest those checks.
