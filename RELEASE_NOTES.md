# Soulu 1.0.73

- Fix VPN icon vertical movement under hover/pressed/busy styling; keep the address row at a fixed height when adaptive tabs open or close.
- Update tab selection, labels and media in place instead of replacing sibling elements. Closing an active tab selects its adjacent sibling within the same profile/private group. Calculate widths before painting and retain the latest native animation frame.
- Close address suggestions on outside clicks, content focus and native window deactivation. Cancel stale suggestion results and dispose detached address bindings.
- Prevent duplicate Settings hover labels: use one DOM tooltip, remove competing native titles, and suppress native tooltip rendering on Settings surfaces.
- Add a persisted Home toolbar button toggle in Interface settings.
- Canonicalize bundled file URLs for installation paths containing spaces, Unicode, percent signs or fragments. Recognize Home correctly and prevent a permanent Home loading indicator. Weather requests have a bounded UI wait.
- Twelve Settings sections: new Extensions, Translation and Performance; Reader mode contains only Reader settings. Page translation and YouTube voice-over settings move to Translation.
- Performance controls: balanced, resource-saver and maximum-performance modes; background-tab pause timer; domain exclusions; optional collection of unused JavaScript objects; manual optimization. Freezing is acknowledged by Chromium, preserves documents/forms, and resumes on activation. Active, pinned, playing/capturing and downloading tabs are protected.
- Extensions is a catalog section. Chrome extension installation is not supported in this release; no install operation or extension compatibility is claimed.
- Remove the bookmark panel close cross. Compact action labels fit the two-column menu; Add current page occupies at most two lines.

Automated Windows runtime, lifecycle, UI, persistence and package checks are required before publication. Physical desktop, real user accounts and configured remote VPN services are not claimed as manually verified.
