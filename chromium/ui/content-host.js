// Chromium's own Webium content-region keeps each tab's native surface attached.
import {ContentRegionElement} from '/content_region.js';
import {browserProxyFactory} from '/browser.mojom-webui.js';
import {TrackedElementManager} from 'chrome://resources/js/tracked_element/tracked_element_manager.js';

const region = new ContentRegionElement();
region.id = 'souluChromiumContent';
document.body.append(region);
const attached = new Set();
const update = state => {
  const live = new Set(state.tabs.map(tab => tab.guestTabId));
  for (const id of attached) {
    if (!live.has(id)) { region.removeTab(id); attached.delete(id); }
  }
  for (const tab of state.tabs) {
    if (!attached.has(tab.guestTabId)) {
      region.createWebView(tab.guestTabId, tab.active);
      attached.add(tab.guestTabId);
    } else if (tab.active && region.activeWebview?.tabId !== tab.guestTabId) {
      region.activateTab(tab.guestTabId);
    }
  }
};
window.souluChromiumOnState(update);
window.browserShell.getState().then(update).catch(console.error);

const callback = browserProxyFactory.getInstance().callbackRouter;
callback.setFocusToLocationBar.addListener(() => window.__souluEmit?.('focusAddress', true));
callback.onFullscreenModeChanged.addListener(fullscreen => {
  document.body.dataset.fullscreen = String(fullscreen);
});
// Native Chromium permission and menu anchors must track original Soulu controls.
const tracker = TrackedElementManager.getInstance();
for (const [selector, name] of [
  ['#classicPageMenu', 'kLocationIconElementId'],
  ['#backButton', 'kToolbarBackButtonElementId'],
  ['#souluChromiumContent', 'kContentsContainerViewElementId'],
]) {
  const element = document.querySelector(selector);
  if (element) tracker.startTracking(element, name);
}
