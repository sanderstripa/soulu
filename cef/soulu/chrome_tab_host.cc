#include "examples/soulu/chrome_tab_host.h"
#include <algorithm>
#include "include/cef_cookie.h"
#include "include/cef_task.h"
#include "include/base/cef_logging.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_browser_view_delegate.h"
#include "include/views/cef_window.h"
#include "include/views/cef_window_delegate.h"
#include "include/views/cef_fill_layout.h"
#include "include/views/cef_panel.h"
#include "include/views/cef_layout.h"
#include "include/wrapper/cef_helpers.h"
namespace soulu { namespace {
class Task final:public CefTask {
 public:explicit Task(std::function<void()> done):done_(std::move(done)){}void Execute()override{done_();}
 private:std::function<void()> done_;IMPLEMENT_REFCOUNTING(Task);
};
class Completion final:public CefCompletionCallback {
 public:explicit Completion(std::function<void()> done):done_(std::move(done)){}void OnComplete()override{done_();}
 private:std::function<void()> done_;IMPLEMENT_REFCOUNTING(Completion);
};
class Host final:public ChromeTabHost,public CefWindowDelegate,public CefBrowserViewDelegate {
 public:
  explicit Host(HWND parent,std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> ready={}):parent_(parent),popup_ready_(std::move(ready)){}
  cef_runtime_style_t GetWindowRuntimeStyle() override{return CEF_RUNTIME_STYLE_CHROME;}
  cef_runtime_style_t GetBrowserRuntimeStyle() override{return CEF_RUNTIME_STYLE_CHROME;}
  ChromeToolbarType GetChromeToolbarType(CefRefPtr<CefBrowserView>) override{return CEF_CTT_NORMAL;}
  bool IsFrameless(CefRefPtr<CefWindow>) override{return true;}
  CefRect GetInitialBounds(CefRefPtr<CefWindow>) override{return CefRect(0,0,1000,700);}
  void SetFailure(std::function<void()> failed){failed_=std::move(failed);}
  bool Start(CefRefPtr<CefClient> client,const std::string& url,const CefBrowserSettings& settings,
      CefRefPtr<CefDictionaryValue> extra,CefRefPtr<CefRequestContext> context){
    if(!context)context=CefRequestContext::GetGlobalContext();
    CefRefPtr<Host> self=this;
    // Unlike CreateBrowser(), CreateBrowserView() requires an initialized
    // request context. Cookie storage completion is the public async barrier.
    return context->GetCookieManager(new Completion([self,client,url,settings,extra,context]{
      // Never create a synchronous Chrome Views widget inside a keyboard,
      // router or cookie-completion callback. Let that callback unwind first.
      CefPostTask(TID_UI,new Task([self,client,url,settings,extra,context]{
        if(self->closing_)return;
        self->view_=CefBrowserView::CreateBrowserView(client,url,settings,extra,context,self);
        if(self->view_)self->window_=CefWindow::CreateTopLevelWindow(self);
        if(!self->view_||!self->window_){LOG(ERROR)<<"Chrome tab host creation failed after context initialization";if(self->failed_)self->failed_();}
      }));
    }))!=nullptr;
  }
  void OnWindowCreated(CefRefPtr<CefWindow> window) override {
    window_=window;auto hwnd=window->GetWindowHandle();
    SetWindowLongPtrW(hwnd,GWL_STYLE,(GetWindowLongPtrW(hwnd,GWL_STYLE)&~(WS_POPUP|WS_CAPTION|WS_THICKFRAME))|WS_CHILD|WS_CLIPCHILDREN);
    SetParent(hwnd,parent_);window->AddChildView(view_);
    toolbar_=view_->GetChromeToolbar();
    // The Chrome toolbar is already owned by BrowserView. Reparenting it
    // detaches Chromium's browser model; retain it in its original hierarchy.
    Resize();SetVisible(visible_,false);
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
    // Keep Chromium's content view visibility in sync with the Win32 child.
    // Hiding the native container alone leaves the BrowserView logically shown.
    if(view_&&view_->IsVisible()!=visible)view_->SetVisible(visible);
    if(visible){if(!window_->IsVisible())window_->Show();if(activate&&!focusing_)FocusNativeContent();}
    else window_->Hide();Resize();
    // A Chrome widget can raise itself when shown. Content must stay below
    // the custom toolbar, page glass and the owner's native resize border.
    SetWindowPos(window_->GetWindowHandle(),HWND_BOTTOM,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE);
  }
  void Close() override{closing_=true;if(view_&&view_->GetBrowser())view_->GetBrowser()->GetHost()->CloseBrowser(true);else if(window_)window_->Close();}
 private:
  struct NativeFocusTarget {HWND window=nullptr;LONGLONG area=0;};
  static BOOL CALLBACK FindRenderer(HWND window,LPARAM data){
    wchar_t name[64]={};GetClassNameW(window,name,64);
    if(IsWindowVisible(window)&&lstrcmpW(name,L"Chrome_RenderWidgetHostHWND")==0){
      RECT bounds={};if(GetClientRect(window,&bounds)){
        const LONGLONG area=static_cast<LONGLONG>(bounds.right-bounds.left)*(bounds.bottom-bounds.top);
        auto* target=reinterpret_cast<NativeFocusTarget*>(data);
        if(area>target->area){target->window=window;target->area=area;}
      }
    }
    return TRUE;
  }
  void FocusNativeContent(){
    focusing_=true;window_->Activate();
    if(auto browser=view_?view_->GetBrowser():nullptr)browser->GetHost()->SetFocus(true);
    // A Views widget reparented to a foreign Win32 host cannot become the
    // top-level active HWND. Forward keyboard focus to its visible renderer,
    // as Windows would when the user clicks the web page.
    NativeFocusTarget target;
    EnumChildWindows(window_->GetWindowHandle(),FindRenderer,reinterpret_cast<LPARAM>(&target));
    if(target.window&&::GetFocus()!=target.window)::SetFocus(target.window);
    focusing_=false;
  }
  void Resize(){
    if(!window_||!view_)return;const auto size=window_->GetSize();
    // Clip the native toolbar above the child viewport while preserving its
    // Chrome-owned parent, layout, action models and popup anchoring.
    const int toolbar_height=toolbar_?std::max(toolbar_->GetBounds().height,toolbar_->GetPreferredSize().height):0;
    view_->SetBounds(CefRect(0,-toolbar_height,std::max(1,size.width),std::max(1,size.height)+toolbar_height));
  }
  std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> popup_ready_;
  std::function<void()> failed_;
  HWND parent_;bool visible_=false,closing_=false,focusing_=false;CefRefPtr<CefWindow> window_;
  CefRefPtr<CefBrowserView> view_;CefRefPtr<CefView> toolbar_;
  IMPLEMENT_REFCOUNTING(Host);
};
}
CefRefPtr<ChromeTabHost> CreateChromeTab(HWND parent,CefRefPtr<CefClient> client,
    const std::string& url,const CefBrowserSettings& settings,CefRefPtr<CefDictionaryValue> extra,
    CefRefPtr<CefRequestContext> context,std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> popup_ready,std::function<void()> failed){
  CefRefPtr<Host> host=new Host(parent,std::move(popup_ready));host->SetFailure(std::move(failed));if(!host->Start(client,url,settings,extra,context))return nullptr;return host;
}
}
