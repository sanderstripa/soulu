# Soulu Gecko Preview 8 — Windows x64

Run `Soulu-Gecko-Preview-8-Setup-win64.exe`. The installer uses the existing Soulu CEF installer interface and installs the independent Gecko product under `%LOCALAPPDATA%\Programs\SouluGecko`. Close running Soulu Gecko instances before installation. Firefox and CEF do not need to be installed. The uninstaller removes the program and keeps profiles.

Existing Gecko profiles are reused. User data remains in `%LOCALAPPDATA%\SouluGecko\Profiles`, separately from Firefox and Soulu CEF. Existing Soulu Gecko profiles are reused; they are not reset and do not repeat first-run onboarding. New profiles receive the original Soulu welcome layout.

The original Soulu interface uses Firefox gBrowser/SessionStore, Places, NSS/LoginManager, native Downloads, permission prompts, Reader View and local translation. Xray/Sudoku and the Rust blocker are the accepted Preview 4 binaries, unchanged. Fission, the sandbox, HTTPS checks and extension signature enforcement remain enabled.

Optional local voice input uses the isolated SouluSpeech helper, adapted from Soulu CEF, and a checksum-pinned multilingual Whisper model. Audio is not uploaded or saved as a recording. Recognized text is placed in Home search for review before submission. Physical microphone/acoustic checks require the user's Windows device.

YouTube voice-over is a bundled native built-in component using the unchanged, AMO-signed VOT 1.12.6 package. It is initialized by default, preserves an existing disabled state, and is managed in Settings → Translation rather than the user-extension list. VOT uses Yandex/VOT servers for voice-over; it is distinct from the local page translator. Its compact controls live on supported videos. Actual public YouTube voice-over is not proven by successful installation alone; consult the release report.

The About page checks only Gecko preview assets in the official Soulu GitHub repository and can download/verify a Windows x64 installer or ZIP. It does not replace files automatically. Independent package signing and transactional automatic installation remain future work.

Default-browser registration is per current Windows user and only after pressing the corresponding button. Windows controls the final HTTP/HTTPS choice. External links reuse the chosen Soulu profile through authenticated loopback remoting; the Windows system proxy is never changed.

Firefox WebExtensions cannot inject content scripts into local file pages, protecting Soulu's application bridge. This also restricts scripts on other local HTML files. Ordinary HTTP/HTTPS extension permissions remain native.

Mozilla licenses remain available through `about:license` and the bundled runtime. VOT and Whisper licenses/provenance accompany their components. See release notes and included reports for confirmed tests and limitations.
