#include "examples/sona/browser_window.h"
#include "include/wrapper/cef_helpers.h"
#include <algorithm>
namespace sona {
CefRefPtr<ExtensionService> BrowserWindow::ExtensionsForProfile(const std::string& profile){
  if(extension_services_closing_||closing_||profile=="__incognito__")return nullptr;
  auto& service=extension_services_[profile];if(service)return service;
  for(const auto& item:profiles_)if(item.id==profile){service=CreateExtensionService(item.context);return service;}
  return nullptr;
}
bool BrowserWindow::HandleExtensionBridge(const std::string& action,CefRefPtr<CefValue> payload,
    CefRefPtr<CefMessageRouterBrowserSide::Callback> callback,bool settings_source){
  if(action!="browser.extensions.list"&&action!="browser.extensions.pin"&&action!="browser.extensions.open")return false;
  CEF_REQUIRE_UI_THREAD();auto data=payload&&payload->GetType()==VTYPE_DICTIONARY?payload->GetDictionary():nullptr;
  const std::string profile=settings_source?active_profile_id_:VisibleProfileId();
  if(!data||data->GetString("profile")!=profile||closing_||extension_services_closing_){callback->Failure(409,"Профиль расширений изменился.");return true;}
  if(profile=="__incognito__"){auto result=CefDictionaryValue::Create();result->SetString("profile",profile);result->SetList("items",CefListValue::Create());Reply(callback,result);return true;}
  auto service=ExtensionsForProfile(profile);if(!service){callback->Failure(500,"Не удалось запустить расширения профиля.");return true;}
  CefRefPtr<BrowserWindow> self=this;
  auto reply=[self,callback,profile](CefRefPtr<CefDictionaryValue> result,const std::string& error){
    if(!error.empty()||!result){callback->Failure(500,error.empty()?"Extension operation failed":error);return;}
    result->SetString("profile",profile);self->Reply(callback,result);
  };
  if(action=="browser.extensions.list"){service->List(reply);return true;}
  const std::string id=data->GetString("id");
  if(action=="browser.extensions.pin"){
    if(!settings_source||data->GetType("pinned")!=VTYPE_BOOL){callback->Failure(403,"Закрепление доступно в настройках расширений.");return true;}
    service->Pin(id,data->GetBool("pinned"),reply);return true;
  }
  auto* tab=ActiveTab();
  if(settings_source||settings_overlay_||!tab||!tab->browser||tab->profile_id!=profile){callback->Failure(403,"Выберите обычную вкладку Sona.");return true;}
  const int tab_id=tab->id;const auto browser=tab->browser;
  const auto rect=data->GetDictionary("anchor");
  CefRect anchor(12,8,32,32);if(rect)anchor=CefRect(rect->GetInt("x"),rect->GetInt("y"),std::clamp(rect->GetInt("width"),1,256),std::clamp(rect->GetInt("height"),1,256));
  service->List([self,service,id,profile,tab_id,browser,callback,reply,anchor](CefRefPtr<CefDictionaryValue> result,const std::string& error){
    auto* tab=self->ActiveTab();if(!tab||tab->id!=tab_id||tab->profile_id!=profile||!tab->browser||!tab->browser->IsSame(browser)){callback->Failure(409,"Активная вкладка изменилась.");return;}
    auto items=result?result->GetList("items"):nullptr;bool allowed=false;
    if(items)for(size_t i=0;i<items->GetSize();++i){auto item=items->GetDictionary(i);if(item&&item->GetString("id")==id&&item->GetBool("enabled")&&item->GetBool("pinned")&&item->GetBool("action"))allowed=true;}
    if(!error.empty()||!allowed){callback->Failure(403,error.empty()?"Расширение не закреплено или отключено.":error);return;}
    self->FocusContent(tab);
    if(tab->chrome_host)tab->chrome_host->ArmActionPopup(anchor);
    service->Open(browser,id,reply);
  });return true;
}
}
