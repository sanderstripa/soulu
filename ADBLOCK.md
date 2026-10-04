# Soulu AdBlock

## Original failure

Audited base: `17483c8554fe044d515fef35d6e9f76e982108c8`, Beta 1.0.52.
The original `BlockResource` was an eight-domain hardcoded allow/block check,
not a filter-list engine. Only script, image, stylesheet and font requests were
considered. `GetResourceRequestHandler` excluded all navigations (including
iframes), and `OnBeforeResourceLoad` required both browser and frame. XHR/fetch,
iframe, media and browserless worker requests bypassed it. There were no bundled
subscriptions, parser, updater, cache, cosmetic filtering or runtime counters.
Settings persisted, but ON could only activate this small subset.

Published Beta 1.0.52 was run locally on E1 with a disposable profile, HTTP cache
disabled and OFF/ON captures. Both showed a large top advertisement and side
advertisements. Those screenshots are an original-version baseline, not evidence
of the new implementation.

## Engine and dependencies

The placeholder matcher is removed. One process-wide `adblock-rust 0.13.3`
engine handles ABP-compatible rules. Cargo.lock pins the dependency graph.
Windows builds link a native Rust static library through a narrow C ABI; no
browser extension, proxy, driver, certificate, administrative rights or separate
runtime service is needed. Rust panic boundaries prevent unwinding into C++.
The engine uses indexed compiled rules and its embedded public-suffix resolver.
Request scheme/hostname/IDNA/trailing-dot normalization preserves URL path case.
Rules support hostname/URL/wildcard/regex matching, domain restrictions, first-
and third-party restrictions, positive/negative resource types, exceptions and
explicit important-rule semantics. Generic matches do not override exceptions.

Engine: MPL-2.0. EasyList/EasyPrivacy: CC-BY-SA-3.0 option of their dual licence.
RU AdList: CC-BY-3.0. Notices, licence texts and transitive dependency attribution
are shipped in `licenses/adblock`. Original lists remain unchanged in source.

## Lists, cache and updates

Bundled directly in the executable, so a new installation works offline:

| Subscription | Official HTTPS source | Bundled version |
| --- | --- | --- |
| EasyList | https://easylist.to/easylist/easylist.txt | 202610040711 |
| EasyPrivacy | https://easylist.to/easylist/easyprivacy.txt | 202610040711 |
| RU AdList | https://easylist-downloads.adblockplus.org/ruadlist.txt | 202610040712 |

Bundled date: 4 October 2026. Rules are initialized before CefInitialize can
open the first web page. Lists are shared, while settings stay profile scoped.
Cache: `%LOCALAPPDATA%\Soulu\User Data\AdBlock\filters-v1.json`.
It contains all three raw lists, schema, successful update timestamp and a
SHA-256 integrity digest covering length-prefixed list contents.

A background thread checks hourly, updating when the last successful update
is at least 24 hours old. HTTPS-only downloads use 10-second connection and
30-second request timeouts. Redirects are rejected, including HTTP redirects;
updates never weaken TLS checks. Each list has a 16 MiB limit. HTTP status,
text/plain content type, UTF-8, ABP header, version, parser result and meaningful
per-list rule counts are validated. A large count reduction is rejected.
Only a fully compiled candidate can replace the current rules. The cache is
written to a temporary file, synced, then atomically replaced using MoveFileExW.
After that, an Arc rules snapshot swaps under a short write lock. Requests
already in progress keep their old immutable engine alive.

Timeout, HTTP error, redirect, invalid content, failed write or invalid parser
result retains the last working engine/cache and records an update error.
Corrupt cache falls back to the bundled lists, without crashing or claiming
zero-rule protection. Missing cache is an ordinary first-install condition.
No visited domains, filter hits or browsing data are sent to Soulu servers.

## CEF integration and settings

Content BrowserClient::GetResourceRequestHandler includes subresources and
iframe navigations. OnBeforeResourceLoad matches synchronously on the CEF IO
thread and returns RV_CANCEL before resource transfer. OnResourceRedirect
checks the redirected target before it is followed; blocked targets become an
HTTP-to-data redirect Chromium refuses before contacting the destination.
User-initiated top-level navigation and downloads are excluded deliberately.
Browserless Service Worker traffic has a separate profile-owned request-context
hook using its initiating origin and the same engine/settings.

Types: script/worker scripts, image/favicon, stylesheet, font, media, iframe,
XHR/fetch, ping and other CEF resources. Document matching is supported by the
engine, while top-level user navigation is exempt in the browser adapter.
CEF does not provide a dedicated WebSocket resource type here; WebSocket
handshake blocking is not claimed. Service Worker responses served entirely
from their own CacheStorage do not perform a network request to intercept.

The top-level policy URL is a locked BrowserClient snapshot updated from UI
navigation/address events, not mutable tab state read from the IO thread.
Subresource rule conditions use the initiating frame URL. Policy remains that
of the top-level site. All content tabs/popups share the process-wide engine.
Internal file/UI pages and local Reader UI are not filtered.

Global/default and host overrides use the existing SitePolicy model, stored in
each profile's `soulu-site-rules.json`. Explicit site ON can override global OFF.
Settings mutations apply immediately to new requests and refresh cosmetic
styles in existing frames. Site Info changes also reload the page without HTTP
cache to remove already loaded advertisements. Incognito starts with a copy of
the active profile's policy, keeps mutations only in memory, and discards them
when its final tab closes. Its context owns the temporary policy safely.

## Cosmetic filtering and diagnostics

A fixed local renderer program gathers class/id tokens in batches (256 per
message), on initial DOM creation and debounced mutations. The engine selects
only relevant generic/domain-specific CSS selectors and honors cosmetic
exceptions/generichide. CSSStyleSheet/adoptedStyleSheets applies rules without
relaxing site CSP. JSON serialization keeps selectors as data. Selectors with
rule-breaking punctuation are rejected; invalid CSS is ignored independently.
SPA insertions and subframes use the same lifecycle. Disabling protection removes
the injected stylesheet immediately.

Scriptlets, arbitrary downloaded JavaScript, procedural cosmetic actions,
resource redirects and removeparam rewriting are not implemented by this
adapter. No claim of complete uBlock Origin compatibility or complete removal
of YouTube/first-party/server-side advertising is made. Token collection is
bounded (10,000 elements per collection, 20,000 unique classes/IDs per document).

SiteSnapshot.adblock reports setting state separately from readiness/active
protection, real loaded rule counts, engine version, subscription versions,
cache/bundled source, last successful update/error and blocked/checked requests.
Counter scope: current tab document, reset on main navigation, not an eternal
global statistic. Browserless worker hits are not attributed to a tab counter.
Detailed hit samples exist only in an explicit SOULU_UI_TEST_PORT diagnostic
process, are capped at 200 per document and include timestamp/site/type/URL/rule.
They contain no headers, cookies, Authorization, request bodies or passwords.
Site Info displays readiness and its real blocked count without a redesign.

## Verification

Engine tests exercise rule matching, eTLD+1, resource types, exceptions, wildcard
separator semantics, cosmetics, valid/corrupt cache and atomic live replacement.
`scripts/test-cef-adblock.py` runs actual CEF with deterministic resources. It
asserts that cancelled script/image/iframe/fetch/redirect requests never reached
the HTTP fixture server; normal resources and exception rules do reach it.
It additionally tests official EasyList, cosmetics/CSP/SPA, OFF/ON, per-site,
profile isolation, incognito, restart and offline corrupt-cache fallback.
The fixture-rule path/update suppression is accessible only in an explicitly
gated diagnostic process; no fixture domains are hardcoded in production rules.

`scripts/test-cef-adblock-public.py` captures OFF/ON network events, actual
runtime counters, DOM/cosmetic observations and screenshots of E1, Lenta, RIA,
The Guardian and the requested normal sites. An opened public login page is
not proof of authenticated session persistence; real account/VPN manual release
gates must remain satisfied before publication.

CEF stays 154.0.33+ga03e714; Chromium stays 154.0.8037.94.
Compilation alone and synthetic fixtures alone are insufficient acceptance.
