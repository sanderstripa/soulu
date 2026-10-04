#include "examples/soulu/translation_model_download.h"
#include "examples/soulu/browser_window.h"
#include "examples/soulu/isolated_page_job.h"
#include "include/cef_parser.h"
#include <filesystem>
#include <fstream>

namespace soulu {
namespace {
CefRefPtr<CefValue> Value(CefRefPtr<CefDictionaryValue> dictionary){auto value=CefValue::Create();value->SetDictionary(dictionary);return value;}
class MenuCallback final:public CefMessageRouterBrowserSide::Callback {
 public:void Success(const CefString&) override{} void Success(const void*,size_t) override{} void Failure(int,const CefString&) override{}
 private:IMPLEMENT_REFCOUNTING(MenuCallback);
};
}
bool BrowserWindow::MenuReaderAvailable(int id) const {
  for(const auto& tab:tabs_)if(tab.id==id)return tab.reader_article!=nullptr&&!tab.main_loading&&!tab.reader_active;
  return false;
}
void BrowserWindow::MenuReader(int id){
  if(id!=active_tab_id_||!MenuReaderAvailable(id))return;
  HandleSiteAction("browser.site.reader.enter",Value(SiteSnapshot(id)),new MenuCallback());
}
void BrowserWindow::MenuTranslate(int id){
  if(auto* tab=FindTab(id);tab&&tab->browser&&!tab->main_loading&&!tab->reader_active){Emit("translateRequest",Value(SiteSnapshot(id)));}
}
void BrowserWindow::MenuQR(int id){
  if(auto* tab=FindTab(id);tab&&!WebOrigin(tab->url).empty())Emit("qrRequest",Value(SiteSnapshot(id)));
}
bool BrowserWindow::HandleTranslationBridge(const std::string& action,CefRefPtr<CefValue> payload,
    CefRefPtr<CefMessageRouterBrowserSide::Callback> callback){
  if(action.rfind("browser.translate.",0)!=0)return false;
  auto data=payload&&payload->GetType()==VTYPE_DICTIONARY?payload->GetDictionary():nullptr;
  if(action=="browser.translate.model"){DownloadTranslationModel(data?data->GetString("sha256").ToString():"",callback);return true;}
  auto* tab=data?FindTab(data->GetInt("tabId")):nullptr;
  if(!tab||!tab->browser||tab->main_loading||tab->reader_active||
     data->GetString("url")!=tab->url||data->GetInt("generation")!=tab->document_generation){callback->Failure(409,"Page changed");return true;}
  if(action=="browser.translate.preferences"){
    if(!tab->incognito&&tab->profile_id!=active_profile_id_){callback->Failure(409,"Profile changed");return true;}
    auto preferences=tab->incognito?tab->translation_preferences:settings_->GetDictionary("translation");
    if(!preferences){preferences=CefDictionaryValue::Create();preferences->SetString("target",MenuEnglish()?"en":"ru");preferences->SetList("always",CefListValue::Create());preferences->SetList("never",CefListValue::Create());}
    auto updated=preferences->Copy(false);
    if(data->HasKey("target")){auto target=data->GetString("target").ToString();if(target!="en"&&target!="ru"&&target!="de"){callback->Failure(400,"Unsupported target");return true;}updated->SetString("target",target);}
    for(const auto& name:{"always","never"})if(data->HasKey(name)){
      if(data->GetType(name)!=VTYPE_BOOL){callback->Failure(400,"Invalid preference");return true;}
      const std::string item=std::string(name)=="always"?data->GetString("source").ToString():WebOrigin(tab->url);
      if(item.empty()||(std::string(name)=="always"&&item!="en"&&item!="ru"&&item!="de")){callback->Failure(400,"Invalid language or site");return true;}
      auto old=updated->GetList(name),next=CefListValue::Create();
      if(old)for(size_t i=0;i<old->GetSize();++i)if(old->GetString(i)!=item)next->SetString(next->GetSize(),old->GetString(i));
      if(data->GetBool(name))next->SetString(next->GetSize(),item);
      if(next->GetSize()>500){callback->Failure(400,"Preference limit reached");return true;}updated->SetList(name,next);
    }
    if(tab->incognito)tab->translation_preferences=updated;
    else {settings_->SetDictionary("translation",updated);if(!SaveSettings()){callback->Failure(500,"Preferences could not be saved");return true;}}
    callback->Success(CefWriteJSON(Value(updated),JSON_WRITER_DEFAULT));return true;
  }
  // Translation can run in a background tab, but only an explicit browser UI
  // request can begin it. The content page has no bridge into this handler.
  const int id=tab->id,generation=tab->document_generation;
  if(action=="browser.translate.begin"){
    if(id!=active_tab_id_){callback->Failure(409,"Tab changed");return true;}
    ++tab->translation_generation;tab->translation_active=true;
    auto result=CefDictionaryValue::Create();result->SetInt("token",tab->translation_generation);
    callback->Success(CefWriteJSON(Value(result),JSON_WRITER_DEFAULT));return true;
  }
  if(action!="browser.translate.probe"&&data->GetInt("token")!=tab->translation_generation){callback->Failure(409,"Translation cancelled");return true;}
  const int token=tab->translation_generation;const auto url=tab->url;
  std::string script;
  wchar_t module[32768]={};GetModuleFileNameW(nullptr,module,32768);
  std::ifstream input(std::filesystem::path(module).parent_path()/L"ui"/L"translation-dom.js",std::ios::binary);
  if(!input){callback->Failure(500,"Translation resources unavailable");return true;}
  script.assign(std::istreambuf_iterator<char>(input),{});script+=';';
  if(action=="browser.translate.probe")script+="globalThis.__souluTranslate.probe()";
  else if(action=="browser.translate.collect"){
    if(!tab->translation_active){callback->Failure(409,"Translation inactive");return true;}
    script+="globalThis.__souluTranslate.collect()";
  }else if(action=="browser.translate.restore"){
    tab->translation_active=false;++tab->translation_generation;script+="globalThis.__souluTranslate.restore()";
  }else if(action=="browser.translate.apply"){
    auto rows=data->GetList("rows");
    if(!tab->translation_active||!rows||rows->GetSize()>32){callback->Failure(400,"Invalid translation batch");return true;}
    for(size_t i=0;i<rows->GetSize();++i){auto row=rows->GetDictionary(i);
      if(!row||row->GetType("id")!=VTYPE_INT||row->GetType("text")!=VTYPE_STRING||row->GetString("text").length()>32000){callback->Failure(400,"Invalid translation result");return true;}}
    auto value=CefValue::Create();value->SetList(rows->Copy());script+="globalThis.__souluTranslate.apply("+CefWriteJSON(value,JSON_WRITER_DEFAULT).ToString()+")";
  }else{callback->Failure(400,"Unknown translation action");return true;}
  CefRefPtr<BrowserWindow> self=this;const bool restore=action=="browser.translate.restore",probe=action=="browser.translate.probe";
  EvaluateTranslationPage(tab->browser,url,script,[self,id,generation,token,url,restore,probe,callback](CefRefPtr<CefDictionaryValue> result){
    auto* current=self->FindTab(id);
    if(!current||current->url!=url||current->document_generation!=generation||(!restore&&!probe&&current->translation_generation!=token)||!result){callback->Failure(409,"Page changed or translation cancelled");return;}
    callback->Success(CefWriteJSON(Value(result),JSON_WRITER_DEFAULT));
  });return true;
}
}
