# Soulu Beta 1.0.54 — site controls and Reader appearance

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
