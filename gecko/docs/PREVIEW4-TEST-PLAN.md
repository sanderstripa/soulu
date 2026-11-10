# Preview 4 acceptance

1. Syntax and targeted adapter checks after each meaningful component change.
2. Run real Gecko integration tests: navigation, tabs/reorder/restore, native downloads/actions/permission, Places and NSS/CSV/HTML imports, locked profiles/private data, reader and translation, untrusted bridge rejection.
3. Windows x64 build with original icon, rebuilt VPN helper and Rust DLL. Retain pinned external core binaries and licenses.
4. Final Windows browser checks: HTTPS, settings persistence, sessions, profile isolation, private history, network + cosmetic blocking and atomic filter updates, local real Xray/Sudoku tunnel, core-failure no-direct fallback, downloads and permissions. Check original UI geometry/screenshots, resizing, settings transitions and video interaction; record CPU/RAM.
5. ZIP, SHA256, extract into a path containing spaces and start the actual launcher using isolated LOCALAPPDATA. Packaging-only retries do not require repeating unchanged executable tests.

No real third-party account credentials are required. Public YouTube may present a bot/sign-in wall; record that as requiring manual verification, never a pass. Physical GPU/DPI combinations not available on CI remain manual checks. Public VPN-provider compatibility requires an available test key; local real-core routing does not prove every provider configuration.
