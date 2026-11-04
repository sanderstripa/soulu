Soulu Gecko Preview 10

Based on the verified Preview 8 runtime and source, with targeted fixes:
- Browser import uses a dedicated Soulu dialog from both first-run setup and Settings, with browser/profile selection, data categories and actual completion results. The native engine migrators handle the data without opening Firefox windows.
- The native migrators retain all supported data categories. Protected Chromium passwords use the engine's supported CSV workflow where direct access is unavailable.
- Firefox installation/registration helpers, updater and default-browser agent are excluded. Only Soulu is installed and registered.
- Synchronous native filter initialization is scheduled after the real Soulu window has composed, rather than blocking the hidden startup window. No fallback exposes Firefox's toolbar.
- Launcher, installer, Settings, updater and build manifest identify Preview 10.

The Windows publication job requires actual migration of synthetic Chrome and Edge bookmarks, history and autofill, native password import, opening Soulu import from welcome and Settings, startup below seven seconds on the runner, first-frame and single-window checks, and clean installer/upgrade/removal checks. The reports attached to this release record the measured results; hardware-specific startup times can vary.
