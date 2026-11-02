#pragma once
#include <windows.h>
#include <functional>
#include "include/cef_browser.h"
#include "include/cef_client.h"
#include "include/cef_request_context.h"
namespace soulu {
class ChromeTabHost:public virtual CefBaseRefCounted {
 public:
  virtual void SetVisible(bool visible,bool activate)=0;
  // Anchor a Chromium-owned extension action bubble to the shell button.
  virtual void ArmActionPopup(const CefRect& anchor)=0;
  virtual void Close()=0;
};
CefRefPtr<ChromeTabHost> CreateChromeTab(HWND parent,CefRefPtr<CefClient> client,
    const std::string& url,const CefBrowserSettings& settings,
    CefRefPtr<CefDictionaryValue> extra,CefRefPtr<CefRequestContext> context,
    std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> popup_ready={},
    std::function<void()> failed={});
}
