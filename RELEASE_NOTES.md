# Soulu Beta 1.0.55 — native menus and local page translation

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
