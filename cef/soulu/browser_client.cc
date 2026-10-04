#include "examples/soulu/menu_commands.h"
#include "examples/soulu/isolated_page_job.h"
#include "examples/soulu/soulu_menu.h"
#include "examples/soulu/typography_native.h"
#include "examples/soulu/browser_client.h"
#include "examples/soulu/adblock_bridge.h"
#include "include/cef_process_message.h"
#include <chrono>

#include <string>
#include <cstring>
#include <tuple>
#include "include/cef_image.h"

#include "examples/soulu/browser_window.h"
#include "include/wrapper/cef_helpers.h"
#include "include/cef_parser.h"

namespace soulu {
bool BrowserClient::OnTooltip(CefRefPtr<CefBrowser> browser,CefString&){
  const std::string url=browser->GetMainFrame()->GetURL();
  // Internal pages draw title tooltips with their shared DOM typography.
  return owner_->IsTrustedUi(url)||owner_->IsHomeUi(url)||owner_->IsHistoryUi(url)||owner_->IsOnboardingUi(url);
}
bool BrowserClient::OnJSDialog(CefRefPtr<CefBrowser>, const CefString& origin, JSDialogType type,
    const CefString& message, const CefString& initial,
    CefRefPtr<CefJSDialogCallback> callback, bool& suppress) {
  CEF_REQUIRE_UI_THREAD();
  if(js_dialog_open_){suppress=true;return false;}
  CefRefPtr<BrowserClient> keep_alive(this);
  js_dialog_open_=true;
  std::wstring value;
  const auto site=origin.empty()?std::wstring():CefFormatUrlForSecurityDisplay(origin).ToWString();
  const auto text=site.empty()?message.ToWString():site+L"\n\n"+message.ToWString();
  bool accepted=false;
  if(type==JSDIALOGTYPE_PROMPT)accepted=TypographyPrompt(owner_->hwnd(),text,initial.ToWString(),value,this);
  else accepted=TypographyMessageBox(owner_->hwnd(),text.c_str(),L"Soulu",
      type==JSDIALOGTYPE_CONFIRM?MB_OKCANCEL:MB_OK,this)==IDOK;
  js_dialog_open_=false;callback->Continue(accepted,CefString(value));return true;
}
bool BrowserClient::OnBeforeUnloadDialog(CefRefPtr<CefBrowser>,const CefString& text,bool,
    CefRefPtr<CefJSDialogCallback> callback){
  CEF_REQUIRE_UI_THREAD();
  if(js_dialog_open_){callback->Continue(false,CefString());return true;}
  CefRefPtr<BrowserClient> keep_alive(this);
  js_dialog_open_=true;
  const bool accepted=TypographyMessageBox(owner_->hwnd(),text.ToWString().c_str(),L"Soulu",MB_YESNO|MB_DEFBUTTON2,this)==IDYES;
  js_dialog_open_=false;callback->Continue(accepted,CefString());return true;
}
void BrowserClient::OnResetDialogState(CefRefPtr<CefBrowser>){
  CEF_REQUIRE_UI_THREAD();TypographyCancelDialogs(this);
}

namespace {
class CopyImage final:public CefDownloadImageCallback {
 public:explicit CopyImage(HWND owner):owner_(owner){}
  void OnDownloadImageFinished(const CefString&,int,CefRefPtr<CefImage> image) override {
    if(!image||!IsWindow(owner_))return;int width=0,height=0;
    auto bitmap=image->GetAsBitmap(1.0f,CEF_COLOR_TYPE_BGRA_8888,CEF_ALPHA_TYPE_OPAQUE,width,height);
    if(!bitmap||width<=0||height<=0||bitmap->GetSize()>128*1024*1024)return;
    auto memory=GlobalAlloc(GMEM_MOVEABLE,sizeof(BITMAPINFOHEADER)+bitmap->GetSize());if(!memory)return;
    auto* bytes=static_cast<unsigned char*>(GlobalLock(memory));if(!bytes){GlobalFree(memory);return;}
    BITMAPINFOHEADER header={};header.biSize=sizeof(header);header.biWidth=width;header.biHeight=-height;header.biPlanes=1;header.biBitCount=32;header.biCompression=BI_RGB;
    memcpy(bytes,&header,sizeof(header));bitmap->GetData(bytes+sizeof(header),bitmap->GetSize(),0);GlobalUnlock(memory);
    if(OpenClipboard(owner_)){EmptyClipboard();if(SetClipboardData(CF_DIB,memory))memory=nullptr;CloseClipboard();}if(memory)GlobalFree(memory);
  }
 private:HWND owner_;IMPLEMENT_REFCOUNTING(CopyImage);
};

bool DownloadableLink(const std::string& url) {
  return url.rfind("https://", 0) == 0 || url.rfind("http://", 0) == 0;
}

class BridgeHandler final : public CefMessageRouterBrowserSide::Handler {
 public:
  explicit BridgeHandler(CefRefPtr<BrowserWindow> owner, int id) : owner_(owner), id_(id) {}
  bool OnQuery(CefRefPtr<CefBrowser>, CefRefPtr<CefFrame> frame, int64_t,
               const CefString& request, bool,
               CefRefPtr<Callback> callback) override {
    if (!frame->IsMain()) return false;
    const std::string url = frame->GetURL();
    if (owner_->IsOnboardingUi(url)) {
      owner_->HandleOnboardingBridge(id_, request, callback);
      return true;
    }
    if (owner_->IsHistoryUi(url)) {
      owner_->HandleHistoryBridge(id_, request, callback);
      return true;
    }
    if (owner_->IsHomeUi(url)) {
      owner_->HandleHomeBridge(id_, request, callback);
      return true;
    }
    if (!owner_->IsTrustedUi(url)) {
      return false;
    }
    if (owner_->HandleSettingsBridge(id_, request, callback)) return true;
    owner_->HandleBridge(request, callback, id_ == -1);
    return true;
  }
 private:
  CefRefPtr<BrowserWindow> owner_;
  int id_;
};
}

BrowserClient::BrowserClient(CefRefPtr<BrowserWindow> owner, BrowserRole role, int tab_id)
    : owner_(owner), role_(role), tab_id_(tab_id),
      policy_(role!=BrowserRole::kShell?owner->PolicyForTab(tab_id):nullptr) {}

bool BrowserClient::OnPreKeyEvent(CefRefPtr<CefBrowser> browser,const CefKeyEvent& event,CefEventHandle,bool*) {
  if (role_ == BrowserRole::kSettings) return false;
  if(role_==BrowserRole::kContent&&event.type==KEYEVENT_RAWKEYDOWN){
    if((event.modifiers&EVENTFLAG_CONTROL_DOWN)&&!(event.modifiers&EVENTFLAG_ALT_DOWN)){
      switch(event.windows_key_code){case 'R':browser->Reload();return true;case 'P':browser->GetHost()->Print();return true;case 'S':if(DownloadableLink(browser->GetMainFrame()->GetURL()))browser->GetHost()->StartDownload(browser->GetMainFrame()->GetURL());return true;case 'U':browser->GetMainFrame()->ViewSource();return true;}
    }
    if(event.modifiers&EVENTFLAG_ALT_DOWN){if(event.windows_key_code==VK_LEFT){browser->GoBack();return true;}if(event.windows_key_code==VK_RIGHT){browser->GoForward();return true;}}
  }
  if (owner_->SettingsOverlayActive()) { owner_->FocusSettings(); return true; }
  if(event.type==KEYEVENT_RAWKEYDOWN&&(event.modifiers&EVENTFLAG_CONTROL_DOWN)&&!(event.modifiers&EVENTFLAG_ALT_DOWN)) {
    if(event.windows_key_code=='H'){owner_->OpenHistory();return true;}
    if(event.windows_key_code==VK_DELETE&&(event.modifiers&EVENTFLAG_SHIFT_DOWN)){owner_->OpenHistory(true);return true;}
  }
  if(event.type==KEYEVENT_RAWKEYDOWN && owner_->HandlePageShortcut(tab_id_, event.windows_key_code,
      (event.modifiers&EVENTFLAG_CONTROL_DOWN)!=0, (event.modifiers&EVENTFLAG_ALT_DOWN)!=0)) return true;
  if(event.type==KEYEVENT_RAWKEYDOWN&&(event.modifiers&EVENTFLAG_CONTROL_DOWN)&&event.windows_key_code=='F') {
    owner_->RequestFind();return true;
  }
  return false;
}

CefRefPtr<CefDictionaryValue> BrowserClient::AdBlockSnapshot() {
  auto result=AdBlockStatus();std::lock_guard lock(adblock_mutex_);
  result->SetDouble("blockedRequests",static_cast<double>(adblock_blocked_));
  result->SetDouble("checkedRequests",static_cast<double>(adblock_checked_));
  result->SetBool("enabled",policy_&&policy_->Blocking(adblock_top_));
  result->SetBool("active",result->GetBool("ready")&&result->GetBool("enabled")&&!WebOrigin(adblock_top_).empty());
  result->SetString("scope","current tab document");
  result->SetList("hits",adblock_hits_->Copy());return result;
}
void BrowserClient::RefreshAdBlock(CefRefPtr<CefBrowser> browser) {
  CEF_REQUIRE_UI_THREAD();if(role_!=BrowserRole::kContent)return;
  const auto revision=policy_?policy_->Revision():0;
  const auto updated=AdBlockStatus()->GetDouble("lastSuccessfulUpdate");
  if(revision==adblock_policy_revision_&&updated==adblock_filter_update_)return;
  adblock_policy_revision_=revision;adblock_filter_update_=updated;
  std::vector<CefString> ids;browser->GetFrameIdentifiers(ids);
  for(const auto& id:ids)if(auto frame=browser->GetFrameByIdentifier(id))
    frame->SendProcessMessage(PID_RENDERER,CefProcessMessage::Create("soulu.adblock.refresh"));
}
class AdBlockResourceHandler final : public CefResourceRequestHandler {
 public:
  AdBlockResourceHandler(CefRefPtr<BrowserClient> client,std::string top,std::string source,uint64_t generation)
    :client_(client),top_(std::move(top)),source_(std::move(source)),generation_(generation){}
  ReturnValue OnBeforeResourceLoad(CefRefPtr<CefBrowser>,CefRefPtr<CefFrame>,
      CefRefPtr<CefRequest> request,CefRefPtr<CefCallback>) override {
    CEF_REQUIRE_IO_THREAD();
    return client_->FilterResource(request,request->GetURL(),top_,source_,generation_,recorded_)?RV_CANCEL:RV_CONTINUE;
  }
  void OnResourceRedirect(CefRefPtr<CefBrowser>,CefRefPtr<CefFrame>,
      CefRefPtr<CefRequest> request,CefRefPtr<CefResponse>,CefString& new_url) override {
    CEF_REQUIRE_IO_THREAD();
    // Chromium refuses an HTTP-to-data redirect before contacting its target.
    if(client_->FilterResource(request,new_url,top_,source_,generation_,recorded_))new_url="data:,";
  }
 private:
  CefRefPtr<BrowserClient> client_;const std::string top_,source_;const uint64_t generation_;
  bool recorded_=false;
  IMPLEMENT_REFCOUNTING(AdBlockResourceHandler);
};
CefRefPtr<CefResourceRequestHandler> BrowserClient::GetResourceRequestHandler(
    CefRefPtr<CefBrowser>,CefRefPtr<CefFrame> frame,CefRefPtr<CefRequest> request,
    bool,bool download,const CefString& initiator,bool&) {
  CEF_REQUIRE_IO_THREAD();
  if(role_!=BrowserRole::kContent||download||request->GetResourceType()==RT_MAIN_FRAME)return nullptr;
  std::string top;uint64_t generation;
  {std::lock_guard lock(adblock_mutex_);top=adblock_top_;generation=adblock_generation_;}
  std::string source=initiator;
  if(WebOrigin(source).empty())source=frame?frame->GetURL().ToString():top;
  if(WebOrigin(source).empty())source=top;
  // Each request keeps its document context across redirects/rapid navigation.
  // The engine remains shared; this object only stores a few context fields.
  return new AdBlockResourceHandler(this,top,source,generation);
}
bool BrowserClient::FilterResource(CefRefPtr<CefRequest> request,const std::string& url,
    const std::string& top,const std::string& source,uint64_t generation,bool& recorded) {
  if(!policy_||!policy_->Blocking(top)||WebOrigin(top).empty()||WebOrigin(url).empty())return false;
  std::string rule;
  const bool blocked=MatchAdBlock(url,source,request->GetResourceType(),request->GetMethod(),&rule);
  {std::lock_guard lock(adblock_mutex_);if(generation==adblock_generation_){++adblock_checked_;
    if(blocked&&!recorded){++adblock_blocked_;recorded=true;
      // Detailed hits are bounded and available only in an explicit test/debug process.
      wchar_t debug[12]={};if(GetEnvironmentVariableW(L"SOULU_UI_TEST_PORT",debug,12)&&adblock_hits_->GetSize()<200){
        auto hit=CefDictionaryValue::Create();hit->SetString("site",SiteDomain(top));
        hit->SetString("requestId",std::to_string(request->GetIdentifier()));
        hit->SetString("url",url);hit->SetInt("type",request->GetResourceType());hit->SetString("rule",rule);
        hit->SetDouble("timestamp",static_cast<double>(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count()));
        adblock_hits_->SetDictionary(adblock_hits_->GetSize(),hit);}}}}
  // No bytes from a matched resource are fetched: cancel synchronously on CEF IO.
  return blocked;
}

bool BrowserClient::OnRequestMediaAccessPermission(CefRefPtr<CefBrowser>,CefRefPtr<CefFrame>,
    const CefString& origin,uint32_t requested,CefRefPtr<CefMediaAccessCallback> callback) {
  CEF_REQUIRE_UI_THREAD();std::vector<std::string> names;
  const uint32_t known=CEF_MEDIA_PERMISSION_DEVICE_VIDEO_CAPTURE|CEF_MEDIA_PERMISSION_DEVICE_AUDIO_CAPTURE;
  if(requested&~known){callback->Continue(0);return true;}
  if(requested&CEF_MEDIA_PERMISSION_DEVICE_VIDEO_CAPTURE)names.push_back("camera");
  if(requested&CEF_MEDIA_PERMISSION_DEVICE_AUDIO_CAPTURE)names.push_back("microphone");
  owner_->RequestSitePermissions(tab_id_,origin,names,[callback,requested](bool allowed){
    callback->Continue(allowed?requested:0);});return true;
}
bool BrowserClient::OnShowPermissionPrompt(CefRefPtr<CefBrowser>,uint64_t prompt_id,
    const CefString& origin,uint32_t requested,CefRefPtr<CefPermissionPromptCallback> callback) {
  CEF_REQUIRE_UI_THREAD();std::vector<std::string> names;
  const std::pair<uint32_t,const char*> supported[]={
    {CEF_PERMISSION_TYPE_GEOLOCATION,"geolocation"},{CEF_PERMISSION_TYPE_NOTIFICATIONS,"notifications"},
    {CEF_PERMISSION_TYPE_CAMERA_STREAM,"camera"},{CEF_PERMISSION_TYPE_MIC_STREAM,"microphone"},
    {CEF_PERMISSION_TYPE_MULTIPLE_DOWNLOADS,"downloads"}};
  uint32_t known=0;for(const auto& item:supported)known|=item.first;
  if(requested&~known){callback->Continue(CEF_PERMISSION_RESULT_DENY);return true;}
  for(const auto& [flag,name]:supported)if(requested&flag)names.push_back(name);
  auto owner=owner_;const int tab_id=tab_id_;const std::string requested_origin=origin;
  owner_->RequestSitePermissions(tab_id_,origin,names,[callback,owner,tab_id,requested_origin,names](bool allowed){
    auto policy=owner->PolicyForTab(tab_id);bool blocked=false;
    if(policy)for(const auto& name:names)if(policy->Rule(requested_origin,name)==2)blocked=true;
    callback->Continue(allowed?CEF_PERMISSION_RESULT_ACCEPT:
      blocked?CEF_PERMISSION_RESULT_DENY:CEF_PERMISSION_RESULT_DISMISS);},prompt_id);
  return true;
}
void BrowserClient::OnDismissPermissionPrompt(CefRefPtr<CefBrowser>,uint64_t prompt_id,
    cef_permission_request_result_t) {
  CEF_REQUIRE_UI_THREAD();owner_->CancelSitePermissions(tab_id_,prompt_id,false);
}
void BrowserClient::OnLoadEnd(CefRefPtr<CefBrowser>,CefRefPtr<CefFrame> frame,int status) {
  if(frame->IsMain()&&role_!=BrowserRole::kShell&&status>=200&&status<400)owner_->RecordHistory(tab_id_);
  if(frame->IsMain()&&role_!=BrowserRole::kShell){owner_->ReaderDocumentLoaded(tab_id_);owner_->ApplySiteSound();owner_->ContentPageLoaded(tab_id_);}
}
bool BrowserClient::OnBeforeBrowse(CefRefPtr<CefBrowser> browser,CefRefPtr<CefFrame> frame,
    CefRefPtr<CefRequest> request,bool,bool) {
  if (frame->IsMain() && owner_->GuardSettingsNavigation(tab_id_, request->GetURL())) return true;
  CEF_REQUIRE_UI_THREAD();if(router_)router_->OnBeforeBrowse(browser,frame);
  if(role_!=BrowserRole::kShell&&frame->IsMain()){
    {std::lock_guard lock(adblock_mutex_);adblock_top_=request->GetURL();
      ++adblock_generation_;adblock_blocked_=0;adblock_checked_=0;adblock_hits_->Clear();}
    owner_->ResetHistoryVisit(tab_id_);
    owner_->ReaderDocumentNavigation(tab_id_);owner_->SyncSitePolicy(tab_id_,request->GetURL());
  }
  return false;
}

void BrowserClient::OnBeforeContextMenu(CefRefPtr<CefBrowser> browser,CefRefPtr<CefFrame> frame,
    CefRefPtr<CefContextMenuParams> params,CefRefPtr<CefMenuModel> model){
  CEF_REQUIRE_UI_THREAD();const bool en=owner_->MenuEnglish();
  auto label=[&](const char* ru,const char* english){return en?english:ru;};
  // Preserve CEF editing and spellchecking, including enabled states.
  if(params->IsEditable()){
    const std::tuple<int,const char*,const char*> labels[]={
      {MENU_ID_UNDO,"Отменить","Undo"},{MENU_ID_REDO,"Повторить","Redo"},
      {MENU_ID_CUT,"Вырезать","Cut"},{MENU_ID_COPY,"Копировать","Copy"},
      {MENU_ID_PASTE,"Вставить","Paste"},{MENU_ID_SELECT_ALL,"Выделить всё","Select all"},
      {MENU_ID_DELETE,"Удалить","Delete"},
      {MENU_ID_NO_SPELLING_SUGGESTIONS,"Нет вариантов исправления","No spelling suggestions"},
      {MENU_ID_ADD_TO_DICTIONARY,"Добавить в словарь","Add to dictionary"}};
    for(const auto& [id,ru,english]:labels)if(model->GetIndexOf(id)>=0)model->SetLabel(id,label(ru,english));
    return;
  }
  const bool internal=owner_->IsTrustedUi(frame->GetURL())||owner_->IsHomeUi(frame->GetURL())||owner_->IsHistoryUi(frame->GetURL())||owner_->IsOnboardingUi(frame->GetURL());
  model->Clear();
  if(internal){if(!params->GetSelectionText().empty())model->AddItem(MENU_ID_COPY,label("Копировать","Copy"));return;}
  auto add=[&](int id,const char* ru,const char* english,bool enabled=true){model->AddItem(id,label(ru,english));model->SetEnabled(id,enabled);};
  const auto link=params->GetLinkUrl().ToString(),source=params->GetSourceUrl().ToString();
  if(!link.empty()){
    const bool web=DownloadableLink(link);
    add(kLinkForeground,"Открыть ссылку в новой вкладке","Open link in new tab",web);
    add(kLinkBackground,"Открыть ссылку в фоновой вкладке","Open link in background tab",web);
    add(kLinkWindow,"Открыть ссылку в новом окне","Open link in new window",web);
    add(kLinkIncognito,"Открыть ссылку в окне инкогнито","Open link in incognito window",web);
    model->AddSeparator();add(kLinkSave,"Сохранить ссылку как…","Save link as…",web);add(kLinkCopy,"Копировать адрес ссылки","Copy link address");
  }
  const bool image=params->GetMediaType()==CM_MEDIATYPE_IMAGE;
  if(image){
    if(model->GetCount())model->AddSeparator();
    add(kImageOpen,"Открыть изображение в новой вкладке","Open image in new tab",DownloadableLink(source));
    add(kImageSave,"Сохранить изображение как…","Save image as…",DownloadableLink(source));
    add(kImageCopy,"Копировать изображение","Copy image",params->HasImageContents());
    add(kImageCopyAddress,"Копировать адрес изображения","Copy image address",!source.empty());
  }
  if(params->GetMediaType()==CM_MEDIATYPE_VIDEO||params->GetMediaType()==CM_MEDIATYPE_AUDIO){
    if(model->GetCount())model->AddSeparator();
    const auto flags=params->GetMediaStateFlags();
    add(kMediaPlay,(flags&CM_MEDIAFLAG_PAUSED)?"Воспроизвести":"Пауза",(flags&CM_MEDIAFLAG_PAUSED)?"Play":"Pause");
    add(kMediaMute,(flags&CM_MEDIAFLAG_MUTED)?"Включить звук":"Выключить звук",(flags&CM_MEDIAFLAG_MUTED)?"Unmute":"Mute",(flags&CM_MEDIAFLAG_HAS_AUDIO)!=0);
    model->AddCheckItem(kMediaLoop,label("Повторять","Loop"));model->SetChecked(kMediaLoop,(flags&CM_MEDIAFLAG_LOOP)!=0);
    model->AddCheckItem(kMediaControls,label("Показывать элементы управления","Show controls"));model->SetChecked(kMediaControls,(flags&CM_MEDIAFLAG_CONTROLS)!=0);
    add(kMediaSave,"Сохранить медиа как…","Save media as…",DownloadableLink(source));add(kMediaCopy,"Копировать адрес медиа","Copy media address",!source.empty());
  }
  if(!params->GetSelectionText().empty()){
    if(model->GetCount())model->AddSeparator();add(MENU_ID_COPY,"Копировать","Copy");
    std::string selected=params->GetSelectionText().ToString();if(selected.size()>80)selected=selected.substr(0,77)+"…";
    model->AddItem(kSelectionSearch,std::string(en?"Search for “":"Искать «")+selected+(en?"”":"»"));
  }
  if(!model->GetCount()){
    add(MENU_ID_BACK,"Назад","Back",browser->CanGoBack());add(MENU_ID_FORWARD,"Вперёд","Forward",browser->CanGoForward());
    add(MENU_ID_RELOAD,"Перезагрузить","Reload");model->AddSeparator();
    add(kPageSave,"Сохранить как…","Save as…",DownloadableLink(params->GetPageUrl()));add(MENU_ID_PRINT,"Печать…","Print…");
    if(owner_->MenuReaderAvailable(tab_id_))add(kPageReader,"Открыть в режиме чтения","Open in Reader mode");
    model->AddSeparator();add(kPageQR,"Создать QR-код этой страницы","Create page QR code",DownloadableLink(params->GetPageUrl()));
    const bool targetEnglish=owner_->MenuTranslationTarget(tab_id_)=="en";
    add(kPageTranslate,targetEnglish?"Перевести на английский":"Перевести на русский",targetEnglish?"Translate to English":"Translate to Russian",DownloadableLink(params->GetPageUrl()));
    model->AddSeparator();add(MENU_ID_VIEW_SOURCE,"Просмотр кода страницы","View page source");
  }
  if(model->GetCount())model->AddSeparator();add(kInspect,"Просмотреть код","Inspect");
}

bool BrowserClient::RunContextMenu(CefRefPtr<CefBrowser> browser,
    CefRefPtr<CefFrame>, CefRefPtr<CefContextMenuParams> params,
    CefRefPtr<CefMenuModel> model, CefRefPtr<CefRunContextMenuCallback> callback) {
  CEF_REQUIRE_UI_THREAD();
  // All browser roles use the browser-owned host; their CEF models retain context-specific commands.
  // Copy CEF's transient model before entering a nested menu loop.
  auto copy=[&](auto&& recurse,CefRefPtr<CefMenuModel> source)->MenuModel {
    MenuModel result;
    for(size_t i=0;i<source->GetCount();++i){
      if(source->GetTypeAt(i)==MENUITEMTYPE_SEPARATOR){result.push_back(MenuItem::Separator());continue;}
      MenuItem item;item.command=source->GetCommandIdAt(i);item.label=source->GetLabelAt(i).ToWString();
      if(item.command<MENU_ID_USER_FIRST)item.label=MenuLabel(item.label);
      auto tab=item.label.find(L'\t');if(tab!=std::wstring::npos){item.accelerator=item.label.substr(tab+1);item.label.resize(tab);}
      switch(item.command){case MENU_ID_BACK:item.accelerator=L"Alt+←";break;case MENU_ID_FORWARD:item.accelerator=L"Alt+→";break;case MENU_ID_RELOAD:item.accelerator=L"Ctrl+R";break;case MENU_ID_PRINT:item.accelerator=L"Ctrl+P";break;case MENU_ID_VIEW_SOURCE:item.accelerator=L"Ctrl+U";break;case kPageSave:item.accelerator=L"Ctrl+S";break;case MENU_ID_COPY:item.accelerator=L"Ctrl+C";break;case MENU_ID_CUT:item.accelerator=L"Ctrl+X";break;case MENU_ID_PASTE:item.accelerator=L"Ctrl+V";break;case MENU_ID_SELECT_ALL:item.accelerator=L"Ctrl+A";break;}
      item.enabled=source->IsEnabledAt(i);item.checked=source->IsCheckedAt(i);
      if(source->GetTypeAt(i)==MENUITEMTYPE_CHECK)item.type=MenuItemType::Check;
      if(source->GetTypeAt(i)==MENUITEMTYPE_RADIO)item.type=MenuItemType::Radio;
      if(auto child=source->GetSubMenuAt(i)){item.type=MenuItemType::Submenu;item.children=recurse(recurse,child);}
      result.push_back(std::move(item));
    }return result;
  };
  auto snapshot=copy(copy,model);
  POINT point={params->GetXCoord(),params->GetYCoord()};
  ClientToScreen(browser->GetHost()->GetWindowHandle(),&point);
  CefRefPtr<BrowserClient> keep_alive(this);
  const std::string menu_url=browser->GetMainFrame()->GetURL();
  auto show=[keep_alive,browser,callback,point,menu_url,snapshot=std::move(snapshot)](CefRefPtr<CefDictionaryValue> hit) mutable {
    if(!browser->IsValid()||browser->GetMainFrame()->GetURL()!=menu_url||!keep_alive->owner_->MenuTabActive(keep_alive->tab_id_)||!IsWindow(keep_alive->owner_->hwnd())){callback->Cancel();return;}
    if(hit&&hit->GetBool("readonly")){
      const bool en=keep_alive->owner_->MenuEnglish();snapshot.clear();
      snapshot.push_back(MenuItem{MENU_ID_COPY,en?L"Copy":L"Копировать"});snapshot.back().accelerator=L"Ctrl+C";snapshot.back().enabled=hit->GetBool("selected");
      snapshot.push_back(MenuItem{MENU_ID_SELECT_ALL,en?L"Select all":L"Выделить всё"});snapshot.back().accelerator=L"Ctrl+A";
    }
    const int command=ShowSouluMenu(keep_alive->owner_->hwnd(),point,std::move(snapshot),{keep_alive->owner_->MenuDark()});
    if(command)callback->Continue(command,EVENTFLAG_NONE);else callback->Cancel();
  };
  if(!params->IsEditable()&&(params->GetEditStateFlags()&CM_EDITFLAG_CAN_SELECT_ALL)){
    const std::string expression="(()=>{const e=document.elementFromPoint("+std::to_string(params->GetXCoord())+","+std::to_string(params->GetYCoord())+");return {readonly:!!(e&&e.matches('input,textarea')&&e.readOnly&&!e.disabled),selected:!!(e&&e.selectionEnd>e.selectionStart)}})()";
    EvaluateTranslationPage(browser,browser->GetMainFrame()->GetURL(),expression,std::move(show));
  }else show(nullptr);
  return true;
}

bool BrowserClient::OnContextMenuCommand(CefRefPtr<CefBrowser> browser,
    CefRefPtr<CefFrame>, CefRefPtr<CefContextMenuParams> params,
    int command, EventFlags) {
  CEF_REQUIRE_UI_THREAD();
  if(role_!=BrowserRole::kContent)return false;
  if(command==kPageTranslate){owner_->MenuTranslate(tab_id_);return true;}
  if(command==kPageQR){owner_->MenuQR(tab_id_);return true;}
  if(command==kPageReader){owner_->MenuReader(tab_id_);return true;}
  if(command==kPageSave){if(DownloadableLink(params->GetPageUrl()))browser->GetHost()->StartDownload(params->GetPageUrl());return true;}
  if(command==kSelectionSearch){owner_->SearchSelection(tab_id_,browser,params->GetSelectionText());return true;}
  if(command==kInspect){CefWindowInfo info;info.SetAsPopup(owner_->hwnd(),"Soulu Developer Tools");CefBrowserSettings settings;browser->GetHost()->ShowDevTools(info,nullptr,settings,CefPoint(params->GetXCoord(),params->GetYCoord()));return true;}
  if(command==kImageOpen||command==kImageSave||command==kMediaSave){const std::string source=params->GetSourceUrl();if(DownloadableLink(source)){if(command==kImageOpen)owner_->OpenTabFrom(tab_id_,browser,source,false);else browser->GetHost()->StartDownload(source);}return true;}
  if(command==kImageCopy){browser->GetHost()->DownloadImage(params->GetSourceUrl(),false,0,false,new CopyImage(owner_->hwnd()));return true;}
  if(command>=kMediaPlay&&command<=kMediaControls){
    std::string code="(()=>{const element=document.elementFromPoint("+std::to_string(params->GetXCoord())+","+std::to_string(params->GetYCoord())+");const m=element?.closest('video,audio');if(!m)return {};";
    if(command==kMediaPlay)code+="if(m.paused)m.play().catch(()=>{});else m.pause();";
    else if(command==kMediaMute)code+="m.muted=!m.muted;";
    else if(command==kMediaLoop)code+="m.loop=!m.loop;";
    else code+="m.controls=!m.controls;";
    code+="return {changed:true};})()";EvaluateTranslationPage(browser,browser->GetMainFrame()->GetURL(),code,[](auto){});return true;
  }
  if(command==kLinkWindow){owner_->OpenLinkWindow(tab_id_,browser,params->GetLinkUrl(),false);return true;}
  if(params->GetLinkUrl().empty()&&command!=kImageCopyAddress&&command!=kMediaCopy)return false;
  const std::string url = params->GetLinkUrl();
  switch (command) {
    case kLinkForeground:
    case kLinkBackground:
      if (DownloadableLink(url))
        owner_->OpenTabFrom(tab_id_, browser, url, command == kLinkBackground);
      return true;
    case kLinkIncognito:
      if (DownloadableLink(url)) owner_->OpenLinkWindow(tab_id_, browser, url, true);
      return true;
    case kLinkSave:
      if (DownloadableLink(url)) browser->GetHost()->StartDownload(url);
      return true;
    case kImageCopyAddress:
    case kMediaCopy:
    case kLinkCopy: {
      const std::wstring wide = command==kLinkCopy?params->GetLinkUrl().ToWString():params->GetSourceUrl().ToWString();
      HGLOBAL memory = GlobalAlloc(GMEM_MOVEABLE, (wide.size() + 1) * sizeof(wchar_t));
      if (!memory) return true;
      void* buffer = GlobalLock(memory);
      if (!buffer) { GlobalFree(memory); return true; }
      memcpy(buffer, wide.c_str(), (wide.size() + 1) * sizeof(wchar_t));
      GlobalUnlock(memory);
      if (OpenClipboard(owner_->hwnd())) {
        EmptyClipboard();
        if (SetClipboardData(CF_UNICODETEXT, memory)) memory = nullptr;
        CloseClipboard();
      }
      if (memory) GlobalFree(memory);
      return true;
    }
    default: return false;
  }
}

CefRefPtr<CefRenderHandler> BrowserClient::GetRenderHandler() {
  return role_ == BrowserRole::kShell ? owner_->surface() : nullptr;
}
bool BrowserClient::OnCursorChange(CefRefPtr<CefBrowser>, CefCursorHandle cursor, cef_cursor_type_t, const CefCursorInfo&) {
  if (role_ != BrowserRole::kShell || !owner_->surface()) return false;
  owner_->surface()->Cursor(cursor); return true;
}

bool BrowserClient::OnProcessMessageReceived(CefRefPtr<CefBrowser> browser,
                                             CefRefPtr<CefFrame> frame,
                                             CefProcessId source_process,
                                             CefRefPtr<CefProcessMessage> message) {
  CEF_REQUIRE_UI_THREAD();
  if(role_==BrowserRole::kContent&&source_process==PID_RENDERER&&frame&&
     message->GetName()=="soulu.adblock.cosmetic") {
    auto args=message->GetArgumentList();
    if(args->GetSize()!=1||args->GetType(0)!=VTYPE_STRING||args->GetString(0).length()>65536)return true;
    std::string top;{std::lock_guard lock(adblock_mutex_);top=adblock_top_;}
    auto reply=CefProcessMessage::Create("soulu.adblock.selectors");
    const bool enabled=policy_&&policy_->Blocking(top)&&!WebOrigin(top).empty()&&!WebOrigin(frame->GetURL()).empty();
    reply->GetArgumentList()->SetBool(0,enabled);
    reply->GetArgumentList()->SetList(1,enabled?CosmeticSelectors(frame->GetURL(),args->GetString(0)):CefListValue::Create());
    frame->SendProcessMessage(PID_RENDERER,reply);return true;
  }
  if(role_!=BrowserRole::kShell&&source_process==PID_RENDERER&&
     message->GetName()=="soulu.credential.submit") {
    auto args=message->GetArgumentList();
    if(args->GetSize()==3 && args->GetType(0)==VTYPE_STRING&&args->GetType(1)==VTYPE_STRING&&args->GetType(2)==VTYPE_STRING)
      owner_->OfferCredential(tab_id_,frame,args->GetString(0),args->GetString(1),args->GetString(2));
    return true;
  }
  return router_ && router_->OnProcessMessageReceived(browser, frame, source_process, message);
}

void BrowserClient::OnAfterCreated(CefRefPtr<CefBrowser> browser) {
  CEF_REQUIRE_UI_THREAD();
  if (popup_opener_) {
    popup_opener_->pending_popups_.erase(opener_popup_id_);
    popup_opener_ = nullptr;
  }
  // Every browser gets a router. Settings has its own role and host, and the
  // bridge binds editing requests to that browser rather than an active tab.
  CefMessageRouterConfig config;
  router_ = CefMessageRouterBrowserSide::Create(config);
  bridge_ = std::make_unique<BridgeHandler>(owner_, tab_id_);
  router_->AddHandler(bridge_.get(), false);
  if (role_ == BrowserRole::kShell) owner_->AttachShell(browser);
  else if (role_ == BrowserRole::kSettings) owner_->AttachSettings(browser);
  else owner_->AttachContent(tab_id_, browser);
}

bool BrowserClient::OnOpenURLFromTab(CefRefPtr<CefBrowser> browser,
    CefRefPtr<CefFrame>, const CefString& url, WindowOpenDisposition disposition,
    bool) {
  CEF_REQUIRE_UI_THREAD();
  if (role_ == BrowserRole::kShell) return false;
  if (owner_->IsSettingsUrl(url)) { owner_->GuardSettingsNavigation(tab_id_, url); return true; }
  if (role_ == BrowserRole::kSettings) { owner_->GuardSettingsNavigation(tab_id_, url); return true; }
  switch (disposition) {
    case CEF_WOD_NEW_FOREGROUND_TAB:
    case CEF_WOD_NEW_BACKGROUND_TAB:
    case CEF_WOD_NEW_WINDOW:
    case CEF_WOD_NEW_POPUP:
      owner_->OpenTabFrom(tab_id_, browser, url,
                         disposition == CEF_WOD_NEW_BACKGROUND_TAB);
      return true;
    default:
      return false;
  }
}

bool BrowserClient::OnBeforePopup(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame>,
    int popup_id, const CefString& url, const CefString&,
    WindowOpenDisposition disposition, bool gesture, const CefPopupFeatures&,
    CefWindowInfo& info, CefRefPtr<CefClient>& client, CefBrowserSettings&,
    CefRefPtr<CefDictionaryValue>& extra_info, bool*) {
  CEF_REQUIRE_UI_THREAD();
  if (role_ != BrowserRole::kContent) return true;
  const bool popup_request=!gesture||disposition==CEF_WOD_NEW_POPUP||disposition==CEF_WOD_NEW_WINDOW;
  if(popup_request&&!owner_->AllowSite(tab_id_,browser->GetMainFrame()->GetURL(),"popups"))return true;
  const int id = owner_->PreparePopup(tab_id_, url,
      disposition == CEF_WOD_NEW_BACKGROUND_TAB, info);
  if (!id) return true;
  CefRefPtr<BrowserClient> popup_client =
      new BrowserClient(owner_, BrowserRole::kContent, id);
  popup_client->popup_opener_ = this;
  popup_client->opener_popup_id_ = popup_id;
  client = popup_client;
  pending_popups_[popup_id] = id;
  if(!extra_info)extra_info=CefDictionaryValue::Create();
  extra_info->SetBool("souluIncognito",owner_->IsIncognitoTab(tab_id_));
  // Let CEF create the real popup, retaining its opener and request context.
  return false;
}

void BrowserClient::OnBeforePopupAborted(CefRefPtr<CefBrowser>, int popup_id) {
  CEF_REQUIRE_UI_THREAD();
  auto it = pending_popups_.find(popup_id);
  if (it == pending_popups_.end()) return;
  owner_->AbortPopup(it->second);
  pending_popups_.erase(it);
}

bool BrowserClient::DoClose(CefRefPtr<CefBrowser> browser) {
  CEF_REQUIRE_UI_THREAD();
  if (role_ == BrowserRole::kShell) return false;
  // Alloy's default close targets the top-level parent. A tab must destroy
  // only its own child HWND, allowing OnBeforeClose to update the tab manager.
  // The Soulu host stays alive until every browser and cookie flush completes.
  const HWND child = browser->GetHost()->GetWindowHandle();
  if (child && IsWindow(child)) DestroyWindow(child);
  return true;
}

void BrowserClient::OnBeforeClose(CefRefPtr<CefBrowser> browser) {
  CEF_REQUIRE_UI_THREAD();
  if (router_) {
    router_->RemoveHandler(bridge_.get());
    bridge_.reset();
    router_ = nullptr;
  }
  for (const auto& popup : pending_popups_) owner_->AbortPopup(popup.second);
  pending_popups_.clear();
  if (role_ == BrowserRole::kSettings) owner_->SettingsClosed(browser);
  else owner_->BrowserClosed(browser, tab_id_, role_ == BrowserRole::kShell);
}

void BrowserClient::OnTitleChange(CefRefPtr<CefBrowser>, const CefString& title) {
  if (role_ != BrowserRole::kShell) owner_->UpdateTitle(tab_id_, title);
}

void BrowserClient::OnAddressChange(CefRefPtr<CefBrowser>, CefRefPtr<CefFrame> frame,
                                    const CefString& url) {
  if (role_ != BrowserRole::kShell && frame->IsMain()) {
    {std::lock_guard lock(adblock_mutex_);adblock_top_=url;}
    owner_->UpdateAddress(tab_id_, url);
  }
}

void BrowserClient::OnFaviconURLChange(CefRefPtr<CefBrowser>,
                                       const std::vector<CefString>& icon_urls) {
  if (role_ != BrowserRole::kShell)
    owner_->UpdateFavicon(tab_id_, icon_urls.empty() ? "" : icon_urls.front());
}

void BrowserClient::OnLoadingStateChange(CefRefPtr<CefBrowser>, bool loading,
                                         bool can_go_back, bool) {
  if (role_ != BrowserRole::kShell)
    owner_->UpdateLoading(tab_id_, loading, can_go_back);
  if (!loading && role_ != BrowserRole::kShell) owner_->ApplyContentTheme();
}

bool BrowserClient::OnBeforeDownload(CefRefPtr<CefBrowser> browser,
                                     CefRefPtr<CefDownloadItem>,
                                     const CefString& suggested_name,
                                     CefRefPtr<CefBeforeDownloadCallback> callback) {
  const std::string site=browser->GetMainFrame()->GetURL();
  owner_->RequestSitePermissions(tab_id_,site,{"downloads"},[callback,suggested_name](bool allowed){
    if(allowed)callback->Continue(suggested_name,true);
  });
  return true;
}

void BrowserClient::OnDownloadUpdated(CefRefPtr<CefBrowser>,
                                      CefRefPtr<CefDownloadItem> item,
                                      CefRefPtr<CefDownloadItemCallback>) {
  owner_->UpdateDownload(tab_id_,item);
}
}

