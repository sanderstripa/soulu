#include "examples/soulu/chrome_tab_host.h"
#include <algorithm>
#include <set>
#include <cwchar>
#include <commctrl.h>
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
  void OnWindowDestroyed(CefRefPtr<CefWindow>) override{UnhookActionPopup();toolbar_=nullptr;view_=nullptr;window_=nullptr;}
  bool OnPopupBrowserViewCreated(CefRefPtr<CefBrowserView>,CefRefPtr<CefBrowserView> popup,bool devtools) override{
    if(devtools)return false;
    CefRefPtr<Host> host=new Host(parent_,popup_ready_);host->view_=popup;
    host->window_=CefWindow::CreateTopLevelWindow(host);
    if(!host->window_)return false;
    if(popup_ready_)popup_ready_(popup->GetBrowser(),host);
    return true;
  }
  void SetVisible(bool visible,bool activate) override {
    CEF_REQUIRE_UI_THREAD();const bool changed=visible_!=visible;visible_=visible;if(!window_)return;
    if(!changed&&visibility_applied_){
      if(visible&&activate&&!focusing_)FocusNativeContent();
      KeepBelowShell();return;
    }
    visibility_applied_=true;
    // Keep Chromium's content view visibility in sync with the Win32 child.
    // Hiding the native container alone leaves the BrowserView logically shown.
    if(view_&&view_->IsVisible()!=visible)view_->SetVisible(visible);
    if(visible){if(!window_->IsVisible())window_->Show();if(activate&&!focusing_)FocusNativeContent();}
    else {DismissActionPopup();window_->Hide();}
    // A Chrome widget can raise itself when shown. Content must stay below
    // the custom toolbar, page glass and the owner's native resize border.
    KeepBelowShell();
  }
  void ArmActionPopup(const CefRect& anchor) override {
    DismissActionPopup();anchor_=anchor;existing_popups_.clear();
    EnumThreadWindows(GetCurrentThreadId(),SnapshotPopup,reinterpret_cast<LPARAM>(this));
    popup_deadline_=GetTickCount64()+15000;mouse_down_=MouseDown();
    const auto generation=++popup_generation_;WatchActionPopup(generation);
  }
  void Close() override{DismissActionPopup();closing_=true;if(view_&&view_->GetBrowser())view_->GetBrowser()->GetHost()->CloseBrowser(true);else if(window_)window_->Close();}
 private:
  void KeepBelowShell(){
    if(!window_||!visible_)return;
    const auto hwnd=window_->GetWindowHandle();
    // Chrome can raise its native child on activation. Restore only Z-order,
    // never its size, so the shell and native resize ring keep pointer input.
    if(GetWindow(hwnd,GW_HWNDNEXT))
      SetWindowPos(hwnd,HWND_BOTTOM,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOACTIVATE);
  }
  static bool MouseDown(){return (GetAsyncKeyState(VK_LBUTTON)|GetAsyncKeyState(VK_RBUTTON)|GetAsyncKeyState(VK_MBUTTON))&0x8000;}
  static BOOL CALLBACK SnapshotPopup(HWND hwnd,LPARAM data){
    if(IsWindowVisible(hwnd))reinterpret_cast<Host*>(data)->existing_popups_.insert(hwnd);return TRUE;
  }
  static BOOL CALLBACK FindActionPopup(HWND hwnd,LPARAM data){
    auto* self=reinterpret_cast<Host*>(data);
    if(!IsWindowVisible(hwnd)||self->existing_popups_.count(hwnd)||!(GetWindowLongPtrW(hwnd,GWL_STYLE)&WS_POPUP))return TRUE;
    wchar_t name[64]={};GetClassNameW(hwnd,name,64);
    if(wcsncmp(name,L"Chrome_WidgetWin_",17)!=0)return TRUE;
    const auto host=self->window_->GetWindowHandle();
    for(HWND owner=GetWindow(hwnd,GW_OWNER);owner;owner=GetWindow(owner,GW_OWNER)){
      if(owner==host||owner==self->parent_){self->action_popup_=hwnd;return FALSE;}
    }
    // Store-installed extensions can retain the installer's Chrome owner
    // instead of the reparented tab widget. Accept only a newly shown,
    // frameless Chrome popup containing an actual web renderer on this UI
    // thread; normal browser windows, menus and tooltips are excluded.
    if(!(GetWindowLongPtrW(hwnd,GWL_STYLE)&WS_CAPTION)){
      NativeFocusTarget renderer;EnumChildWindows(hwnd,FindRenderer,reinterpret_cast<LPARAM>(&renderer));
      if(renderer.window){self->action_popup_=hwnd;return FALSE;}
    }
    return TRUE;
  }
  CefRect ActionBounds(int width,int height){
    POINT anchor={anchor_.x+anchor_.width,anchor_.y+anchor_.height};ClientToScreen(parent_,&anchor);
    POINT origin={0,0};ClientToScreen(parent_,&origin);
    MONITORINFO monitor={sizeof(monitor)};GetMonitorInfoW(MonitorFromPoint(anchor,MONITOR_DEFAULTTONEAREST),&monitor);
    const auto& work=monitor.rcWork;const int dpi=GetDpiForWindow(parent_);
    width=std::clamp(width,1,std::min(MulDiv(800,dpi,96),static_cast<int>(work.right-work.left)));
    height=std::clamp(height,1,std::min(MulDiv(600,dpi,96),static_cast<int>(work.bottom-work.top)));
    int x=anchor.x-width;if(x<origin.x)x=anchor.x-anchor_.width;
    return CefRect(std::clamp<int>(x,work.left,work.right-width),
      std::clamp<int>(anchor.y+MulDiv(6,dpi,96),work.top,work.bottom-height),width,height);
  }
  static LRESULT CALLBACK ActionProc(HWND hwnd,UINT message,WPARAM wp,LPARAM lp,UINT_PTR,DWORD_PTR data){
    CefRefPtr<Host> self=reinterpret_cast<Host*>(data);
    if(message==WM_WINDOWPOSCHANGING){
      auto* pos=reinterpret_cast<WINDOWPOS*>(lp);RECT current={};GetWindowRect(hwnd,&current);
      const auto bounds=self->ActionBounds((pos->flags&SWP_NOSIZE)?current.right-current.left:pos->cx,
        (pos->flags&SWP_NOSIZE)?current.bottom-current.top:pos->cy);
      pos->x=bounds.x;pos->y=bounds.y;pos->cx=bounds.width;pos->cy=bounds.height;
      pos->flags&=~(SWP_NOMOVE|SWP_NOSIZE);
    }
    if(message==WM_NCDESTROY)self->UnhookActionPopup();
    return DefSubclassProc(hwnd,message,wp,lp);
  }
  void UnhookActionPopup(){
    if(popup_hooked_&&action_popup_)RemoveWindowSubclass(action_popup_,ActionProc,reinterpret_cast<UINT_PTR>(this));
    popup_hooked_=false;
  }
  void DismissActionPopup(){
    ++popup_generation_;UnhookActionPopup();
    if(action_popup_&&IsWindow(action_popup_))PostMessageW(action_popup_,WM_CLOSE,0,0);
    action_popup_=nullptr;
  }
  void WatchActionPopup(unsigned generation){
    if(generation!=popup_generation_||closing_||!window_)return;
    if(!action_popup_){
      EnumThreadWindows(GetCurrentThreadId(),FindActionPopup,reinterpret_cast<LPARAM>(this));
      if(!action_popup_){if(GetTickCount64()>=popup_deadline_)return;}
      else {
        popup_started_=GetTickCount64();
        popup_hooked_=SetWindowSubclass(action_popup_,ActionProc,reinterpret_cast<UINT_PTR>(this),reinterpret_cast<DWORD_PTR>(this))!=FALSE;
      }
    }else if(!IsWindow(action_popup_)||!IsWindowVisible(action_popup_)){UnhookActionPopup();action_popup_=nullptr;if(GetTickCount64()>=popup_deadline_)return;}
    if(action_popup_){
      RECT bounds={};GetWindowRect(action_popup_,&bounds);
      const auto position=ActionBounds(bounds.right-bounds.left,bounds.bottom-bounds.top);
      if(bounds.left!=position.x||bounds.top!=position.y||bounds.right-bounds.left!=position.width||bounds.bottom-bounds.top!=position.height)
        SetWindowPos(action_popup_,HWND_TOP,position.x,position.y,position.width,position.height,SWP_NOACTIVATE);
      const bool down=MouseDown();POINT mouse={};GetCursorPos(&mouse);GetWindowRect(action_popup_,&bounds);
      const auto foreground=GetForegroundWindow();
      // Child Chrome widgets do not receive normal top-level deactivation
      // when the user clicks the shell. Dismiss on outside press as well.
      if((down&&!mouse_down_&&!PtInRect(&bounds,mouse))||(GetAsyncKeyState(VK_ESCAPE)&0x8000)||
          (GetTickCount64()-popup_started_>250&&foreground!=parent_&&foreground!=action_popup_&&
           !IsChild(action_popup_,foreground)&&GetAncestor(foreground,GA_ROOTOWNER)!=parent_)){
        DismissActionPopup();return;
      }
      mouse_down_=down;
    }
    CefRefPtr<Host> self=this;CefPostDelayedTask(TID_UI,new Task([self,generation]{self->WatchActionPopup(generation);}),30);
  }
  CefRect anchor_;std::set<HWND> existing_popups_;HWND action_popup_=nullptr;
  unsigned popup_generation_=0;ULONGLONG popup_deadline_=0,popup_started_=0;bool mouse_down_=false,popup_hooked_=false;
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
    focusing_=false;KeepBelowShell();
  }
  void Resize(){
    if(!window_||!view_||resizing_)return;const auto size=window_->GetSize();
    // Clip the native toolbar above the child viewport while preserving its
    // Chrome-owned parent, layout, action models and popup anchoring.
    if(!toolbar_height_&&toolbar_)toolbar_height_=std::max(toolbar_->GetBounds().height,toolbar_->GetPreferredSize().height);
    const CefRect bounds(0,-toolbar_height_,std::max(1,size.width),std::max(1,size.height)+toolbar_height_);
    if(view_->GetBounds()==bounds)return;
    resizing_=true;view_->SetBounds(bounds);resizing_=false;
  }
  std::function<void(CefRefPtr<CefBrowser>,CefRefPtr<ChromeTabHost>)> popup_ready_;
  std::function<void()> failed_;
  HWND parent_;bool visible_=false,closing_=false,focusing_=false,visibility_applied_=false,resizing_=false;int toolbar_height_=0;CefRefPtr<CefWindow> window_;
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
