/* CEF request compatibility only; transport and runtime are native Chromium. */
(() => {
  'use strict';
  if (location.protocol !== 'chrome:' || location.host !== 'webui-browser' ||
      window.top !== window || typeof globalThis.chrome?.send !== 'function') return;
  let sequence = 0;
  const pending = new Map();
  const stateListeners = new Set();
  window.souluChromiumOnState = callback => {
    stateListeners.add(callback);
    return () => stateListeners.delete(callback);
  };
  window.souluChromiumState = state => {
    for (const callback of stateListeners) callback(state);
    window.__souluEmit?.('state', state);
  };
  window.souluChromiumReply = (id, success, result) => {
    const item = pending.get(id);
    if (!item) return;
    pending.delete(id);
    clearTimeout(item.timeout);
    if (success) item.onSuccess?.(JSON.stringify(result));
    else item.onFailure?.(501, String(result));
  };
  window.cefQuery = ({request, persistent, onSuccess, onFailure}) => {
    // No CEF object exists. Existing Soulu scripts use this request signature.
    if (persistent) { onFailure?.(400, 'Persistent requests are not supported'); return; }
    let data;
    try { data = JSON.parse(request); }
    catch { onFailure?.(400, 'Malformed request'); return; }
    if (!data || typeof data.action !== 'string') {
      onFailure?.(400, 'Missing action'); return;
    }
    const id = String(++sequence);
    const timeout = setTimeout(() => {
      pending.delete(id);
      onFailure?.(408, 'Native Chromium request timed out');
    }, 15000);
    pending.set(id, {onSuccess, onFailure, timeout});
    try { chrome.send('soulu.request', [id, data.action, data.payload ?? null]); }
    catch (error) { window.souluChromiumReply(id, false, error.message); }
  };
  addEventListener('pagehide', () => {
    for (const item of pending.values()) clearTimeout(item.timeout);
    pending.clear();
    stateListeners.clear();
  }, {once: true});
})();
