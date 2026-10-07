#include "examples/soulu/browser_window.h"
#include "examples/soulu/home_weather.h"
#include "examples/soulu/home_system.h"
#include "include/cef_parser.h"
#include "include/wrapper/cef_helpers.h"
#include <algorithm>
#include <filesystem>

namespace soulu {
namespace {
std::string LocalPage(const char* name) {
  wchar_t executable[32768] = {};
  GetModuleFileNameW(nullptr, executable, 32768);
  const auto path=std::filesystem::path(executable).parent_path()/L"ui"/name;
  std::string value=CefString(path.wstring()).ToString();
  std::replace(value.begin(),value.end(),'\\','/');
  std::string encoded;
  for(unsigned char c:value)encoded+=c==' '?"%20":std::string(1,c);
  return "file:///"+encoded;
}
std::string WebUrl(std::string value) {
  const auto first=value.find_first_not_of(" \t\r\n");
  if(first==std::string::npos || value.size()>4096)return "";
  value=value.substr(first,value.find_last_not_of(" \t\r\n")-first+1);
  if(std::any_of(value.begin(),value.end(),[](unsigned char c){return c<=32||c==127;}))return "";
  if(value.find("://")==std::string::npos)value="https://"+value;
  CefURLParts parts;
  if(!CefParseURL(value,parts))return "";
  const std::string scheme=CefString(&parts.scheme);
  if((scheme!="http"&&scheme!="https")||CefString(&parts.host).empty()||
     !CefString(&parts.username).empty()||!CefString(&parts.password).empty())return "";
  return CefString(&parts.spec);
}
CefRefPtr<CefValue> AsValue(CefRefPtr<CefDictionaryValue> data) {
  auto v=CefValue::Create();v->SetDictionary(data);return v;
}
}

void BrowserWindow::MigrateHomePreferences(CefRefPtr<CefDictionaryValue> saved){
  if(saved&&saved->HasKey("homeWeatherCity")&&!saved->HasKey("homeWeatherMode")&&!saved->GetString("homeWeatherCity").empty())
    settings_->SetString("homeWeatherMode","configured");
  if(saved&&saved->HasKey("homeFavoriteIds"))return;
  auto rows=settings_->GetList("homeShortcuts");if(!rows||!rows->GetSize())return;
  auto marks=bookmarks_->Copy();auto ids=CefListValue::Create();int next=1;
  for(size_t j=0;j<marks->GetSize();++j){auto mark=marks->GetDictionary(j);if(mark)next=std::max(next,mark->GetInt("id")+1);}
  for(size_t i=0;i<std::min<size_t>(rows->GetSize(),12);++i){auto row=rows->GetDictionary(i);if(!row)continue;
    const auto url=WebUrl(row->GetString("url"));if(url.empty())continue;int id=0;
    for(size_t j=0;j<marks->GetSize();++j){auto mark=marks->GetDictionary(j);if(mark&&mark->GetString("profileId")==active_profile_id_&&mark->GetString("url")==url){id=mark->GetInt("id");break;}}
    if(!id){id=next++;auto mark=CefDictionaryValue::Create();mark->SetInt("id",id);mark->SetString("type","url");mark->SetString("title",row->GetString("name"));mark->SetString("url",url);mark->SetString("favicon","");mark->SetString("profileId",active_profile_id_);mark->SetInt("parentId",0);mark->SetInt("order",static_cast<int>(marks->GetSize()));marks->SetDictionary(marks->GetSize(),mark);}
    bool selected=false;for(size_t j=0;j<ids->GetSize();++j)if(ids->GetInt(j)==id){selected=true;break;}
    if(!selected)ids->SetInt(ids->GetSize(),id);
  }
  // A failed writer leaves legacy data untouched; retry reuses existing URLs.
  if(SaveBookmarks(marks)){bookmarks_=marks;settings_->SetList("homeFavoriteIds",ids);}
}

std::string BrowserWindow::InternalUrl(const std::string& url) const {
  if(url=="soulu://home"||url=="soulu://home/")return LocalPage("home.html");
  if(url=="soulu://history"||url=="soulu://history/")return LocalPage("history.html");
  if(url=="soulu://onboarding")return LocalPage("onboarding.html");
  if(url=="about:blank")return LocalPage("start.html");
  return url;
}
bool BrowserWindow::IsHomeUi(const std::string& url) const {
  return url==InternalUrl("soulu://home");
}
std::string BrowserWindow::PageUrl(const std::string& kind,CefRefPtr<CefDictionaryValue> config) const {
  const std::string mode=config->GetString(kind+"Mode");
  if(mode=="blank")return "about:blank";
  if(mode=="custom"){
    const auto url=WebUrl(config->GetString(kind+"Url"));
    return url.empty()?"soulu://home":url;
  }
  return "soulu://home";
}
CefRefPtr<CefDictionaryValue> BrowserWindow::PageSettings(const Tab& tab) const {
  if(tab.incognito)return private_page_settings_?private_page_settings_:settings_;
  if(tab.profile_id==active_profile_id_)return settings_;
  auto config=initial_settings_->Copy(false);
  auto saved=ReadJson(ProfileRoot(tab.profile_id)/L"soulu-settings.json");
  if(saved&&saved->GetType()==VTYPE_DICTIONARY){
    CefDictionaryValue::KeyList keys;saved->GetDictionary()->GetKeys(keys);
    for(const auto& key:keys)config->SetValue(key,saved->GetDictionary()->GetValue(key)->Copy());
  }
  return config;
}
CefRefPtr<CefDictionaryValue> BrowserWindow::HomeState(const Tab& tab) const {
  auto config=PageSettings(tab), data=CefDictionaryValue::Create();
  for(const char* key:{"theme","language","homeProvider","homeWeatherMode","homeWeatherCity","homeWeatherUnits"})
    if(config->HasKey(key))data->SetValue(key,config->GetValue(key)->Copy());
  if(!data->HasKey("homeProvider"))data->SetString("homeProvider","google");
  auto favorites=CefListValue::Create();auto ids=config->GetList("homeFavoriteIds");
  if(ids)for(size_t i=0;i<ids->GetSize();++i)for(size_t j=0;j<bookmarks_->GetSize();++j){
    auto row=bookmarks_->GetDictionary(j);
    if(row&&row->GetInt("id")==ids->GetInt(i)&&row->GetString("profileId")==
       (tab.incognito?private_home_profile_:tab.profile_id)&&!WebUrl(row->GetString("url")).empty())
      favorites->SetDictionary(favorites->GetSize(),row->Copy(false));
  }
  data->SetList("favorites",favorites);
  const auto policy=policies_.find(tab.incognito?"__incognito__":tab.profile_id);
  data->SetBool("homeLocationAllowed",policy!=policies_.end()&&policy->second&&policy->second->Rule("soulu://home","geolocation")==0);
  const std::string theme=config->GetString("theme");
  DWORD light=1,size=sizeof(light);
  RegGetValueW(HKEY_CURRENT_USER,L"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
      L"AppsUseLightTheme",RRF_RT_REG_DWORD,nullptr,&light,&size);
  data->SetString("resolvedTheme",theme=="dark"||(theme=="system"&&!light)?"dark":"light");
  data->SetBool("incognito",tab.incognito);
  data->SetInt("tabId",tab.id);
  return data;
}
void BrowserWindow::RefreshHomePages(int id) {
  for(const auto& tab:tabs_)if(tab.browser && (!id || tab.id==id)){
    auto frame=tab.browser->GetMainFrame();
    if(frame&&IsHomeUi(frame->GetURL()))frame->ExecuteJavaScript(
      "window.souluHomeApply&&window.souluHomeApply("+Json(HomeState(tab))+")",frame->GetURL(),0);
  }
}
void BrowserWindow::ContentPageLoaded(int id) {
  auto* tab=FindTab(id);if(!tab||!tab->browser)return;
  auto frame=tab->browser->GetMainFrame();if(!frame)return;
  if(IsOnboardingUi(frame->GetURL())){if(id==active_tab_id_)tab->browser->GetHost()->SetFocus(true);return;}
  if(IsHomeUi(frame->GetURL())){RefreshHomePages(id);
    if(tab->focus_home_on_load&&id==active_tab_id_&&!SettingsOverlayActive()){
      tab->focus_home_on_load=false;
      tab->browser->GetHost()->SetFocus(true);
      auto text=CefValue::Create();text->SetString(CefString(tab->pending_home_input));
      const auto submit=tab->pending_home_submit;tab->pending_home_input.clear();tab->pending_home_submit=false;
      frame->ExecuteJavaScript("window.souluHomeFocus&&window.souluHomeFocus("+CefWriteJSON(text,JSON_WRITER_DEFAULT).ToString()+","+(submit?"true":"false")+")",frame->GetURL(),0);
    }return;}
  if(frame->GetURL()!=InternalUrl("about:blank"))return;
  const std::string theme=HomeState(*tab)->GetString("resolvedTheme");
  frame->ExecuteJavaScript("document.body.dataset.theme='"+theme+"';document.documentElement.style.background='"+
      (theme=="dark"?std::string("#08090b"):std::string("#fafafa"))+"';",frame->GetURL(),0);
}
void BrowserWindow::HandleHomeBridge(int id,const std::string& request,
    CefRefPtr<CefMessageRouterBrowserSide::Callback> callback) {
  CEF_REQUIRE_UI_THREAD();
  auto* tab=FindTab(id);
  if(!tab||!tab->browser||!IsHomeUi(tab->browser->GetMainFrame()->GetURL())){
    callback->Failure(403,"Home document required");return;
  }
  auto parsed=CefParseJSON(request,JSON_PARSER_RFC);
  if(!parsed||parsed->GetType()!=VTYPE_DICTIONARY){callback->Failure(400,"Invalid request");return;}
  auto root=parsed->GetDictionary();const std::string action=root->GetString("action");
  auto payload=root->GetValue("payload");
  if(action=="home.get"){Reply(callback,HomeState(*tab));return;}
  if(action=="home.navigate"){
    if(!payload||payload->GetType()!=VTYPE_STRING){callback->Failure(400,"Text required");return;}
    // Use exactly the omnibox parser, with this document's profile search engine.
    const auto config=PageSettings(*tab);
    const auto url=NormalizeAddress(payload->GetString(),config->GetString("homeProvider")=="perplexity"?"perplexity":"google");
    if(url!="soulu://home"&&url!="about:blank"&&WebUrl(url).empty()){
      callback->Failure(400,"Only web addresses or search queries are allowed");return;
    }
    ReplyEmpty(callback);tab->browser->GetMainFrame()->LoadURL(InternalUrl(url));return;
  }
  if(action=="home.favorite"){
    if(!payload||payload->GetType()!=VTYPE_DICTIONARY){callback->Failure(400,"Favorite required");return;}
    const int mark=payload->GetDictionary()->GetInt("id");auto favorites=HomeState(*tab)->GetList("favorites");
    for(size_t i=0;i<favorites->GetSize();++i){auto row=favorites->GetDictionary(i);if(row->GetInt("id")==mark){
      ReplyEmpty(callback);NewTab(row->GetString("url"),tab->incognito,!payload->GetDictionary()->GetBool("background"),tab->browser->GetHost()->GetRequestContext(),tab->profile_id);return;}}
    callback->Failure(404,"Favorite not found");return;
  }
  if(action=="home.voice.cancel"){++tab->home_voice_generation;CancelSitePermissions(id);HomeCancelVoice(tab->browser->GetIdentifier());ReplyEmpty(callback);return;}
  if(action=="home.voice"){
    const auto generation=tab->document_generation;const int voice=++tab->home_voice_generation;CefRefPtr<BrowserWindow> self=this;
    RequestSitePermissions(id,"soulu://home",{"microphone"},[self,id,generation,voice,callback](bool allowed){
      auto* current=self->FindTab(id);
      if(!allowed||!current||!current->browser||self->active_tab_id_!=id||!self->IsHomeUi(current->browser->GetMainFrame()->GetURL())||current->document_generation!=generation||current->home_voice_generation!=voice){auto d=CefDictionaryValue::Create();d->SetString("status","denied");self->Reply(callback,d);return;}
      HomeRecognize(current->browser->GetIdentifier(),self->PageSettings(*current)->GetString("language"),
        [self,id,generation,voice,callback](CefRefPtr<CefDictionaryValue> result){auto* t=self->FindTab(id);if(!t||!t->browser||t->document_generation!=generation||t->home_voice_generation!=voice){callback->Failure(410,"Voice request cancelled");return;}self->Reply(callback,result);});
    });return;
  }
  if(action=="home.weather"){
    auto config=PageSettings(*tab)->Copy(false);const auto profile=tab->profile_id;
    const auto file=tab->incognito?std::filesystem::path():ProfileRoot(profile)/L"soulu-weather.json";
    auto context=tab->browser->GetHost()->GetRequestContext();
    auto done=[callback](CefRefPtr<CefDictionaryValue> data){callback->Success(CefWriteJSON(AsValue(data),JSON_WRITER_DEFAULT));};
    if(config->GetString("homeWeatherMode")=="configured"){HomeWeather(profile,file,context,config,nullptr,done);return;}
    // Never interrupt immediate typing with a location prompt on New Tab.
    if(PolicyForTab(id)->Rule("soulu://home","geolocation")!=0){
      HomeWeather(profile,file,context,config,nullptr,done);return;
    }
    CefRefPtr<BrowserWindow> self=this;const auto generation=tab->document_generation;
    RequestSitePermissions(id,"soulu://home",{"geolocation"},[self,id,generation,profile,file,context,config,done](bool allowed){
      auto* t=self->FindTab(id);if(!allowed||!t||t->document_generation!=generation){auto d=CefDictionaryValue::Create();d->SetString("status","unavailable");done(d);return;}
      HomeLocate([profile,file,context,config,done](CefRefPtr<CefDictionaryValue> location){HomeWeather(profile,file,context,config,location,done);});
    });return;
  }
  if(action!="home.set"||!payload||payload->GetType()!=VTYPE_DICTIONARY){
    callback->Failure(403,"Home action not allowed");return;
  }
  auto patch=payload->GetDictionary(),config=PageSettings(*tab)->Copy(false);
  CefDictionaryValue::KeyList allowedKeys;patch->GetKeys(allowedKeys);
  for(const auto& key:allowedKeys)if(key!="homeProvider"){callback->Failure(403,"Home setting not allowed");return;}
  std::string error;
  if(!ValidateHomePatch(patch,config,error)){callback->Failure(400,error);return;}
  if(tab->incognito)private_page_settings_=config;
  else {
    if(!WriteJson(ProfileRoot(tab->profile_id)/L"soulu-settings.json",AsValue(config))){callback->Failure(500,"Could not save home settings");return;}
    if(tab->profile_id==active_profile_id_)settings_=config;
  }
  Reply(callback,HomeState(*tab));RefreshHomePages();EmitState();
}

bool BrowserWindow::ValidateHomePatch(CefRefPtr<CefDictionaryValue> patch,
    CefRefPtr<CefDictionaryValue> config,std::string& error) const {
  CefDictionaryValue::KeyList keys;patch->GetKeys(keys);
  for(const auto& key:keys){
    const std::string name=key;auto value=patch->GetValue(key);
    if(name=="homeProvider"||name=="homeWeatherMode"||name=="homeWeatherUnits"){
      if(value->GetType()!=VTYPE_STRING){error="String required";return false;}
      const std::string text=value->GetString();
      if((name=="homeProvider"&&text!="google"&&text!="perplexity")||
         (name=="homeWeatherMode"&&text!="automatic"&&text!="configured")||
         (name=="homeWeatherUnits"&&text!="celsius"&&text!="fahrenheit")){error="Invalid Home choice";return false;}
      config->SetValue(key,value->Copy());
    }else if(name=="homeFavoriteIds"){
      if(value->GetType()!=VTYPE_LIST||value->GetList()->GetSize()>100){error="Invalid favorites";return false;}
      auto ids=value->GetList();std::set<int> unique;
      for(size_t i=0;i<ids->GetSize();++i)if(ids->GetType(i)!=VTYPE_INT||ids->GetInt(i)<=0||!unique.insert(ids->GetInt(i)).second){error="Invalid favorite ID";return false;}
      config->SetValue(key,value->Copy());
    }else if(name=="homeShortcuts"){
      if(value->GetType()!=VTYPE_LIST||value->GetList()->GetSize()>12){error="At most 12 shortcuts";return false;}
      auto safe=CefListValue::Create(),rows=value->GetList();
      for(size_t i=0;i<rows->GetSize();++i){
        auto row=rows->GetDictionary(i);
        if(!row||row->GetType("name")!=VTYPE_STRING||row->GetString("name").empty()||row->GetString("name").length()>80){error="Invalid shortcut name";return false;}
        const auto url=WebUrl(row->GetString("url"));
        if(url.empty()){error="Invalid shortcut URL";return false;}
        auto item=CefDictionaryValue::Create();item->SetString("name",row->GetString("name"));item->SetString("url",url);
        safe->SetDictionary(i,item);
      }
      config->SetList(name,safe);
    }else if(name=="homeWeatherCity"){
      if(value->GetType()!=VTYPE_STRING||value->GetString().length()>100){error="Invalid city";return false;}
      config->SetValue(key,value->Copy());
    }else if(name=="homeShowLogo"||name=="homeShowSearch"||name=="homeShowWeather"||name=="homeShowShortcuts"||name=="homeShowBackground"){
      if(value->GetType()!=VTYPE_BOOL){error="Boolean required";return false;}config->SetValue(key,value->Copy());
    }else {error="Setting not allowed";return false;}
  }
  return true;
}

bool BrowserWindow::ValidatePagePatch(CefRefPtr<CefDictionaryValue> patch) const {
  for(const char* kind:{"startup","newTab","home","startPage"}){
    const std::string modeKey=std::string(kind)+"Mode",urlKey=std::string(kind)+"Url";
    if(patch->HasKey(modeKey)){
      if(patch->GetType(modeKey)!=VTYPE_STRING)return false;
      const std::string mode=patch->GetString(modeKey);
      if(mode!="soulu"&&mode!="blank"&&mode!="custom"&&!(std::string(kind)=="startup"&&mode=="continue"))return false;
    }
    if(patch->HasKey(urlKey)){
      if(patch->GetType(urlKey)!=VTYPE_STRING)return false;
      const std::string url=patch->GetString(urlKey);
      if(!url.empty()&&WebUrl(url).empty())return false;
    }
  }
  return true;
}

bool BrowserWindow::BufferHomeInput(const CefKeyEvent& event) {
  auto* tab=ActiveTab();
  if(!tab||!tab->focus_home_on_load||tab->url!="soulu://home"||event.type!=KEYEVENT_CHAR||
     (event.modifiers&(EVENTFLAG_CONTROL_DOWN|EVENTFLAG_ALT_DOWN)))return false;
  const auto character=static_cast<wchar_t>(event.character);
  if(character==L'\r'){tab->pending_home_submit=true;return true;}
  if(character==L'\b'){
    if(!tab->pending_home_input.empty()){
      const auto last=tab->pending_home_input.back();tab->pending_home_input.pop_back();
      if(last>=0xdc00&&last<=0xdfff&&!tab->pending_home_input.empty()&&tab->pending_home_input.back()>=0xd800&&tab->pending_home_input.back()<=0xdbff)tab->pending_home_input.pop_back();
    }return true;
  }
  if(character<32)return false;
  if(tab->pending_home_input.size()<4096)tab->pending_home_input+=character;
  return true;
}

bool BrowserWindow::HandlePageShortcut(int id,int key,bool control,bool alt) {
  if(control&&key=='T'){
    auto* tab=FindTab(id);
    NewTab("",tab?tab->incognito:VisibleProfileId()=="__incognito__");return true;
  }
  if(control&&key=='L'){FocusAddress();return true;}
  if(alt&&key==VK_HOME){
    if(auto* tab=ActiveTab();tab&&tab->browser){
      tab->focus_home_on_load=true;tab->browser->GetMainFrame()->LoadURL(InternalUrl(PageUrl("home",PageSettings(*tab))));
    }
    return true;
  }
  return false;
}
void BrowserWindow::ReplaceLastTab(bool incognito,const std::string& profile) {
  if(closing_)return;
  auto next=std::find_if(tabs_.begin(),tabs_.end(),[&](const Tab& t){
    return incognito?t.incognito:!t.incognito&&t.profile_id==profile;
  });
  if(next!=tabs_.end()){active_tab_id_=next->id;if(!next->incognito)last_normal_active_[next->profile_id]=next->id;return;}
  // Last-tab OFF has always opened a blank replacement, independently of Ctrl+T.
  if(incognito){
    auto normal=std::find_if(tabs_.begin(),tabs_.end(),[&](const Tab& t){return !t.incognito&&t.profile_id==active_profile_id_;});
    if(normal!=tabs_.end()){active_tab_id_=normal->id;last_normal_active_[normal->profile_id]=normal->id;return;}
  }
  const auto url=settings_->GetBool("openStartPageAfterLastTab")?PageUrl("startup",settings_):"about:blank";
  NewTab(url,false,true,nullptr,active_profile_id_);
}
void BrowserWindow::SaveSession() {
  for(const auto& profile:profiles_){
    auto data=CefDictionaryValue::Create();auto rows=CefListValue::Create();int active=0;
    for(const auto& tab:tabs_)if(!tab.incognito&&tab.profile_id==profile.id&&rows->GetSize()<100){
      if(tab.url!="about:blank"&&tab.url!="soulu://home"&&WebUrl(tab.url).empty())continue;
      if(tab.id==active_tab_id_||tab.id==last_normal_active_[profile.id])active=static_cast<int>(rows->GetSize());
      rows->SetString(rows->GetSize(),tab.url);
    }
    data->SetList("tabs",rows);data->SetInt("active",active);
    WriteJson(ProfileRoot(profile.id)/L"soulu-session.json",AsValue(data));
  }
}
bool BrowserWindow::RestoreSession() {
  if(settings_->GetString("startupMode")!="continue")return false;
  auto value=ReadJson(ProfileRoot(active_profile_id_)/L"soulu-session.json");
  if(!value||value->GetType()!=VTYPE_DICTIONARY)return false;
  auto data=value->GetDictionary();auto rows=data->GetList("tabs");
  if(!rows||rows->GetSize()==0||rows->GetSize()>100)return false;
  int selected=data->GetInt("active");std::vector<int> ids;
  for(size_t i=0;i<rows->GetSize();++i){
    if(rows->GetType(i)!=VTYPE_STRING)continue;const std::string url=rows->GetString(i);
    if(url!="about:blank"&&url!="soulu://home"&&WebUrl(url).empty())continue;
    const int id=next_tab_id_;NewTab(url,false,false);if(FindTab(id))ids.push_back(id);
  }
  if(ids.empty())return false;
  active_tab_id_=ids[std::clamp(selected,0,static_cast<int>(ids.size())-1)];last_normal_active_[active_profile_id_]=active_tab_id_;return true;
}
}
