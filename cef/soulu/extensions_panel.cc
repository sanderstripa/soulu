#include "examples/soulu/extensions_panel.h"
#include "include/cef_client.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_browser_view_delegate.h"
#include "include/views/cef_window.h"
#include "include/views/cef_fill_layout.h"
#include "include/views/cef_window_delegate.h"
#include "include/wrapper/cef_helpers.h"

namespace soulu {
namespace {
class Panel final : public ExtensionsPanel, public CefClient,
    public CefLifeSpanHandler, public CefWindowDelegate,
    public CefBrowserViewDelegate {
 public:
  explicit Panel(HWND parent) : parent_(parent) {}
  CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler() override { return this; }
  cef_runtime_style_t GetWindowRuntimeStyle() override { return CEF_RUNTIME_STYLE_CHROME; }
  cef_runtime_style_t GetBrowserRuntimeStyle() override { return CEF_RUNTIME_STYLE_CHROME; }
  bool IsFrameless(CefRefPtr<CefWindow>) override { return true; }
  CefRect GetInitialBounds(CefRefPtr<CefWindow>) override { return CefRect(0,0,800,500); }
  bool Start(CefRefPtr<CefRequestContext> context) {
    CEF_REQUIRE_UI_THREAD();
    CefBrowserSettings settings;
    auto extra=CefDictionaryValue::Create();extra->SetBool("souluExtensionsSurface",true);
    view_=CefBrowserView::CreateBrowserView(this,"chrome://extensions/",settings,extra,context,this);
    if(view_) window_=CefWindow::CreateTopLevelWindow(this);
    if(!window_){view_=nullptr;return false;}
    return true;
  }
  void OnWindowCreated(CefRefPtr<CefWindow> window) override {
    window_=window;
    if(closing_||!IsWindow(parent_)){window->Close();return;}
    // Keep the native Chrome surface within the existing Settings panel, with
    // its lifetime independent of the Alloy settings renderer's bridge.
    const auto hwnd=window->GetWindowHandle();
    SetWindowLongPtrW(hwnd,GWL_STYLE,(GetWindowLongPtrW(hwnd,GWL_STYLE)&~(WS_POPUP|WS_CAPTION|WS_THICKFRAME))|WS_CHILD|WS_CLIPCHILDREN);
    SetParent(hwnd,parent_);
    window->SetToFillLayout();window->AddChildView(view_);
    Place(bounds_);
  }
  bool CanClose(CefRefPtr<CefWindow>) override { return !browser_||browser_->GetHost()->TryCloseBrowser(); }
  void OnWindowDestroyed(CefRefPtr<CefWindow>) override {
    window_=nullptr;view_=nullptr;auto done=std::move(done_);if(done)done();
  }
  void OnAfterCreated(CefRefPtr<CefBrowser> browser) override {
    browser_=browser;if(closing_)browser->GetHost()->CloseBrowser(true);
    else if(store_)Navigate(true);
  }
  void OnBeforeClose(CefRefPtr<CefBrowser>) override {
    browser_=nullptr;if(window_)window_->Close();
  }
  void Place(const RECT& bounds) override {
    CEF_REQUIRE_UI_THREAD();bounds_=bounds;
    if(!window_||closing_)return;
    const auto hwnd=window_->GetWindowHandle();
    const bool visible=bounds.right>bounds.left&&bounds.bottom>bounds.top;
    if(!visible){ShowWindow(hwnd,SW_HIDE);return;}
    SetWindowPos(hwnd,HWND_TOP,bounds.left,bounds.top,bounds.right-bounds.left,
        bounds.bottom-bounds.top,SWP_NOACTIVATE|SWP_FRAMECHANGED|SWP_SHOWWINDOW);
  }
  void Navigate(bool store) override {
    CEF_REQUIRE_UI_THREAD();
    store_=store;
    if(browser_&&!closing_)browser_->GetMainFrame()->LoadURL(store?
        "https://chromewebstore.google.com/category/extensions":"chrome://extensions/");
  }
  void Close(std::function<void()> done = {}) override {
    CEF_REQUIRE_UI_THREAD();if(done)done_=std::move(done);if(closing_)return;closing_=true;
    if(window_)ShowWindow(window_->GetWindowHandle(),SW_HIDE);
    if(browser_)browser_->GetHost()->CloseBrowser(true);
    else if(window_)window_->Close();
    else {auto complete=std::move(done_);if(complete)complete();}
  }
 private:
  HWND parent_;RECT bounds_={};bool closing_=false,store_=false;
  std::function<void()> done_;
  CefRefPtr<CefBrowser> browser_;CefRefPtr<CefBrowserView> view_;CefRefPtr<CefWindow> window_;
  IMPLEMENT_REFCOUNTING(Panel);
};
}
CefRefPtr<ExtensionsPanel> CreateExtensionsPanel(HWND parent,CefRefPtr<CefRequestContext> context) {
  CefRefPtr<Panel> panel=new Panel(parent);
  if(!panel->Start(context))return nullptr;
  return panel;
}
}
