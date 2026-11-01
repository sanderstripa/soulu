#include "examples/soulu/extensions_panel.h"
#include "examples/soulu/engine_version.h"
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
    if(!visible){window_->Hide();return;}
    // Show through Views as well as Win32: native SW_SHOWWINDOW alone leaves
    // the Aura compositor hidden and the settings backdrop visible underneath.
    window_->Show();
    SetWindowPos(hwnd,HWND_TOP,bounds.left,bounds.top,bounds.right-bounds.left,
        bounds.bottom-bounds.top,SWP_NOACTIVATE|SWP_FRAMECHANGED|SWP_SHOWWINDOW);
  }
  void Navigate(bool store) override {
    CEF_REQUIRE_UI_THREAD();
    store_=store;
    if(browser_&&!closing_){
      StoreCompatibility(store);
      browser_->GetMainFrame()->LoadURL(store?
        "https://chromewebstore.google.com/category/extensions":"chrome://extensions/");
    }
  }
  void Close(std::function<void()> done = {}) override {
    CEF_REQUIRE_UI_THREAD();if(done)done_=std::move(done);if(closing_)return;closing_=true;
    if(window_)window_->Hide();
    if(browser_)browser_->GetHost()->CloseBrowser(true);
    else if(window_)window_->Close();
    else {auto complete=std::move(done_);if(complete)complete();}
  }
 private:
  void StoreCompatibility(bool enabled) {
    // Web Store checks UA Client Hints in addition to webstorePrivate. Limit
    // Chrome compatibility metadata to this catalog surface. Chromium still
    // verifies the original package and displays its native permission prompt.
    auto params=CefDictionaryValue::Create();
    params->SetString("userAgent", "");
    if(enabled){
      const auto major=std::to_string(CHROME_VERSION_MAJOR),full=EngineVersion(4,4);
      params->SetString("userAgent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"+major+".0.0.0 Safari/537.36");
      auto metadata=CefDictionaryValue::Create();
      for(const auto& field:{std::string("brands"),std::string("fullVersionList")}){
        auto brands=CefListValue::Create();
        for(const auto* name:{"Chromium","Google Chrome"}){
          auto brand=CefDictionaryValue::Create();brand->SetString("brand",name);
          brand->SetString("version",field=="brands"?major:full);brands->SetDictionary(brands->GetSize(),brand);
        }
        metadata->SetList(field,brands);
      }
      metadata->SetString("fullVersion",full);metadata->SetString("platform","Windows");
      metadata->SetString("platformVersion","10.0.0");metadata->SetString("architecture","x86");
      metadata->SetString("model","");metadata->SetBool("mobile",false);
      metadata->SetString("bitness","64");metadata->SetBool("wow64",false);
      params->SetDictionary("userAgentMetadata",metadata);
    }
    browser_->GetHost()->ExecuteDevToolsMethod(0,"Emulation.setUserAgentOverride",params);
  }
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
