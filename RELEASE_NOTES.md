# Soulu Beta 1.0.58 — Settings 2.0

- Settings Home and all nine sections use the compact monochrome design reviewed with the owner, bundled Onest typography and a new Settings icon family.
- Ordinary settings save immediately through existing canonical stores. Global Apply/Cancel, staged preview and dirty-close confirmation are removed. Invalid values and write errors report the actual persisted state.
- Home opens at intrinsic height; sections expand smoothly. Search aligns with the right Home column. Native panel sizing precedes its first visible frame, and shadow follows the visible panel.
- Browser toolbar refinements retain the final reviewed sizes: regular glyph18, window Close20; address star18, Reload16, Close14. Reload/Stop are mutually exclusive and centered. Maximize retains native Snap behavior with explicit hover feedback; tooltips appear below buttons. Light Home is white.
- Startup/new-tab/home remain independent. VPN, Reader, profile, permissions, history, imports, storage and browser engines retain existing backend mechanisms.
- CEF 154.0.33+ga03e714 / Chromium 154.0.8037.94 are unchanged.

Validation and remaining manual limitations are recorded in the final verification report; no unperformed authenticated-session checks are claimed.

## Soulu Beta 1.0.57 — window geometry and surface polish

- Normal maximize constrains the root HWND and its input area to the current monitor work area, retaining auto-hide taskbar activation edges.
- F11 uses the current monitor's full bounds and restores the previous normal/maximized state. HTML5/video fullscreen is tracked separately, including inside F11.
- Main uses 58 DIP toolbar / 38 DIP container / 32 DIP active capsule and action targets, with 16 DIP glyphs and unchanged 42 DIP caption width.
- CSS and native content insets share generated DIP geometry; bookmarks, Reader, overview and popup fallbacks follow it. Classic retains its existing size.
- Browser-owned native menus retain Onest, command routing and opaque white light surfaces, with 12 DIP text and 30 DIP rows.
- Home keeps the omnibox completely empty; its logo/search group is slightly raised and the search capsule is more compact. Weather uses restrained color accents; source credits are available in Settings instead of the forecast card.
- The left toolbar button opens bookmarks. The address star opens one compact save/edit form for name, URL, folder and Home favorites, replacing sequential system prompts and their local file paths.
- CEF 154.0.33+ga03e714 / Chromium 154.0.8037.94 remain unchanged.
- Google/Ozon authenticated-session restart checks are deferred to the owner by explicit instruction; they are not claimed as passed for this release.
- Remaining physical desktop acceptance checks will be completed by the owner; automated Windows/CEF regression checks remain required.

## Beta 1.0.56 — Soulu Home

- Minimal local Home follows the approved layout, with the canonical logo, search capsule and separate weather/favorites popovers.
- Home offers Google and Perplexity independently from the omnibox provider, with direct address navigation and native foreground input focus.
- Immediate typing is retained while Home loads; Ctrl+L keeps control of the omnibox.
- Favorites use real ordered profile bookmark IDs and are managed through ordinary Settings. Legacy shortcuts migrate without deleting their source data.
- Weather uses Open-Meteo through the originating browser network context, with configured city or explicitly permitted Windows location, current conditions, five following days, bounded cache and calm offline behavior.
- Microphone capture and RU/EN recognition run locally with an integrity-pinned multilingual Whisper model. The interface distinguishes preparation, listening and recognition; cancellation releases the microphone and invalidates results.
- Existing page intents, profiles, private state and session behavior remain independent. New profiles receive Soulu Home and Google defaults.
- Bundled Onest, light/dark/system themes and responsive layouts are retained. No dashboard, feed, widgets, background editor or inline Home settings are added.
- CEF 154.0.33+ga03e714 / Chromium 154.0.8037.94 remain unchanged.

Voice recognition requires an available microphone and permission. Weather requires network access and a saved city or permitted Windows location. Public speech fixtures do not substitute for live microphone verification.

## Beta 1.0.55 — native menus and local page translation

- A shared native Soulu Menu System replaces browser-owned default context menus, using Onest, browser themes, keyboard navigation, nested menus and Windows accessibility.
- Expanded page, link, image and media menus connect to real browser commands, with foreground/background tabs, separate normal/private windows, clipboard actions, downloads, Reader, local QR codes and translation.
- Soulu Translate uses a local Bergamot WASM worker with Mozilla language models. English → Russian and Russian → English are direct; German → Russian uses English as a pivot.
- Verified models are downloaded on demand into a shared cache outside profiles. Cached translation works offline after restart; page text is not sent to a cloud translation service.
- Original text can be restored without reload. Translation handles dynamic text and navigation while preserving form values, editable content and code.
- Always/never translation rules are saved per profile; private-tab rules remain temporary.
- CEF 154.0.33 and Chromium 154.0.8037.94 remain unchanged.

Language coverage is limited to the bundled model manifest. The main-document translator excludes shadow roots, cross-origin frame documents and technical/interactive text. Unsupported language pairs are reported explicitly.

## Beta 1.0.54 — site controls and Reader appearance

- Compact Site Info with separate site settings and compact permission pickers.
- Soulu permission cards bind actual notification, location, media and download callbacks to the requesting document. Decisions persist; dismissal, navigation and tab changes cancel pending consent safely.
- Working notification controls use Chromium content settings and the Notification API.
- Site data clearing has its own confirmation and accurately describes the storage it clears. Reset removes permission and AdBlock exceptions while preserving stored site data.
- Reader appearance offers four article themes, installed Windows fonts, text size, visual width/spacing controls and an image switch. Interface controls retain Onest.
- Existing CEF/Chromium, AdBlock engine, Reader extraction and general Settings design are preserved.

Popup consent applies to the next attempt; repeat the site's action after allowing it. Physical devices, authenticated sessions and VPN checks require the corresponding environment and are recorded separately from controlled tests.

## Beta 1.0.53 — functional AdBlock repair

- Replaced the limited built-in matcher with real indexed network filtering for advertising and tracking requests, including iframe and fetch/XHR resources.
- Bundled EasyList, EasyPrivacy and RU AdList so enabled protection works immediately, including offline startup.
- Added relevant cosmetic selectors, domain-specific rules and exceptions to hide remaining advertising containers.
- Connected global/per-site controls to actual runtime protection, preserving profile settings and temporary incognito overrides.
- Added validated background HTTPS updates, an atomic cache and fallback to the last working or bundled rules.
- Added real blocked-request counters and diagnostic filter status in Site Info.

CEF/Chromium and the existing typography, motion, toolbar and window design remain unchanged.
Scriptlets and complete uBlock Origin compatibility are not claimed. First-party/server-side and anti-adblock advertising can remain.
