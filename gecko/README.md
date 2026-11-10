# Soulu Preview 1.160.24

The primary Soulu implementation uses Gecko 160.0 on Windows x64.

Install Soulu-1.160.24-Preview-Setup-win64.exe from the normal GitHub release.
Program files are installed beneath %LOCALAPPDATA%/Programs/Soulu.
Profiles remain beneath %LOCALAPPDATA%/Soulu/Profiles. Application data and engine update directories are redirected into the Soulu data tree.

The primary source branch is main. The gecko-preview branch preserves development history.
The CEF implementation and its original build environment are preserved in cef-archive.

## Release build

The workflow .github/workflows/build-soulu24.yml performs these operations.

1. Restore the integrity-checked baseline application assets.
2. Download and verify the complete official Gecko 160.0 runtime.
3. Apply Soulu bootstrap, interface, Inter typography and blue wave branding.
4. Compile the launcher and installer.
5. Verify the installed browser, filter updates, private windows, profile-preserving upgrades and repeated native launches.
6. Publish the installer and checksum after acceptance succeeds.

The native adblock-rust core ships with the browser. EasyList, EasyPrivacy and RU AdList can be downloaded, compiled and installed separately. Failed filter updates preserve the active rules and cache.

Build evidence and metadata are retained in GitHub Actions artifacts.
