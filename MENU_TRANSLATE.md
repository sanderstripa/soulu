# Soulu Menu System and Soulu Translate

## Native menu ownership

`cef/soulu/soulu_menu.cc` owns copied menu models and renders native popup
windows outside website DOM. `TypographyFont(compactControl, dpi)` supplies
the bundled Onest face. Theme colors, row spacing, separators, rounded corners,
hover/pressed/focus states and submenu placement are shared by all callers.
Models support actions, separators, disabled items, check/radio items and nested
submenus. MSAA exposes names, roles, states, bounds, focus and default actions.

CEF editing and spelling commands remain CEF commands; their transient models
are copied before opening the shared native host. Link/image/media/page actions
use browser-owned command handlers. Read-only controls are identified by a
bounded isolated-world hit test rather than general CEF Select All flags.
Website-owned menus are unchanged. Native file dialogs and print dialogs remain
their respective operating-system/CEF services rather than menu surfaces.

## Translation provenance

The packaging script verifies official npm archive SHA-512 before extracting
`@browsermt/bergamot-translator` 0.4.9 and tinyld 1.3.4. The JavaScript package
revision is `8cc5d0495479c9ec56eafafd6bcd7fb5b929ca98`; its embedded inference
binary identifies as `v0.4.5+4917c11`, source revision
`4917c1124e394acd8deb78100b7c81a69999ffe8`. Package and embedded engine versions
must not be conflated. CEF/Chromium are unchanged by this feature.

Official upstream repositories and the Mozilla fork were inspected; compatibility
of this supplied binary with the selected current Mozilla models was verified
by real inference. Soulu wraps upstream JavaScript into a classic local script
and embeds unchanged WASM in a Blob worker. The worker avoids dynamic JavaScript
evaluation and uses the shell's restrictive CSP with `wasm-unsafe-eval`.

The model registry comes from Mozilla's public
`moz-fx-translations-data--303e-prod-translations-data/db/models.json` bucket.
`ui/translation-models.json` pins exact URLs, decompressed sizes and SHA-256
for en→ru, ru→en and de→en. German→Russian pivots through English. No language
is offered merely because a remote translator might support it.

Bergamot and Mozilla models are MPL-2.0. Bundled notices include Marian,
SentencePiece, intgemm, Apache-2.0 sentence splitting, LGPL-2.1 prefix data,
tinyld and QR generation. Exact revisions and source links are retained in
`ui/third_party/notices/THIRD-PARTY.md`; packaging includes the license files.

## Execution and data

tinyld detects a bounded sample of eligible visible text; sufficiently long
samples override incorrect HTML language hints. The target comes from the
profile's translation settings. Direct model pairs are preferred; supported
pivot routes use English. Same-language requests preserve the text.

Native download requests accept only a pinned model SHA, use the official
HTTPS bucket, omit stored credentials, reject redirects and enforce byte/time
limits. JavaScript decompresses and verifies the registry size and SHA-256 before
acknowledging the downloaded buffer to the native cache. Only acknowledged
buffers are persisted; failed validation discards the pending download.

The shared cache is `%LOCALAPPDATA%/Soulu/User Data/Translation/Models/v1`,
outside `Profiles` and all website cookies/storage. It stores model resources
under registry-hash keys with separate compressed-resource SHA-256 records.
File reads, hashing, pruning and atomic replacement run on CEF's file task
runner. Readback checks the stored resource hash before returning bytes, then
JavaScript rechecks decompressed registry size/hash before inference. Invalid
and stale entries are deleted; manifest updates introduce new keys. Unverified
automatic replacement and external translation fallback are not used. A
standalone web test harness uses IndexedDB only when the native cache bridge is
absent; production CEF uses the native shared cache exclusively.

Inference runs in one WASM worker with batches of eight and a bounded inference
cache. Models are reused between paragraphs. Jobs carry tab/document/token
guards; cancellation removes queued requests and discards stale results.
The worker is disposed when the shell closes. Available model routes are bounded
to the three pinned pairs, rather than an unbounded language inventory.

DOM access uses a dedicated CEF isolated world. Lazy text scans and bounded
collections preserve original text per node. Inputs, passwords, selects,
contenteditable, code/pre, scripts/styles, translate=no, hidden text, SVG,
canvas and URL-only strings are excluded. A MutationObserver queues inserted
or changed text and ignores the translator's own writes. Restoration changes
only nodes still holding Soulu's translated value, preserving subsequent site
edits. Full navigation invalidates jobs; same-document URL changes restore the
original and start with a new generation. Shadow roots and cross-origin frame
documents are not traversed by the main-document translator.

Always/never preferences are persisted in each profile's `soulu-settings.json`.
Private-tab preferences remain in memory and are discarded with that tab.
Shared downloaded model buffers contain public model files, not private page
text. QR codes are generated locally with qrcode-generator 2.0.4.

## Verification

Run `node scripts/test-translation-unit.cjs` for routing/detection/integrity.
`scripts/test-cef-translation.py <Soulu.exe> <output>` checks real native model
transport, real inference, toolbar translation, original restoration, excluded
controls, dynamic/long pages, stale and SPA navigation, offline worker/restart,
preferences and profile/private-tab isolation. Its NetLog evidence checks model
GETs and absence of cloud translation provider requests.

`scripts/test-cef-menu-system.py <Soulu.exe> <output>` checks native context menus
in RU/EN, compact/classic, light/dark and 96/120/144/192 DPI. These are dedicated
native menu layout/font overrides, not changes to Windows monitor settings.
It records accessibility labels/roles/states, keyboard dismissal, recursive
commands and screenshots. Existing link/history/platform suites check actual
routing, cookie isolation, clipboard, history and native downloads.

These commands describe coverage, not a claim that any particular release has
passed them. The release report must identify the tested SHA and actual results.
