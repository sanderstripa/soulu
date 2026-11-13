# Sona Preview 1.160.26

- Remove the reserved toolbar space and hide shell overlays during native DOM fullscreen, including iframe video players.
- Restore the toolbar and its previous geometry automatically on fullscreen exit.
- Keep ordinary browser fullscreen, tab animations, window maximization and normal layouts unchanged.

# Sona Preview 1.160.25

- Native error artwork and built-in page accents use Sona branding and Inter.
- Inherited chatbot integration and its context-menu shortcuts are disabled on existing and new profiles.
- Standard Gecko User-Agent compatibility token restored: fixes the basic Google HTML response. Sona remains the product identifier.
- Logo-free home layout centers the search form in the available page viewport, including resized windows.
- Security/certificate checks, tab animations, profiles and VPN behavior are retained.
- Engine namespaces, compatibility tokens and required third-party license notices remain intact.

# Sona Preview 1.160.24

- Remove the rectangular hover background from installer text actions.
- Enlarge the optical Windows icon variant and refresh Sona-owned shortcut icons.
- Add the Home logo toggle at the bottom of Startup and home. Center the search field when the logo is hidden.

# Sona Preview 1.160.23

- Restore the original blue petal logo and enlarge its home-page presentation by 15 percent.
- Apply Inter typography, Sona light and dark palettes, and matching caption glyphs to the installer.
- Preserve Gecko 160.0 and the existing browser behavior.

# Sona Preview 1.160.22

- Promote Gecko to the primary implementation and preserve CEF in the cef-archive branch.
- Update the engine to Gecko 160.0.
- Introduce the blue wave product icon throughout the application and Windows installer.
- Align right caption controls with the left toolbar inset.
- Separate browser, Adblock and VPN component information in About Sona.
- Expose real filter downloads and atomic installation from the Adblock section. The native blocker core remains part of the tested browser build.
- Revise first-window presentation and isolate engine application directories under Sona.
- Use the 1.engine.build version format and publish this Preview as a normal release.

# Sona Beta 1.0.76

- Stabilize Chrome Views page bounds and skip redundant visibility/layout changes introduced with extension support.
- Keep nested page scrolling from moving the native page viewport.
- Anchor Chromium extension action popups to their Sona toolbar button, cap them at 800×600 DIP, and dismiss on outside click, Escape, tab switch or application deactivation.
- Preserve extension toolbar buttons when the installed extension list has not changed.
- Retain a private native toolbar cursor and apply cursor changes only while the pointer is over that toolbar.
- Forward light/dark/system appearance to Chromium profiles so supported sites receive the browser color scheme.
- Smooth settings, tab overview and bookmark sidebar transitions; retain the shell surface for bookmark exit animations.

Windows build and only the reported UI and Bitwarden regressions plus build/installer integrity checks run in GitHub Actions. Unrelated feature suites are not repeated for this hotfix, as requested. Physical YouTube playback, GPU/DPI and real Bitwarden account use require desktop verification; they are not claimed as manually verified here.
