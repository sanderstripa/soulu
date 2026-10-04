# Soulu Beta 1.0.53 — functional AdBlock repair

- Replaced the limited built-in matcher with real indexed network filtering for advertising and tracking requests, including iframe and fetch/XHR resources.
- Bundled EasyList, EasyPrivacy and RU AdList so enabled protection works immediately, including offline startup.
- Added relevant cosmetic selectors, domain-specific rules and exceptions to hide remaining advertising containers.
- Connected global/per-site controls to actual runtime protection, preserving profile settings and temporary incognito overrides.
- Added validated background HTTPS updates, an atomic cache and fallback to the last working or bundled rules.
- Added real blocked-request counters and diagnostic filter status in Site Info.

CEF/Chromium and the existing typography, motion, toolbar and window design remain unchanged.
Scriptlets and complete uBlock Origin compatibility are not claimed. First-party/server-side and anti-adblock advertising can remain.
