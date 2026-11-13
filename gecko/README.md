# Sona Preview 1.160.26

The primary Sona implementation uses Gecko 160.0 on Windows x64.

Install Sona-1.160.26-Preview-Setup-win64.exe from the normal GitHub release.
Program files are installed beneath %LOCALAPPDATA%/Programs/Sona.
Profiles remain beneath %LOCALAPPDATA%/Sona/Profiles. Application data and engine update directories are redirected into the Sona data tree.

The primary source branch is main. The gecko-preview branch preserves development history.
The CEF implementation and its original build environment are preserved in cef-archive.

## Release build

The workflow .github/workflows/build-sona24.yml performs these operations.

1. Restore the integrity-checked baseline application assets.
2. Download and verify the complete official Gecko 160.0 runtime.
3. Apply Sona bootstrap, interface, Inter typography and blue wave branding.
4. Compile the launcher and installer.
5. Verify the installed browser, filter updates, private windows, profile-preserving upgrades and repeated native launches.
6. Publish the installer and checksum after acceptance succeeds.

The native adblock-rust core ships with the browser. EasyList, EasyPrivacy and RU AdList can be downloaded, compiled and installed separately. Failed filter updates preserve the active rules and cache.

Build evidence and metadata are retained in GitHub Actions artifacts.
