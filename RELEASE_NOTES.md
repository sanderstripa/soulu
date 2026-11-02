# Soulu Beta 1.0.76

- Stabilize Chrome Views page bounds and skip redundant visibility/layout changes introduced with extension support.
- Keep nested page scrolling from moving the native page viewport.
- Anchor Chromium extension action popups to their Soulu toolbar button, cap them at 800×600 DIP, and dismiss on outside click, Escape, tab switch or application deactivation.
- Preserve extension toolbar buttons when the installed extension list has not changed.
- Retain a private native toolbar cursor and apply cursor changes only while the pointer is over that toolbar.
- Forward light/dark/system appearance to Chromium profiles so supported sites receive the browser color scheme.
- Smooth settings, tab overview and bookmark sidebar transitions; retain the shell surface for bookmark exit animations.

Windows build and focused UI/extension, layout, motion and installer checks run in GitHub Actions. Unrelated feature suites are not repeated for this hotfix, as requested. Physical YouTube playback, GPU/DPI and real Bitwarden account use require desktop verification; they are not claimed as manually verified here.
