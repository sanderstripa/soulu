#include "examples/soulu/chrome_tab_host.h"
#include <algorithm>
#include "include/views/cef_browser_view.h"
#include "include/views/cef_browser_view_delegate.h"
#include "include/views/cef_window.h"
#include "include/views/cef_window_delegate.h"
#include "include/views/cef_fill_layout.h"
#include "include/views/cef_panel.h"
#include "include/views/cef_layout.h"
#include "include/wrapper/cef_helpers.h"
namespace soulu { namespace {
class Host final:public ChromeTabHost,public CefWindowDelegate,public CefBrowserViewDelegate {
 public:
  explicit Host(HWND parent,std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> ready={}):parent_(parent),popup_ready_(std::move(ready)){}
  cef_runtime_style_t GetWindowRuntimeStyle() override{return CEF_RUNTIME_STYLE_CHROME;}
  cef_runtime_style_t GetBrowserRuntimeStyle() override{return CEF_RUNTIME_STYLE_CHROME;}
  ChromeToolbarType GetChromeToolbarType(CefRefPtr<CefBrowserView>) override{return CEF_CTT_NORMAL;}
  bool IsFrameless(CefRefPtr<CefWindow>) override{return true;}
  CefRect GetInitialBounds(CefRefPtr<CefWindow>) override{return CefRect(0,0,1000,700);}
  bool Start(CefRefPtr<CefClient> client,const std::string& url,const CefBrowserSettings& settings,
      CefRefPtr<CefDictionaryValue> extra,CefRefPtr<CefRequestContext> context){
    view_=CefBrowserView::CreateBrowserView(client,url,settings,extra,context,this);
    if(!view_)return false;
    window_=CefWindow::CreateTopLevelWindow(this);return window_!=nullptr;
  }
  void OnWindowCreated(CefRefPtr<CefWindow> window) override {
    window_=window;auto hwnd=window->GetWindowHandle();
    SetWindowLongPtrW(hwnd,GWL_STYLE,(GetWindowLongPtrW(hwnd,GWL_STYLE)&~(WS_POPUP|WS_CAPTION|WS_THICKFRAME))|WS_CHILD|WS_CLIPCHILDREN);
    SetParent(hwnd,parent_);window->AddChildView(view_);
    toolbar_=view_->GetChromeToolbar();
    if(toolbar_)window->AddChildView(toolbar_);
    Resize();if(visible_)window->Show();else window->Hide();
  }
  void OnWindowBoundsChanged(CefRefPtr<CefWindow>,const CefRect&) override{Resize();}
  bool CanClose(CefRefPtr<CefWindow>) override {
    auto browser=view_?view_->GetBrowser():nullptr;
    return !browser||browser->GetHost()->TryCloseBrowser();
  }
  void OnWindowDestroyed(CefRefPtr<CefWindow>) override{toolbar_=nullptr;view_=nullptr;window_=nullptr;}
  bool OnPopupBrowserViewCreated(CefRefPtr<CefBrowserView>,CefRefPtr<CefBrowserView> popup,bool devtools) override{
    if(devtools)return false;
    CefRefPtr<Host> host=new Host(parent_,popup_ready_);host->view_=popup;
    host->window_=CefWindow::CreateTopLevelWindow(host);
    if(!host->window_)return false;
    if(popup_ready_)popup_ready_(popup->GetBrowser(),host);
    return true;
  }
  void SetVisible(bool visible,bool activate) override {
    CEF_REQUIRE_UI_THREAD();visible_=visible;if(!window_)return;
    if(visible){if(!window_->IsVisible())window_->Show();if(activate)window_->Activate();}
    else window_->Hide();Resize();
  }
  void Close() override{if(view_&&view_->GetBrowser())view_->GetBrowser()->GetHost()->CloseBrowser(true);else if(window_)window_->Close();}
 private:
  void Resize(){
    if(!window_||!view_)return;const auto size=window_->GetSize();
    view_->SetBounds(CefRect(0,0,std::max(1,size.width),std::max(1,size.height)));
    // Chrome owns action models and popup anchoring; Soulu draws the visible
    // toolbar. Retain the real Chrome toolbar in the same Views hierarchy.
    if(toolbar_)toolbar_->SetBounds(CefRect(0,-40,std::max(1,size.width),40));
  }
  std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> popup_ready_;
  HWND parent_;bool visible_=false;CefRefPtr<CefWindow> window_;
  CefRefPtr<CefBrowserView> view_;CefRefPtr<CefView> toolbar_;
  IMPLEMENT_REFCOUNTING(Host);
};
}
CefRefPtr<ChromeTabHost> CreateChromeTab(HWND parent,CefRefPtr<CefClient> client,
    const std::string& url,const CefBrowserSettings& settings,CefRefPtr<CefDictionaryValue> extra,
    CefRefPtr<CefRequestContext> context,std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> popup_ready){
  CefRefPtr<Host> host=new Host(parent,std::move(popup_ready));if(!host->Start(client,url,settings,extra,context))return nullptr;return host;
}
}
