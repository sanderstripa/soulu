# Native WebExtensions toolbar follow-up

Base: published Soulu Gecko Preview 4, source dac6a6d6ba0959ccb1664bb38114ee27a638baaa. Work stays in gecko-preview; the existing release remains immutable.

- Reuse Soulu action slots and pin controls. Firefox CustomizableUI owns pin persistence, so the native manager and Soulu do not maintain two pin stores.
- Use the native BrowserAction trigger for enabled checks, activeTab grants and onClicked. Use Firefox PanelPopup for the actual remote extension view; do not render extension HTML inside the Soulu application document.
- Permit action dispatch only from the installed shell, after recent trusted pointer/keyboard input and with a matching active tab/document generation.
- Respect each extension's native private-window permission.
- Update icons/badges from native action/widget/add-on events. Remove inherited 2s/3s polling from Gecko frontend copies.
- Establish Gecko ExtensionGuardSet restrictions for file:// before user extensions start. Local Soulu HTML has a privileged command bridge, so extension injection into local files must be denied even when the add-on has file access. This also makes add-on content scripts unavailable on other local HTML files; ordinary web content keeps its native permission model.

Targeted acceptance: actual action popup in extension process, actual content change through activeTab, badge updates, no website resize/reload, native onClicked, settings pin/unpin, private-window denial, install/disable/uninstall cleanup, stale/programmatic request rejection, dynamic/static injection denial on app files, signed-extension restart/pin persistence, Windows extracted ZIP launch. Signature enforcement stays enabled; unsigned test fixtures use only the native temporary-addon developer API in isolated test profiles.

Limits to document: page_action URL-bar controls and background-initiated action.openPopup are not covered by this first integration. Browser-action popups and onClicked are the acceptance scope. Physical GPU/DPI and external-account workflows remain manual.
