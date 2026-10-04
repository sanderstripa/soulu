#include "examples/soulu/soulu_menu.h"
#include "examples/soulu/typography_native.h"
#include "examples/soulu/typography_metrics.h"
#include "include/cef_app.h"
#include <windowsx.h>
#include <dwmapi.h>
#include <oleacc.h>
#include <algorithm>
#include <memory>

namespace soulu {
std::wstring MenuLabel(const std::wstring& input) {
  std::wstring output;
  for(size_t i=0;i<input.size();++i) {
    if(input[i]!=L'&')output+=input[i];
    else if(i+1<input.size()&&input[i+1]==L'&'){output+=L'&';++i;}
  }
  return output;
}
namespace {
struct Session;
struct Panel {
  Session* session=nullptr;
  HWND window=nullptr;
  MenuModel* model=nullptr;
  Panel* parent=nullptr;
  int selected=-1, width=0, height=0, offset=0;
  std::vector<RECT> rows;
};
struct Session {
  HWND owner=nullptr,previousFocus=nullptr;
  UINT dpi=96;
  MenuAppearance appearance;
  MenuModel model;
  std::vector<std::unique_ptr<Panel>> panels;
  bool done=false;
  int result=0;
  int Px(int n) const {return MulDiv(n,dpi,96);}
  COLORREF Surface()const{return appearance.dark?RGB(17,18,21):RGB(255,255,255);}
  COLORREF Text()const{return appearance.dark?RGB(238,238,239):RGB(28,29,32);}
  COLORREF Muted()const{return appearance.dark?RGB(150,151,157):RGB(104,106,113);}
  COLORREF Hover()const{return appearance.dark?RGB(37,38,43):RGB(242,243,245);}
  COLORREF Line()const{return appearance.dark?RGB(48,49,54):RGB(232,233,235);}
};
thread_local Session* active=nullptr;
void CloseAfter(Session& s,Panel* panel){
  auto found=std::find_if(s.panels.begin(),s.panels.end(),[&](auto& p){return p.get()==panel;});
  if(found==s.panels.end())return;
  while(s.panels.end()!=found+1){DestroyWindow(s.panels.back()->window);s.panels.pop_back();}
}
bool Selectable(const MenuItem& item){return item.enabled&&item.type!=MenuItemType::Separator;}
void Select(Panel& p,int next){
  if(next==p.selected)return;
  CloseAfter(*p.session,&p);p.selected=next;
  if(next>=0){auto r=p.rows[next];const int top=p.session->Px(6),bottom=p.height-top;
    if(r.top-p.offset<top)p.offset=r.top-top;
    if(r.bottom-p.offset>bottom)p.offset=r.bottom-bottom;}
  NotifyWinEvent(EVENT_OBJECT_FOCUS,p.window,OBJID_CLIENT,next+1);
  InvalidateRect(p.window,nullptr,FALSE);
}
void Step(Panel& p,int direction,bool edge=false){
  int count=static_cast<int>(p.model->size()),next=edge?(direction>0?-1:count):p.selected;
  for(int i=0;i<count;++i){next=(next+direction+count)%count;if(Selectable((*p.model)[next])){Select(p,next);return;}}
}
Panel* Open(Session&,MenuModel&,POINT,Panel*);
void Activate(Panel& p,bool first=false){
  if(p.selected<0)return;
  auto& item=(*p.model)[p.selected];if(!Selectable(item))return;
  if(!item.children.empty()){
    CloseAfter(*p.session,&p);RECT rect={};GetWindowRect(p.window,&rect);
    POINT at={rect.right-p.session->Px(3),rect.top+p.rows[p.selected].top-p.offset};
    if(auto* child=Open(*p.session,item.children,at,&p);child&&first)Step(*child,1,true);
  }else{p.session->result=item.command;p.session->done=true;}
}
// MSAA exposes native menu rows without a document or browser bridge.
// HWND lookup prevents an assistive client from retaining a dead Panel pointer.
class AccessibleMenu final:public IAccessible {
 public: explicit AccessibleMenu(HWND hwnd):window_(hwnd){}
  HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid,void** out) override {if(!out)return E_POINTER;*out=nullptr;if(iid==IID_IUnknown||iid==IID_IDispatch||iid==IID_IAccessible){*out=static_cast<IAccessible*>(this);AddRef();return S_OK;}return E_NOINTERFACE;}
  ULONG STDMETHODCALLTYPE AddRef() override{return ++refs_;}
  ULONG STDMETHODCALLTYPE Release() override{auto refs=--refs_;if(!refs)delete this;return refs;}
  HRESULT STDMETHODCALLTYPE GetTypeInfoCount(UINT* n) override{if(!n)return E_POINTER;*n=0;return S_OK;}
  HRESULT STDMETHODCALLTYPE GetTypeInfo(UINT,LCID,ITypeInfo**) override{return E_NOTIMPL;}
  HRESULT STDMETHODCALLTYPE GetIDsOfNames(REFIID,LPOLESTR*,UINT,LCID,DISPID*) override{return E_NOTIMPL;}
  HRESULT STDMETHODCALLTYPE Invoke(DISPID,REFIID,LCID,WORD,DISPPARAMS*,VARIANT*,EXCEPINFO*,UINT*) override{return E_NOTIMPL;}
  HRESULT STDMETHODCALLTYPE get_accParent(IDispatch** out) override{if(!out)return E_POINTER;*out=nullptr;return S_FALSE;}
  HRESULT STDMETHODCALLTYPE get_accChildCount(long* n) override{if(!n)return E_POINTER;auto p=Get();*n=p?static_cast<long>(p->model->size()):0;return S_OK;}
  HRESULT STDMETHODCALLTYPE get_accChild(VARIANT,IDispatch** out) override{if(!out)return E_POINTER;*out=nullptr;return S_FALSE;}
  HRESULT STDMETHODCALLTYPE get_accName(VARIANT child,BSTR* out) override{if(!out)return E_POINTER;auto item=Item(child);*out=SysAllocString(item?item->label.c_str():L"Soulu");return S_OK;}
  HRESULT STDMETHODCALLTYPE get_accValue(VARIANT,BSTR* out) override{if(!out)return E_POINTER;*out=nullptr;return S_FALSE;}
  HRESULT STDMETHODCALLTYPE get_accDescription(VARIANT,BSTR* out) override{return get_accValue({},out);}
  HRESULT STDMETHODCALLTYPE get_accRole(VARIANT child,VARIANT* out) override{if(!out)return E_POINTER;VariantInit(out);out->vt=VT_I4;auto item=Item(child);out->lVal=!item?ROLE_SYSTEM_MENUPOPUP:item->type==MenuItemType::Separator?ROLE_SYSTEM_SEPARATOR:ROLE_SYSTEM_MENUITEM;return S_OK;}
  HRESULT STDMETHODCALLTYPE get_accState(VARIANT child,VARIANT* out) override{if(!out)return E_POINTER;VariantInit(out);out->vt=VT_I4;auto p=Get();auto item=Item(child);out->lVal=!p?STATE_SYSTEM_UNAVAILABLE:0;if(item){if(!item->enabled)out->lVal|=STATE_SYSTEM_UNAVAILABLE;else out->lVal|=STATE_SYSTEM_FOCUSABLE;if(item->checked)out->lVal|=STATE_SYSTEM_CHECKED;if(!item->children.empty())out->lVal|=STATE_SYSTEM_HASPOPUP;if(child.lVal==p->selected+1)out->lVal|=STATE_SYSTEM_FOCUSED;}return S_OK;}
  HRESULT STDMETHODCALLTYPE get_accHelp(VARIANT,BSTR* out) override{return get_accValue({},out);}
  HRESULT STDMETHODCALLTYPE get_accHelpTopic(BSTR* out,VARIANT,long* topic) override{if(out)*out=nullptr;if(topic)*topic=0;return S_FALSE;}
  HRESULT STDMETHODCALLTYPE get_accKeyboardShortcut(VARIANT child,BSTR* out) override{if(!out)return E_POINTER;auto item=Item(child);*out=item?SysAllocString(item->accelerator.c_str()):nullptr;return item?S_OK:S_FALSE;}
  HRESULT STDMETHODCALLTYPE get_accFocus(VARIANT* out) override{if(!out)return E_POINTER;VariantInit(out);auto p=Get();if(!p)return S_FALSE;out->vt=VT_I4;out->lVal=p->selected+1;return S_OK;}
  HRESULT STDMETHODCALLTYPE get_accSelection(VARIANT* out) override{return get_accFocus(out);}
  HRESULT STDMETHODCALLTYPE get_accDefaultAction(VARIANT child,BSTR* out) override{if(!out)return E_POINTER;*out=Item(child)?SysAllocString(L"Activate"):nullptr;return *out?S_OK:S_FALSE;}
  HRESULT STDMETHODCALLTYPE accSelect(long flags,VARIANT child) override{auto p=Get();auto item=Item(child);if(!p||!item||!Selectable(*item))return E_INVALIDARG;if(flags&(SELFLAG_TAKEFOCUS|SELFLAG_TAKESELECTION)){Select(*p,child.lVal-1);SetFocus(window_);return S_OK;}return E_INVALIDARG;}
  HRESULT STDMETHODCALLTYPE accLocation(long* x,long* y,long* width,long* height,VARIANT child) override{if(!x||!y||!width||!height)return E_POINTER;auto p=Get();if(!p)return S_FALSE;RECT r={};GetWindowRect(window_,&r);if(Item(child)){auto row=p->rows[child.lVal-1];OffsetRect(&row,r.left,r.top-p->offset);r=row;}*x=r.left;*y=r.top;*width=r.right-r.left;*height=r.bottom-r.top;return S_OK;}
  HRESULT STDMETHODCALLTYPE accNavigate(long direction,VARIANT from,VARIANT* out) override{if(!out)return E_POINTER;VariantInit(out);auto p=Get();if(!p)return S_FALSE;long id=from.vt==VT_I4?from.lVal:0;long next=direction==NAVDIR_FIRSTCHILD?1:direction==NAVDIR_LASTCHILD?static_cast<long>(p->model->size()):direction==NAVDIR_NEXT?id+1:direction==NAVDIR_PREVIOUS?id-1:0;if(next<1||next>static_cast<long>(p->model->size()))return S_FALSE;out->vt=VT_I4;out->lVal=next;return S_OK;}
  HRESULT STDMETHODCALLTYPE accHitTest(long x,long y,VARIANT* out) override{if(!out)return E_POINTER;VariantInit(out);auto p=Get();if(!p)return S_FALSE;POINT point={x,y};ScreenToClient(window_,&point);point.y+=p->offset;for(size_t i=0;i<p->rows.size();++i)if(PtInRect(&p->rows[i],point)){out->vt=VT_I4;out->lVal=static_cast<long>(i+1);return S_OK;}return S_FALSE;}
  HRESULT STDMETHODCALLTYPE accDoDefaultAction(VARIANT child) override{auto p=Get();auto item=Item(child);if(!p||!item||!Selectable(*item))return E_INVALIDARG;Select(*p,child.lVal-1);Activate(*p,true);return S_OK;}
  HRESULT STDMETHODCALLTYPE put_accName(VARIANT,BSTR) override{return E_NOTIMPL;}
  HRESULT STDMETHODCALLTYPE put_accValue(VARIANT,BSTR) override{return E_NOTIMPL;}
 private:Panel* Get(){return IsWindow(window_)?reinterpret_cast<Panel*>(GetWindowLongPtrW(window_,GWLP_USERDATA)):nullptr;}
  MenuItem* Item(VARIANT child){auto p=Get();return p&&child.vt==VT_I4&&child.lVal>0&&child.lVal<=static_cast<long>(p->model->size())?&(*p->model)[child.lVal-1]:nullptr;}
  HWND window_;ULONG refs_=1;
};
void Rounded(HDC dc,RECT r,COLORREF color,int radius){
  auto brush=CreateSolidBrush(color);auto oldBrush=SelectObject(dc,brush);auto oldPen=SelectObject(dc,GetStockObject(NULL_PEN));
  RoundRect(dc,r.left,r.top,r.right,r.bottom,radius,radius);SelectObject(dc,oldPen);SelectObject(dc,oldBrush);DeleteObject(brush);
}
LRESULT CALLBACK Procedure(HWND window,UINT message,WPARAM w,LPARAM l){
  auto* p=reinterpret_cast<Panel*>(GetWindowLongPtrW(window,GWLP_USERDATA));
  if(message==WM_NCCREATE){p=reinterpret_cast<Panel*>(reinterpret_cast<CREATESTRUCTW*>(l)->lpCreateParams);p->window=window;SetWindowLongPtrW(window,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(p));}
  if(!p)return DefWindowProcW(window,message,w,l);
  auto& s=*p->session;
  if(message==WM_GETOBJECT&&static_cast<LONG>(l)==OBJID_CLIENT){auto* accessible=new AccessibleMenu(window);auto result=LresultFromObject(IID_IAccessible,w,accessible);accessible->Release();return result;}
  if(message==WM_NCDESTROY){SetWindowLongPtrW(window,GWLP_USERDATA,0);return DefWindowProcW(window,message,w,l);}
  if(message==WM_ERASEBKGND)return 1;
  if(message==WM_PAINT){
    PAINTSTRUCT paint={};auto target=BeginPaint(window,&paint);
    auto dc=CreateCompatibleDC(target);auto bitmap=CreateCompatibleBitmap(target,p->width,p->height);auto oldBitmap=SelectObject(dc,bitmap);
    RECT all={0,0,p->width,p->height};Rounded(dc,all,s.Surface(),s.Px(14));
    SetBkMode(dc,TRANSPARENT);auto oldFont=SelectObject(dc,TypographyFont(typography::compactControl,s.dpi));
    int saved=SaveDC(dc);IntersectClipRect(dc,s.Px(6),s.Px(6),p->width-s.Px(6),p->height-s.Px(6));
    for(size_t i=0;i<p->model->size();++i){
      auto& item=(*p->model)[i];RECT row=p->rows[i];OffsetRect(&row,0,-p->offset);
      if(item.type==MenuItemType::Separator){RECT line={s.Px(12),(row.top+row.bottom)/2,p->width-s.Px(12),(row.top+row.bottom)/2+1};auto b=CreateSolidBrush(s.Line());FillRect(dc,&line,b);DeleteObject(b);continue;}
      if(static_cast<int>(i)==p->selected)Rounded(dc,row,s.Hover(),s.Px(8));
      SetTextColor(dc,item.enabled?s.Text():s.Muted());RECT label=row;label.left+=s.Px(26);label.right-=s.Px(20);
      if(!item.accelerator.empty()){RECT shortcut=label;shortcut.left=shortcut.right-s.Px(124);SetTextColor(dc,s.Muted());DrawTextW(dc,item.accelerator.c_str(),-1,&shortcut,DT_RIGHT|DT_VCENTER|DT_SINGLELINE|DT_NOPREFIX);label.right=shortcut.left-s.Px(12);SetTextColor(dc,item.enabled?s.Text():s.Muted());}
      DrawTextW(dc,item.label.c_str(),-1,&label,DT_LEFT|DT_VCENTER|DT_SINGLELINE|DT_END_ELLIPSIS|DT_NOPREFIX);
      if(item.checked){RECT mark=row;mark.left+=s.Px(5);mark.right=mark.left+s.Px(16);DrawTextW(dc,item.type==MenuItemType::Radio?L"•":L"✓",-1,&mark,DT_CENTER|DT_VCENTER|DT_SINGLELINE);}
      if(!item.children.empty()){RECT arrow=row;arrow.left=arrow.right-s.Px(20);DrawTextW(dc,L"›",-1,&arrow,DT_CENTER|DT_VCENTER|DT_SINGLELINE);}
    }
    RestoreDC(dc,saved);SelectObject(dc,oldFont);BitBlt(target,0,0,p->width,p->height,dc,0,0,SRCCOPY);SelectObject(dc,oldBitmap);DeleteObject(bitmap);DeleteDC(dc);EndPaint(window,&paint);return 0;
  }
  if(message==WM_MOUSEMOVE||message==WM_LBUTTONUP||message==WM_RBUTTONUP){
    POINT point={GET_X_LPARAM(l),GET_Y_LPARAM(l)+p->offset};int hit=-1;
    for(size_t i=0;i<p->rows.size();++i)if(PtInRect(&p->rows[i],point)&&Selectable((*p->model)[i])){hit=static_cast<int>(i);break;}
    if(hit<0&&message==WM_MOUSEMOVE){KillTimer(window,1);Select(*p,-1);}
    if(hit>=0){Select(*p,hit);if(message!=WM_MOUSEMOVE)Activate(*p);else if(!(*p->model)[hit].children.empty())SetTimer(window,1,180,nullptr);}
    return 0;
  }
  if(message==WM_TIMER){KillTimer(window,1);POINT point={};GetCursorPos(&point);RECT r={};GetWindowRect(window,&r);if(PtInRect(&r,point))Activate(*p);return 0;}
  if(message==WM_MOUSEWHEEL){int extent=p->rows.empty()?0:p->rows.back().bottom+s.Px(6);p->offset=std::clamp(p->offset-GET_WHEEL_DELTA_WPARAM(w)/WHEEL_DELTA*s.Px(90),0,std::max(0,extent-p->height));InvalidateRect(window,nullptr,FALSE);return 0;}
  if(message==WM_KEYDOWN){switch(w){
    case VK_DOWN:Step(*p,1);break;case VK_UP:Step(*p,-1);break;
    case VK_HOME:Step(*p,1,true);break;case VK_END:Step(*p,-1,true);break;
    case VK_RETURN:case VK_SPACE:Activate(*p,true);break;case VK_RIGHT:Activate(*p,true);break;
    case VK_LEFT:if(p->parent){auto* parent=p->parent;CloseAfter(s,parent);SetFocus(parent->window);}break;
    case VK_ESCAPE:if(p->parent){auto* parent=p->parent;CloseAfter(s,parent);SetFocus(parent->window);}else s.done=true;break;
  }return 0;}
  if(message==WM_CLOSE){s.done=true;return 0;}
  return DefWindowProcW(window,message,w,l);
}
Panel* Open(Session& s,MenuModel& model,POINT at,Panel* parent){
  auto panel=std::make_unique<Panel>();panel->session=&s;panel->model=&model;panel->parent=parent;
  int width=s.Px(240),y=s.Px(6);auto dc=GetDC(s.owner);auto font=SelectObject(dc,TypographyFont(typography::compactControl,s.dpi));
  for(auto& item:model){item.label=MenuLabel(item.label);SIZE size={};GetTextExtentPoint32W(dc,item.label.c_str(),static_cast<int>(item.label.size()),&size);width=std::max(width,static_cast<int>(size.cx)+s.Px(item.accelerator.empty()?58:194));}
  SelectObject(dc,font);ReleaseDC(s.owner,dc);panel->width=std::min(width,s.Px(560));
  for(auto& item:model){int height=s.Px(item.type==MenuItemType::Separator?9:32);panel->rows.push_back({s.Px(6),y,panel->width-s.Px(6),y+height});y+=height;}
  MONITORINFO monitor={sizeof(monitor)};GetMonitorInfoW(MonitorFromPoint(at,MONITOR_DEFAULTTONEAREST),&monitor);auto work=monitor.rcWork;
  panel->width=std::min(panel->width,static_cast<int>(work.right-work.left));panel->height=std::min(y+s.Px(6),static_cast<int>(work.bottom-work.top)-s.Px(8));
  if(parent&&at.x+panel->width>work.right){RECT rect={};GetWindowRect(parent->window,&rect);at.x=rect.left-panel->width+s.Px(3);}
  at.x=std::clamp(static_cast<int>(at.x),static_cast<int>(work.left),static_cast<int>(work.right)-panel->width);
  at.y=std::clamp(static_cast<int>(at.y),static_cast<int>(work.top),static_cast<int>(work.bottom)-panel->height);
  HWND window=CreateWindowExW(WS_EX_TOOLWINDOW|WS_EX_TOPMOST,L"SouluMenuHost",L"Soulu",WS_POPUP,at.x,at.y,panel->width,panel->height,s.owner,nullptr,GetModuleHandleW(nullptr),panel.get());
  if(!window)return nullptr;
  SetWindowRgn(window,CreateRoundRectRgn(0,0,panel->width+1,panel->height+1,s.Px(14),s.Px(14)),FALSE);
  const DWORD corner=2;DwmSetWindowAttribute(window,33,&corner,sizeof(corner));
  auto* result=panel.get();s.panels.push_back(std::move(panel));ShowWindow(window,SW_SHOWNOACTIVATE);SetFocus(window);NotifyWinEvent(EVENT_SYSTEM_MENUPOPUPSTART,window,OBJID_CLIENT,CHILDID_SELF);return result;
}
}
int ShowSouluMenu(HWND owner,POINT anchor,MenuModel model,MenuAppearance appearance){
  if(active||model.empty()||!IsWindow(owner))return 0;
  static const bool registered=[](){WNDCLASSW wc={};wc.style=CS_DROPSHADOW;wc.lpfnWndProc=Procedure;wc.hInstance=GetModuleHandleW(nullptr);wc.hCursor=LoadCursorW(nullptr,IDC_ARROW);wc.lpszClassName=L"SouluMenuHost";return RegisterClassW(&wc)!=0;}();
  if(!registered)return 0;
  Session s;s.owner=owner;s.previousFocus=GetFocus();s.model=std::move(model);s.appearance=appearance;
  s.dpi=GetDpiForWindow(owner);if(!s.dpi)s.dpi=96;
  active=&s;if(!Open(s,s.model,anchor,nullptr)){active=nullptr;return 0;}
  CefScopedSetNestableTasksAllowed allow_tasks;
  MSG message={};
  while(!s.done&&IsWindow(owner)){
    int received=GetMessageW(&message,nullptr,0,0);if(received<=0){if(received==0)PostQuitMessage(static_cast<int>(message.wParam));break;}
    const bool ours=std::any_of(s.panels.begin(),s.panels.end(),[&](auto& p){return p->window==message.hwnd;});
    if(!ours&&(message.message==WM_LBUTTONDOWN||message.message==WM_RBUTTONDOWN||message.message==WM_MBUTTONDOWN||message.message==WM_NCLBUTTONDOWN)){s.done=true;}
    if(message.message==WM_ACTIVATEAPP&&!message.wParam)s.done=true;
    TranslateMessage(&message);DispatchMessageW(&message);
  }
  for(auto& p:s.panels)if(IsWindow(p->window))DestroyWindow(p->window);
  active=nullptr;if(IsWindow(s.previousFocus))SetFocus(s.previousFocus);
  return s.result;
}
void DismissSouluMenus(HWND owner){if(active&&active->owner==owner){active->done=true;PostMessageW(owner,WM_NULL,0,0);}}
}
