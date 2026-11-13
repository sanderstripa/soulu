# Chrome extensions in Settings

The Extensions section embeds a Chrome-style CEF BrowserView in the existing
Settings host. Installed extensions and the Chrome Web Store share the selected
normal profile's request context. The surface has no Sona message router.
Chromium handles package signatures, permission prompts, updates and removal.

For local installation, use Developer mode → Load unpacked in the embedded
manager and select a directory containing manifest.json. The Store button
navigates the embedded surface to the official Chrome Web Store. Neither path
uses downloaded extension code in the privileged Sona settings renderer.

The child is hidden for search, dialogs and other sections. Profile switching
closes it; reopening creates it with the new profile. Settings shutdown waits
for its Chrome window to close before destroying the parent document.

## Acceptance still required

This is an unverified integration, not a claim of complete Chrome compatibility.
Sona content tabs still use Alloy style. CEF documents that RequestContext-level
extension behavior can work there, but features requiring Chrome UI are not
supported: https://github.com/chromiumembedded/cef/issues/3859.

Before merging, build on Windows with the pinned CEF distribution and verify:

- The embedded native Chrome window sizes, focuses and closes correctly at
  100%, 125%, 150% and 200% Windows scaling.
- Load an unpacked MV3 fixture; verify its content script in an ordinary Sona
  tab, service worker, storage, disable/enable, reload and removal.
- Install Bitwarden from the Store; verify installation confirmation, unlock,
  autofill and action popup. Toolbar-dependent behavior is not implemented by
  this change and may require migrating content tabs to Chrome-style views.
- Restart Sona and confirm persistence and isolation between profiles.
- Switch settings sections, open dialogs, search and close the app while the
  manager or a Store permission prompt is open.

`node scripts/test-extensions-settings.cjs` checks the settings UI contract with
Playwright and a mocked CEF bridge. It does not verify native hosting or actual
extension installation. `node scripts/test-video-runtime.cjs` checks existing
JavaScript syntax and the translation runtime regression suite.
