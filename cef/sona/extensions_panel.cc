#include "examples/sona/extensions_panel.h"
#include "examples/sona/engine_version.h"
#include "include/cef_client.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_browser_view_delegate.h"
#include "include/views/cef_window.h"
#include "include/views/cef_fill_layout.h"
#include "include/views/cef_window_delegate.h"
#include "include/wrapper/cef_helpers.h"
#include <map>
#include <vector>
#include <algorithm>

namespace sona {
namespace {
class Panel;
std::vector<Panel*> panels;
class Panel final : public ExtensionsPanel, public CefClient,
    public CefLifeSpanHandler, public CefWindowDelegate,
    public CefBrowserViewDelegate {
 public:
  explicit Panel(HWND parent) : parent_(parent) {}
  ~Panel() override {panels.erase(std::remove(panels.begin(),panels.end(),this),panels.end());}
  bool Owns(CefRefPtr<CefRequestContext> context) const {return !closing_&&context_&&context_->IsSharingWith(context);}
  void Adopt(CefRefPtr<CefBrowser> browser){popups_[browser->GetIdentifier()]=browser;if(closing_)browser->GetHost()->CloseBrowser(true);}
  void PopupClosed(CefRefPtr<CefBrowser> browser){popups_.erase(browser->GetIdentifier());CompleteClose();}
  CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler() override { return this; }
  cef_runtime_style_t GetWindowRuntimeStyle() override { return CEF_RUNTIME_STYLE_CHROME; }
  cef_runtime_style_t GetBrowserRuntimeStyle() override { return CEF_RUNTIME_STYLE_CHROME; }
  bool IsFrameless(CefRefPtr<CefWindow>) override { return true; }
  CefRect GetInitialBounds(CefRefPtr<CefWindow>) override { return CefRect(0,0,800,500); }
  bool Start(CefRefPtr<CefRequestContext> context) {
    CEF_REQUIRE_UI_THREAD();
    context_=context;
    CefBrowserSettings settings;
    auto extra=CefDictionaryValue::Create();extra->SetBool("sonaExtensionsSurface",true);
    view_=CefBrowserView::CreateBrowserView(this,"chrome://extensions/",settings,extra,context,this);
    if(view_) window_=CefWindow::CreateTopLevelWindow(this);
    if(!window_){view_=nullptr;return false;}
    panels.push_back(this);return true;
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
    window_=nullptr;view_=nullptr;CompleteClose();
  }
  void OnAfterCreated(CefRefPtr<CefBrowser> browser) override {
    // Store installations and extensions may create welcome/options windows.
    // Their callbacks use the same client: never replace the manager browser.
    if(!primary_created_){primary_created_=true;browser_=browser;}
    else popups_[browser->GetIdentifier()]=browser;
    if(closing_)browser->GetHost()->CloseBrowser(true);
    else if(browser_&&browser_->IsSame(browser)&&store_)Navigate(true);
  }
  void OnBeforeClose(CefRefPtr<CefBrowser> browser) override {
    if(browser_&&browser_->IsSame(browser)){
      browser_=nullptr;if(window_)window_->Close();
    }else popups_.erase(browser->GetIdentifier());
    CompleteClose();
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
    // Close a snapshot; callbacks can erase entries while the requests run.
    std::vector<CefRefPtr<CefBrowser>> closing;
    for(const auto& [id,browser]:popups_)closing.push_back(browser);
    if(browser_)closing.push_back(browser_);
    for(const auto& browser:closing)browser->GetHost()->CloseBrowser(true);
    if(!browser_&&window_)window_->Close();
    CompleteClose();
  }
 private:
  void CompleteClose(){
    if(!closing_||browser_||window_||!popups_.empty())return;
    auto complete=std::move(done_);if(complete)complete();
  }
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
  HWND parent_;RECT bounds_={};bool closing_=false,store_=false,primary_created_=false;
  CefRefPtr<CefRequestContext> context_;
  std::map<int,CefRefPtr<CefBrowser>> popups_;
  std::function<void()> done_;
  CefRefPtr<CefBrowser> browser_;CefRefPtr<CefBrowserView> view_;CefRefPtr<CefWindow> window_;
  IMPLEMENT_REFCOUNTING(Panel);
};

// Chrome UI-created tabs/windows do not necessarily inherit a CefClient. CEF
// explicitly leaves such browsers unmanaged unless GetDefaultClient supplies
// one, and unmanaged windows block CefShutdown after the Sona host closes.
class DefaultClient final:public CefClient,public CefLifeSpanHandler {
 public:
  CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler() override{return this;}
  void OnAfterCreated(CefRefPtr<CefBrowser> browser) override {
    Entry entry;entry.browser=browser;
    const auto context=browser->GetHost()->GetRequestContext();
    for(auto* panel:panels)if(panel->Owns(context)){entry.owner=panel;panel->Adopt(browser);break;}
    browsers_[browser->GetIdentifier()]=entry;
    if(closing_)browser->GetHost()->CloseBrowser(true);
  }
  void OnBeforeClose(CefRefPtr<CefBrowser> browser) override {
    const auto it=browsers_.find(browser->GetIdentifier());
    CefRefPtr<Panel> owner;
    if(it!=browsers_.end()){owner=it->second.owner;browsers_.erase(it);}
    if(owner)owner->PopupClosed(browser);
    Complete();
  }
  void Close(std::function<void()> done){
    CEF_REQUIRE_UI_THREAD();closing_=true;done_=std::move(done);
    std::vector<CefRefPtr<CefBrowser>> snapshot;
    for(const auto& [id,entry]:browsers_)snapshot.push_back(entry.browser);
    for(const auto& browser:snapshot)browser->GetHost()->CloseBrowser(true);
    Complete();
  }
 private:
  void Complete(){if(!closing_||!browsers_.empty())return;auto done=std::move(done_);if(done)done();}
  struct Entry{CefRefPtr<CefBrowser> browser;CefRefPtr<Panel> owner;};
  std::map<int,Entry> browsers_;bool closing_=false;std::function<void()> done_;
  IMPLEMENT_REFCOUNTING(DefaultClient);
};
CefRefPtr<DefaultClient> Default(){static CefRefPtr<DefaultClient> client=new DefaultClient();return client;}
}
CefRefPtr<CefClient> ExtensionDefaultClient(){return Default();}
void CloseExtensionWindows(std::function<void()> done){Default()->Close(std::move(done));}
CefRefPtr<ExtensionsPanel> CreateExtensionsPanel(HWND parent,CefRefPtr<CefRequestContext> context) {
  CefRefPtr<Panel> panel=new Panel(parent);
  if(!panel->Start(context))return nullptr;
  return panel;
}
}
