#pragma once
#include <windows.h>
#include <functional>
#include "include/cef_request_context.h"
#include "include/cef_client.h"
#include "include/cef_base.h"

namespace soulu {
// A Chrome-style surface in the Settings document. It intentionally has no
// Soulu bridge; Chromium owns package verification, permissions and persistence.
class ExtensionsPanel : public virtual CefBaseRefCounted {
 public:
  virtual void Place(const RECT& bounds) = 0;
  virtual void Navigate(bool store) = 0;
  virtual void Close(std::function<void()> done = {}) = 0;
};
CefRefPtr<CefClient> ExtensionDefaultClient();
void CloseExtensionWindows(std::function<void()> done);
CefRefPtr<ExtensionsPanel> CreateExtensionsPanel(HWND parent,
    CefRefPtr<CefRequestContext> context);
}
