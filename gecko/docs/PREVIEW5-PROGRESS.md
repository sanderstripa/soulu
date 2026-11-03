# Preview 5 — working checkpoint

Base: Preview 4 Update 1, source 5e183785ed80294ea2cc61986eeb65662d46c50c. Only gecko-preview is modified.

Implemented, pending final Windows acceptance:

- Places bookmark updates include mandatory index; imported native roots remain separate.
- Explicit grid columns for faviconless address suggestions.
- Compact page-translation panel, aligned labels, grouped buttons; local Firefox translator preserved.
- Native PageThumbs images for overview and inactive-tab hover, memory-only per window, bounded cache, event driven.
- Idle preparation of existing settings document, without displaying its overlay before a user requests it.
- Import actions in a 2×2 grid, readable operation messages, close Soulu dialog before opening native wizard.
- Remove native split-view padding; apply Soulu blue to native permission/password/migration controls.
- Native Windows window grouping set to Soulu alongside original application icon.

Local checks before the workspace restart passed actual bookmark edits/move, nonblank native thumbnail pixels, overview image rendering, readable faviconless suggestion geometry, 12 settings sections, content-edge alignment and bookmark/favorite persistence after restart. Repeat changed scenarios on Windows before release.

Not yet complete: first-run flow, Windows default registration/external URL routing, voice input, VOT integration/playback, GitHub update UI, typography comparison, Windows DPI/startup visual verification. No Preview 5 release is claimed at this checkpoint.


Second implementation checkpoint:

- Per-user HTTP/HTTPS registration invokes Windows Default Apps only on a trusted click. No UserChoice overrides. Authenticated loopback remoting reuses an existing Soulu profile and rejects invalid tokens/URL schemes.
- Existing CEF local Whisper/microphone implementation adapted into a small standalone CPU-only helper. Pinned multilingual model, no audio upload or disk recording. Recognition inserts text without submitting it.
- VOT 1.12.6 Firefox XPI is unchanged, SHA-pinned and verified with Firefox signature enforcement. Installation is opt-in after explicit permission/service disclosure. Optional data collection is not automatically granted. End-to-end public YouTube voice-over remains a separate real-playback gate.
- Original welcome layout restored for new profiles, persisted language/theme/privacy/import/VPN/default-browser steps. Existing profile files skip automatic onboarding.
- About page checks only official Gecko-channel GitHub release assets; downloads are voluntary, GitHub digest and archive channel/platform are verified. Automatic file replacement and independent signed update manifests are deferred; download UI states this explicitly.

First Windows corrected-component candidate passed run 41696851891, including the original targeted defect checks and native extension suite. New speech/VOT/onboarding/registration/update integrations need their own Windows acceptance and are not declared complete yet.
