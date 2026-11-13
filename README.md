<p align="center"><img src="gecko/chrome/branding/sona-petals.png" width="150" alt="Sona"></p>
<h1 align="center">Sona</h1>

Sona is a Windows browser with its own interface, built-in VPN and ad blocking.

**Current release — Sona Preview 1.160.31**, powered by **Gecko 160.0**.

[Download for Windows x64](https://github.com/sanderstripa/soulu/releases/tag/sona-preview-1.160.31)

## Development

Gecko is the primary implementation starting with Sona Preview 1.160.22.
The default main branch contains the Gecko product. The gecko-preview branch preserves its development history.

The Chromium/CEF implementation is preserved in [cef-archive](https://github.com/sanderstripa/soulu/tree/cef-archive), including source, build scripts and history. It remains available for future development and tests.

## Features

- Adaptive tabs, tab overview, bookmarks, history and profiles.
- Inter typography and the blue wave Sona icon throughout the product.
- Built-in Xray and Sudoku VPN components.
- Native adblock-rust request filtering and cosmetic filtering.
- Independently downloadable filter lists. The native blocker core is updated with a tested browser release.
- Voluntary downloads of verified Sona updates.

## Build and verification

The release workflow is .github/workflows/build-sona26.yml.
It assembles the pinned official Gecko runtime, applies Sona chrome and branding, builds the Windows installer and verifies the installed application before publication.

The release contains the Windows installer and SHA256SUMS.txt.
Test reports, screenshots and build metadata remain in GitHub Actions artifacts.

## Local data

Sona profiles live in %LOCALAPPDATA%/Sona/Profiles.
Sona application data and update directories are redirected beneath %LOCALAPPDATA%/Sona.

Existing directories named Mozilla can originate from older Sona builds or other applications using Mozilla components. The installer preserves unrelated application data.

## Licensing

Gecko and other bundled open-source components retain their licenses and notices. See the source and packaged license files.
