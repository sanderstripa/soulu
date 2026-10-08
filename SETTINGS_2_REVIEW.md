# Settings 2.0 — awaiting user review

Baseline: clean clone of GitHub main, fetched and pulled before editing:
`49b90f22bbb94d17d9428309b4dfcd4a96b129fd`.
Latest published release at the start: `beta-1.0.57`.
Pinned CEF: `154.0.33+ga03e714`; Chromium: `154.0.8037.94`.
No engine or product version bump is part of this review.

The user requires an interactive review before tests, release builds, commits,
pushes and publication. Continue only after “Хорошо. Продолжай”.
No test result or native build success is claimed at this stage.

## Information architecture and bindings

| Previous location | New location | Binding / scope |
| --- | --- | --- |
| General | General → Language and system | Profile settings; Windows default-app action |
| Downloads | General → Downloads | Profile downloadPath / askDownloadLocation; existing folder picker and opener |
| Interface | Interface → Appearance / Toolbar items | Profile theme, mattePanel, layout and existing toolbar keys |
| Bookmarks | Interface → Bookmarks bar | Profile bookmarksBarMode / bookmarksBarPosition / bookmarksIconsOnly |
| Tabs and pages | Startup and home | Independent startup*, newTab*, home* keys; weather permissions and existing bookmarks IDs |
| Search | Search → Address bar | Profile searchEngine / addressOpenMode |
| Websites → Permissions, exceptions, ad blocking, site data | Privacy and security | Existing per-profile SitePolicy and site storage actions |
| Profiles and data → History and clearing / Passwords | Privacy and security | Profile history settings; existing History and PasswordVault entry points |
| Websites → Reader mode / Soulu Translate | Reading and translation | Existing per-profile reader preferences and translationTarget |
| Profiles and data → Profiles / Import / Incognito | Profiles and import | App profile registry; explicit import targets; existing incognito action |
| VPN | VPN | Existing global VPN dictionary and native helper |
| Updates | About Soulu | Runtime component versions and truthful existing updater status |

`showDownloads` is toolbar visibility. `downloadsMode` independently chooses
always-visible versus visible-during-download behavior. Both are retained and
renamed to make that distinction explicit. No migration or storage key changes.
`automaticUpdates` remains a legacy value without a working updater; no fake
toggle is added. Home-only editor controls remain in Home. No new settings
or alternative bookmarks, permissions, reader, import or VPN engines are added.

## UI and save model

Home is a responsive three/two/one-column grid, with nine entries and no rail.
Internal pages have a compact named navigation column, becoming an icon rail
on narrow widths. The header and navigation remain fixed while content scrolls.
Search retains the existing index and targets actual controls in their new
sections; result navigation preserves highlighting and conditional-page hints.

The header places search next to a 42px close target. Settings has neutral
surfaces, compact rows, shared controls and local Onest fonts. Typography is
loaded before settings.css, so shared global declarations cannot enlarge the
new controls. Titles are 21/19px, labels and controls 13px, descriptions 11.5px.

`ui/settings-icons.js` is the canonical new monochrome system: 24-unit viewport,
1.5-unit stroke, rounded caps and joins, 19–24px optical display sizes. It owns
home, rail, page, search, close and chevron glyphs. The favicon is redrawn too.
Category colors and colored icon backplates are removed.

The native `settings.save` handler validates and writes each requested snapshot
using the existing settings, SitePolicy, reader and VPN writers. It preserves
the old per-key concurrency guards and returns the actual stored snapshot,
including partial-write errors. The requested value exists only during the save
call. Persistent staged/preview dictionaries, dirty flags, Apply, Cancel,
rollback and close-with-unsaved-changes dialogs are removed.

Toggles, selects, segments, favorite selection and permission exceptions queue
saves immediately. Text and URLs commit on change/blur; Enter blurs a single-line
input. An empty custom page opens its URL field for local text entry and commits
mode plus URL together, so no invalid empty custom URL reaches storage. VPN
keys use the existing parser at commit. A protocol without a key represents an
unconfigured VPN and does not connect the helper.

Close and profile actions blur text inputs and await queued saves. Destructive
clear/delete/reset actions retain their existing confirmations.

The native Settings overlay keeps its existing geometry, backdrop and downward
entry. A Settings-only composition shadow follows the native panel through
movement and opacity changes. Shared backdrop behavior is unchanged unless the
new Settings-specific function is called.

## Interactive preview limitations

For the user's review, the new UI is copied into an isolated local portable
copy of the published 1.0.57 release. A review-only adapter outside the repository
translates `settings.save` into the published binary's stage/apply calls, applying
and persisting on every normal interaction. It cancels failed temporary drafts.
The user's usual profile is not used. This adapter is never shipped.

This preview shows the new UI and exercises the published storage implementations.
It does not run the changed native save handler, new native composition shadow,
or removal of native profile dirty guards. Those need a new native build and
verification after the user approves. Existing staged-model tests must then be
updated to assert live-save behavior before executing the required targeted,
persistence, native, keyboard/DPI and final regression checks.

After those checks, commit and normal push to main, verify HEAD equals origin/main
and the tree is clean, then build and publish the next release from that final
main SHA. Do not start another product block.

## Second visual review

User requested four changes before approval: a pill-shaped search field, removal
of the header divider, stronger exterior shadow, and a compact Home that expands
to the existing workspace height when entering a section.

Search now has a fully rounded radius. The header has no bottom border. Native
shadow uses 34% opacity, 20px blur and an 8px vertical offset, scaled with DPI.
Intrinsic Home/search content height is observed and sent through the trusted
`settings.resize` endpoint. `SettingsOverlay::SetPanelHeight` clamps requests to
160–800 logical pixels and retains the owner-client bounds and top anchoring.
Sections request the existing 800px height; returning Home measures its entries
again. Narrow Home and large search results scroll within the capped height.

The published-executable preview has a separate, review-only native companion
outside the repository that applies panel height and an exterior layered shadow
to this isolated preview process. Production uses the C++ overlay and Windows
Composition implementation. No native build or regression checks have been run;
the user's original approval gate remains in place.

## Preview input hang correction

Windows recorded `AppHangXProcB1`: the preview Soulu process was waiting on
the Python companion. The companion owned a native shadow window while making
blocking renderer/network requests on its window-message thread. That created
a cross-process input wait. Network observation now runs on an independent
daemon thread; the native window thread continuously services Windows messages.
Panel position requests are asynchronous, and the companion exits with the
preview browser. This review-only companion is not part of production.

The published CEF `cefQuery` function also cannot be replaced through assignment.
The preview adapter now uses a separate `souluPreviewQuery` hook only in the
copied preview UI. Repository UI continues to call the production native bridge.

The user's repeated freeze report authorized the focused reproduction/fix check:
real Windows mouse clicks opened all nine sections and returned Home, confirmed
compact/expanded height requests, saved and restored a toolbar toggle, then
closed/reopened Settings and navigated again. All remained responsive. Evidence:
`../preview-input-fix-evidence.json`. These are preview diagnostics, not a claim
that the changed native production code or final regression suite has passed.

## Search alignment and motion review

Search width now follows the left edge of the rightmost Home grid column instead
of using a fixed 290px width. In the current 1020px preview it measures 268px;
its left edge differs from the card column by less than one pixel.

Settings-only height and entry/exit animations use a 380ms smooth start/stop
curve. Height retargets from the currently displayed value, including rapid
navigation. Native resize ticks update only the panel clip and placement, not
the full backdrop host. Closing cancels pending height animation.

Section transitions use a dedicated 320ms content fade with a 45ms delay and
5px movement. They are independent of global viewport-resize cancellation,
so changing native panel height cannot cancel the reveal midway. The previous
cloned-page/shared-glyph transition is removed from Settings. Reduced-motion
preferences retain brief fades and immediate height changes in production.

The review companion listens for resize notifications instead of polling height,
tweens height over 380ms, and renders shadow edges from one small cached template
per DPI rather than blurring a full-window bitmap each frame. Network notification
handling stays separate from the responsive native message thread. The updated
preview expanded to 800px and returned to 472px with no bridge errors; it was
left open on Home. Native production compilation remains behind the approval gate.

## User-authorized toolbar and Home refinements

The user explicitly expanded the review scope to the primary browser toolbar
and Home. Settings and dialog Close now retain their 42px target while showing
a 32px circular hover surface with the toolbar's red hover/pressed tint (22/34%).

Canonical geometry raises toolbar action glyphs from 16px to 20px. A distinct
16px addressGlyph token keeps all address-capsule icons at their previous size.
VPN images, navigation, downloads, new-tab, overview and window actions use the
shared 20px glyph. Hit targets, toolbar heights and address layout stay intact.

Home's existing 20px right inset is a shared geometry token. Both toolbar layouts
inset the window-action group by 21px, aligning the 42px Close target's center
with Home's 44px favorites target. Existing DOM-derived maximize hit bounds
continue to supply native caption/Snap geometry. In the 1280px review viewport,
both centers measured 1238px. Address glyphs measured 16px; window, overview and
VPN glyphs measured 20px.

Light Home uses white instead of #fafafa, matching the existing white opaque
toolbar. Its native initial background is also white in production. Dark Home
and matte/transparency behavior retain their existing semantics. No engines,
toolbar architecture or Home configuration/storage are redesigned.

The preview was refreshed with these visual changes. Final native compilation,
required product/regression validation and publication remain pending the user's
explicit approval.


Latest visual review: initial Settings readiness awaits Onest and measured compact height; ready carries height and the native overlay applies it before opening. Review adapter holds readiness until the isolated native companion has sized/clipped the hidden panel. Main toolbar glyphs now 18px, window Close remains 20px; address actions use optical footprints around 9px (cross 20px viewport, reload 15px, star 12px). Non-client Snap hover has explicit native tracking; tooltips extend the shell below the buttons instead of clamping over them. Full checks, native build and release still await the user's “Хорошо. Продолжай”.

Latest review refinement: address star/reload/close now share 24px vector coordinates, 18px boxes and 1.25px strokes; action vectors use common strokes, caption minimize is centered at y=12, center cluster anchored at half toolbar height. Window Close unchanged. Section-to-section changes crossfade outgoing content over incoming content and keep the rail visible. Hidden panel shadows are suppressed until the panel actually enters the owner clipping region; preview shadow also fades at its visible edge. Awaiting visual approval before full checks/build/release.

Screenshot review correction: reverted section crossfade to the prior fade behavior as explicitly requested. Removed the broad SVG display override that exposed both Reload and Stop, and assigned mutually exclusive reload/loading states to a shared centered grid cell. Approved right caption actions and New Tab retained. Full checks/build/release still gated on visual approval.
`nVisual review adjustment: address Reload and Close reduced from 18px to 16px to match the approved star visually. Star remains 18px; shared stroke and centered hit targets retained. No full checks/build/release before approval.

User-defined toolbar grid: ordinary and address glyph boxes 16px, shared physical strokes 1.5px, ordinary hit targets 32px compact / 30px classic. Back matches sidebar vector bounds with opacity-only disabled presentation. Caption glyphs 10px with 46x32px centered hit targets in both layouts. Previous per-role optical size exceptions removed. Visual preview pending; no full checks/build/release before approval.

User reverted the last uniform-grid revision. Restored prior toolbar geometry and vectors: ordinary glyphs 18px, window Close 20px, caption width42, heights58/48; address star18, Reload16, Close14. Settings transition and prior preview fixes retained.
Caption hover fix: explicit hover state synchronized during native hit testing as well as non-client mouse tracking. Preview launcher restores its companion after browser restart so native Snap hover feedback remains visible. Full checks/build/release remain pending approval.
