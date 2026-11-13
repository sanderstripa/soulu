Sona Gecko Preview 11

Fixes requested after Preview 10:
- Installation recognizes older uninstall leftovers (empty directories and the Gecko uninstaller), and repairs an owned partial installation even if Sona.exe is missing. Unrelated nonempty directories remain protected.
- The Gecko uninstaller schedules cleanup of its own executable and empty application directories after it exits. User profile data stays outside the application directory and is preserved.
- Automatic weather uses the standard Geolocation WebIDL API. Internal exceptions are logged for diagnosis; the Home interface receives readable weather messages.
- Nonempty bookmark folders use an asynchronous confirmation dialog in Sona. Confirmed deletion removes the subtree from Places; cancellation preserves it, and unrelated bookmarks are retained. Storage errors are no longer silently swallowed.

Publication requires Windows browser checks for real geolocation with a local provider fixture, weather responses and error presentation, actual folder deletion/cancellation, plus installer checks reproducing old uninstall leftovers and a missing launcher, profile preservation, and complete application-directory cleanup. Only the requested regressions are tested.
