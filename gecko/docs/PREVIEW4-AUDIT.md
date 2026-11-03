# Preview 4: implementation decisions

Audit baseline: CEF main f3a4ae3fc1f15487c95811de8010524ab95b311b; Gecko Preview 3 7798bb7f046fc5c97b26bee26a4822d34e34f3a9; Mozilla Firefox 159.0. Source inspection is not runtime acceptance. All rows require actual browser checks.

|Component|CEF|Gecko 3|Decision|Required work|
|---|---|---|---|---|
|Tabs/navigation|CEF controller, adaptive UI|gBrowser with original UI|Keep Firefox + Gecko|Restore, duplicate, reorder, forward, stop, shortcuts|
|Session|Own persistence|Native SessionStore preferences|Keep Firefox|Active tab and restart checks|
|Profiles|Own per-profile data|Separate Firefox processes and directories|Keep Firefox|Rename; reject deletion while locked|
|Private browsing|CEF private context|Firefox private windows|Keep Firefox|History and storage isolation tests|
|VPN|Go helper, Xray/VLESS, Sudoku|Same helper and cores, NSS configuration|Keep Gecko/CEF adaptation|Separate profile port/root, fail-closed tests|
|AdBlock|Rust adblock-rust, EasyList/EasyPrivacy/RuAdList|Same Rust source; request observer + cosmetic actor|Keep Rust|Native Gecko downloads + atomic Rust filter install; avoid duplicate URL blockers|
|History|Own DB|Places|Keep Firefox|Search/delete/clear/restart checks|
|Bookmarks/favorites|Own DB|Places adapter|Keep Firefox|Native invalidation, favicons and folder tests|
|Passwords|Windows-protected CEF store|NSS/LoginManager|Keep Firefox|GUID editing, native save/autofill tests|
|Browser import|Own importers|Incorrect migration API path|Keep Firefox|MigrationUtils native wizard; accurately describe supported browser formats|
|HTML/CSV import|Own parsing|Not exposed|Keep Firefox|BookmarkHTMLUtils and LoginCSVImport; no path access from web pages|
|Privacy|Own settings|Native cookie isolation, clearData|Keep Firefox|Guard stale clear requests; keep partitioning and HTTPS/security defaults|
|Permissions|CEF callbacks|Native permissions manager|Keep Firefox|Downloads preflight; camera/mic/geo/popup checks|
|Downloads|CEF download manager|Native read-only list|Keep Firefox|Cancel/retry/open/reveal/remove, directory selection|
|Page translation|Local translator|Native local Firefox translator|Keep Gecko|Retest Russian translation and restore|
|YouTube voice translation|VOT implementation|Unavailable|Defer|Large cross-process integration; do not expose working-looking control|
|Extensions|Chromium extensions|Firefox WebExtensions|Keep Firefox|Native Add-ons manager/store; CRX and toolbar pinning deferred|
|Reader|Own DOM extraction|Not implemented|Keep Firefox|Native Reader View and compatible font/theme preferences|
|Performance|CEF freezing/timers|Firefox low-memory unload|Keep Firefox|Unload eligible background tabs; CEF timers explicitly unavailable|
|Home|Search, favorites, weather, voice|Original UI; Open-Meteo|Keep Gecko|Provider routing; voice explicitly unavailable|
|Weather|Provider integration|Open-Meteo with permission-aware location|Keep Gecko|Real response/error/cache checks|
|Themes/Mica|Native Windows materials|Native Mica + original CSS|Keep Gecko|Preserve light/dark/system; no screenshot polling|
|Settings|12 sections|Original HTML/CSS|Keep Gecko|Each supported setting must act and persist|
|QR/share/find|CEF utilities|Partial|Adapt CEF + native|Local QR generator, native clipboard/finder|
|Security bridge|CEF messaging|Exact installed principal allowlist|Keep Gecko|Adversarial web-content test; no generic privileged API|
|Sandbox/isolation|CEF|Firefox Fission and sandbox|Keep Firefox|Never disable in shipped defaults|
|Default browser|Installer registry integration|Portable only|Defer|Do not imply registration works|
|Soulu auto-update|CEF update workflow|Portable ZIP|Defer|Use reviewed releases; runtime pin explicitly documented|

Firefox 159 API compatibility: SessionStore and MigrationUtils use moz-src:/// browser module URLs; moveTabTo accepts {tabIndex}; Downloads uses the registered Integration.downloads hook, preserving native parental/reputation checks. Distribution defaults replace active Preferences policy because Firefox 159 ServiceRequest expects an array from an API that currently returns an object. Do not re-enable that incompatible policy.

The single Rust URL blocker replaces duplicate ETP URL classification, while native cookie partitioning, Safe Browsing, sandboxing, certificate verification and Fission remain enabled. Native extension URL blockers may still be installed by the user; Soulu does not install a second one.
