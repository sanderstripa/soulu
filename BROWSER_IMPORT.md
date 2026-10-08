# Browser Import 2.0 — preliminary implementation

This is the mandatory review stage, not a release or a claim of native readiness.
Baseline: `d290070a2f5a0e4954b9d031a9898ac0f4d926ca`, published release
`beta-1.0.58`. CEF 154.0.33 / Chromium 154.0.8037.94 are unchanged.

## Compact UI revision

The Comet references are used for interaction structure only. Import now opens a
single compact Settings 2.0 dialog, with From, To, category checkboxes, Cancel and
Import. No browser/profile/category wizard pages or confirmation dialogs remain.
Every discovered source profile is one dropdown option; HTML, password CSV and
custom profile-folder selection are options in the same dropdown. Browser profiles
are probed only after an explicit source selection. A stale probe cannot replace
the latest selected source. Source/target selections are locked during execution
and remain visible in the compact result.

To defaults to the current Soulu profile. New Soulu profile reveals an inline name
field; clicking Import creates it through the existing CreateProfile mechanism
without changing the active profile or opening tabs. The import-specific handler
defers catalog persistence until it can write atomically with WriteJson and rejects
a stale/unreadable catalog. A creation failure prevents the import from starting.
The corresponding C++ additions are pending native compilation/verification.

Available categories use 16px square checkboxes. Browser sources show bookmarks,
history, passwords, autofill and tabs, with concise reasons for unavailable items.
Additional categories appear only when a source adapter actually supports them.
HTML sources offer bookmarks or open-tab URLs according to the selected source option; CSV sources offer only passwords and require
explicit selection plus consent. File pickers filter the chosen export format.
Cookies, payment data and unsupported extensions are not advertised. Progress,
cancellation and imported/skipped/error totals appear inside the same dialog.

45 targeted UI/parser checks passed with a labeled synthetic adapter, covering the
dropdowns, deferred profile creation, a creation error, explicit destinations,
stale probes, picker cancellation, CSV consent, partial results, dark/narrow layouts
and no external requests. The main review window measures 440 × 519 pixels including
the demonstration label. These checks do not execute C++ or verify real imports.

## Discovery and adapters

The new Settings flow uses `browser.import.catalog`, separate from legacy password
discovery. Bounded standard profile-directory enumeration and Firefox profiles.ini
identify real profiles; no disk-wide recursion occurs. Local State info_cache is
read only for display names. Login stores are not inspected during discovery.
App Paths and known executable locations also identify installed browsers with no
accessible profiles. Ambiguous executable names do not identify another browser.
Opera root profiles and Default profiles have distinct catalog IDs.

| Source | Profile detection | Bookmarks reader | History reader | Passwords |
| --- | --- | --- | --- | --- |
| Chrome | LocalAppData, Local State, Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Edge | LocalAppData, Local State, Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Brave | LocalAppData, Local State, Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Opera | AppData, root or Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Opera GX | AppData, root or Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Vivaldi | LocalAppData, Local State, Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Yandex | LocalAppData, Local State, Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Chromium | LocalAppData, Default/Profile N | Chromium JSON tree | History visits + urls | Supported DPAPI/AES or NSS + CSV fallback |
| Firefox | AppData, profiles.ini relative/absolute paths | Places tree, positions, roots | Places individual visits | Supported DPAPI/AES or NSS + CSV fallback |
| Custom/portable | Explicit local profile-folder picker | Recognized Chromium/Places format | Recognized History/Places format | Supported DPAPI/AES or NSS + CSV fallback |

These are implemented adapter paths, **not verified compatibility claims for every
current browser version**. Capabilities are probed for the selected source, with
available/not found/action required/unsupported/blocked states and counts where
supported. A locked database is reported as unavailable, with a retry instruction.
The custom picker selects a single profile directory, not an entire User Data tree.

Autofill, session tabs, separate favicon databases, foreign preferences, downloads
and extensions are unsupported in this preview. Soulu has no verified address/form
autofill storage binding; no verified session parser or preference mapping was
found. Cookies, authentication tokens, payment data and extension executables are
excluded. Safe PNG/ICO data-URL icons in HTML exports can accompany bookmarks.

## Storage and privacy

Readers normalize data; there is no parallel imported-data store. Bookmark merges
use the existing bookmarks.json writer and publish updated lists to browser
windows. Existing rows survive; folder/title/URL/parent identities prevent repeat
imports while retaining the same URL at different locations. Imports do not mark
bookmarks as Home favorites. The older bookmark-file UI now also deduplicates by
folder, title and URL rather than by URL alone.

History uses HistoryStore, the current visit database and views. Exact URL/time
matches are skipped in a transaction. Chromium's 1601 epoch is subtracted in integer
microseconds before conversion to Soulu's Unix milliseconds; Firefox uses Unix
microseconds. Implausible timestamps and unsupported URL schemes are skipped.

CSV credentials go directly to PasswordVault (the existing user-scope DPAPI
storage), never to renderer previews or settings. The whole CSV is validated
before writes. UTF-8/BOM, quoted commas, multiline fields and escaped quotes are
supported, with 20 MB / 20,000 row limits. Required headers are url (or origin),
username, password. Existing origin/username conflicts are skipped, not replaced.
Explicit renderer consent is revalidated in the native handler. The user's export
is retained. Browser profiles also use the existing DPAPI/AES-GCM and installed
Firefox NSS importer, now bound to the common discovered/portable source and
ImportControl. v20 App-Bound and primary-password protected records are skipped,
reported separately and require export from the original browser. No impersonation,
injection into another browser, elevation or protection bypass is used. Legacy
onboarding retains its separate protected-record count for compatibility.

Autofill reads Chromium Web Data form values and allowlisted address tokens
(address_type_tokens, previous local/contact token tables and known legacy tables).
Firefox reads formhistory.sqlite and the addresses array of autofill-profiles.json.
Names, emails, phones, addresses and ordinary form values are normalized to
field names / standard HTML autocomplete tokens. Payment tables, creditCards,
password/token/card-like field names and unrelated types are excluded. Target data
is a per-profile DPAPI-encrypted model, atomically saved after complete validation;
repeated name/value pairs are skipped and cancellation before commit writes nothing.
The model is consumed by the browser-owned “Fill from Soulu…” field menu, not
inert import-only JSON. It reads the field in an isolated world, offers matching
values in Soulu's native menu, and fills only the chosen field. Password choices
are restricted to the current origin. Disabled/read-only fields, autocomplete off,
new passwords, OTP and payment fields, cross-origin forms and incognito are excluded.
This adds explicit field-menu filling; automatic focus suggestions are not claimed.

Open tabs read Firefox Mozilla JSONLZ4 selected entries and Chromium SNSS v1/v3
Session files. Latest normal sessions are used; closed tabs/windows, private Firefox
windows/tabs, unsupported schemes and URL credentials are excluded. Only URLs are
transferred, never cookies, page state, sessionStorage or POST data. Known encrypted
SNSS versions are rejected with an actionable export fallback. An “Open tabs HTML
file…” source imports a user-exported bookmark HTML list as tabs instead of bookmarks.
Accepted URLs are opened as background tabs in the explicit target context, with
URL/profile deduplication across Soulu windows and a 500-tab cap. Pending reads are
cancelled before opening. No automatic decrypt of encrypted session files is claimed.

Local drive and reparse-point checks restrict sources. SQLite source files are
never opened as SQLite connections: read handles lock the database and WAL as a
set before a temporary copy. Only that private copy may perform WAL recovery or
create SHM. Browser credentials use their own locked private snapshot. Snapshot
cleanup is scoped to operation lifetime; passwords remain only in memory until
vault encryption, with input buffers wiped after CSV processing. There are no
import network calls or logging of source content.

Work runs on the file-background thread. Cancellation checks interrupt reader and
write loops. Bookmarks commit as a category through the existing atomic writer;
history and passwords preserve earlier successful writes on cancellation or
failure. No full rollback is claimed. Concurrent imports and conflicting bookmark,
credential or profile mutations are guarded across the current browser windows.

## Verification status

Passed: JavaScript syntax checks, patch whitespace checks, 45 browser-driven UI and
HTML parsing checks against an explicitly labeled synthetic adapter. The revised
preview made no network requests. Eleven additional checks exercise the actual
field-query/fill expressions on a synthetic page, including sensitive fields,
cross-origin forms and changed field purpose; they do not execute the C++ bridge,
DPAPI, native menu or isolated-world integration. Seventeen screenshots show the combined form,
both dropdowns, inline profile creation, progress, success, partial failure, empty
discovery, HTML file, CSV consent, cancellation and dark/narrow layouts. These
results do not execute the new C++ backend.

Prepared but **not run**: isolated native adapter checks in browser_import_tests.cc,
including all nine discovery layouts, multiple profiles without Login Data, display
names, hierarchy, bookmark/history/credential repetition, target isolation, both
history epochs, Firefox's separate reader, CSV validation before writes, source sidecar preservation, direct DPAPI import,
autofill encryption/deduplication/isolation/payment exclusion, SNSS and JSONLZ4
current-tab parsing, closed/private tab exclusion and encrypted/truncated sessions. The harness requires a fresh empty AppData fixture root and
never uses real personal profiles.

After building the modified sources with the pinned Windows CEF toolchain:

```text
python scripts/test-browser-import-native.py PATH_TO_NEW_SOULU_EXE REPORT_JSON
```

Still required: actual native compilation; adapter checks on synthetic profiles
created by each current source browser; live/closed source locking and WAL cases;
access denial, corrupt/oversized inputs and disk-write failures; Windows file and
folder pickers; renderer/native cancellation timing; normal browsing during import;
restart persistence and UI visibility; independent profiles and multiple windows.
The UI demonstration cannot validate DPAPI, SQLite Windows sharing modes or native
bridge compilation. Full regression, commit, normal push to main and release are
deferred until explicit preview approval.

Schema references: [Mozilla Places](https://firefox-source-docs.mozilla.org/browser/places/index.html),
[Firefox history](https://firefox-source-docs.mozilla.org/browser/places/History.html),
[Chromium history types](https://chromium.googlesource.com/chromium/src/+/d9a8fa43a45782b61c2537577bb1d308ec27732a/components/history/core/browser/history_types.h).


Additional primary references: [Firefox Chrome migration](https://searchfox.org/firefox-main/source/browser/components/migration/ChromeProfileMigrator.sys.mjs),
[Chromium address schema](https://raw.githubusercontent.com/chromium/chromium/main/components/autofill/core/browser/webdata/addresses/address_autofill_table.cc),
[Chromium persisted field types](https://raw.githubusercontent.com/chromium/chromium/main/components/autofill/core/browser/field_types.h),
[Chromium session commands](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/sessions/core/session_service_commands.cc),
[Chromium session file versions](https://chromium.googlesource.com/chromium/src/+/refs/heads/main/components/sessions/core/command_storage_backend.cc),
[Firefox session paths](https://raw.githubusercontent.com/mozilla/gecko-dev/master/browser/components/sessionstore/SessionFile.sys.mjs).
