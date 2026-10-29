#include "examples/soulu/browser_window.h"
#include "examples/soulu/video_bridge.h"
#include "examples/soulu/video_network.h"
#include "examples/soulu/protected_store.h"
#include "examples/soulu/profile_data.h"
#include "include/cef_parser.h"
#include "include/cef_process_message.h"
namespace soulu {
namespace {
CefRefPtr<CefDictionaryValue> private_values;
bool IsVideoPage(const CefString& raw){CefURLParts p;if(!CefParseURL(raw,p)||CefString(&p.scheme)!="https")return false;const std::string host=CefString(&p.host);return host=="youtube.com"||host=="www.youtube.com"||host=="m.youtube.com"||host=="music.youtube.com"||host=="www.youtube-nocookie.com";}
CefRefPtr<CefValue> WrapVideo(CefRefPtr<CefDictionaryValue> value){auto wrapper=CefValue::Create();wrapper->SetDictionary(value);return wrapper;}
}
CefRefPtr<CefDictionaryValue> VideoPreferences(const std::string& profile){
 auto result=profile=="__incognito__"?(private_values?private_values->Copy(false):CefDictionaryValue::Create()):ReadProtectedStore(profile,"video");
 if(!result)return nullptr;
 if(!result->HasKey("responseLanguage"))result->SetString("responseLanguage","ru");
 if(!result->HasKey("localeLangOverride"))result->SetString("localeLangOverride","ru");
 if(!result->HasKey("sendErrorReports"))result->SetBool("sendErrorReports",false);
 return result;
}
bool SaveVideoPreferences(const std::string& profile,CefRefPtr<CefDictionaryValue> value){
 if(!value||CefWriteJSON(WrapVideo(value),JSON_WRITER_DEFAULT).length()>4*1024*1024)return false;
 if(profile=="__incognito__"){private_values=value->Copy(false);return true;}
 return WriteProtectedStore(profile,"video",value);
}
void ForgetPrivateVideoPreferences(){private_values=nullptr;}
void BrowserWindow::HandleVideoRequest(int tab_id,CefRefPtr<CefFrame> frame,int id,const std::string& raw){
 auto respond=[frame,id](CefRefPtr<CefDictionaryValue> data){if(!frame||!frame->IsValid())return;auto message=CefProcessMessage::Create("soulu.video.response");message->GetArgumentList()->SetInt(0,id);message->GetArgumentList()->SetString(1,CefWriteJSON(WrapVideo(data),JSON_WRITER_DEFAULT));frame->SendProcessMessage(PID_RENDERER,message);};
 auto failure=[respond](const std::string& text){auto result=CefDictionaryValue::Create();result->SetBool("ok",false);result->SetString("error",text);respond(result);};
 auto* tab=FindTab(tab_id);if(!tab||!tab->browser||!frame||!frame->IsMain()||!IsVideoPage(frame->GetURL())||frame->GetBrowser()->GetIdentifier()!=tab->browser->GetIdentifier()){failure("Video runtime unavailable");return;}
 auto config=tab->incognito&&private_page_settings_?private_page_settings_:settings_;
 if(!tab->incognito&&tab->profile_id!=active_profile_id_){auto value=ReadJson(ProfileRoot(tab->profile_id)/L"soulu-settings.json");if(value&&value->GetType()==VTYPE_DICTIONARY)config=value->GetDictionary();}
 auto parsed=CefParseJSON(raw,JSON_PARSER_RFC);if(!parsed||parsed->GetType()!=VTYPE_DICTIONARY){failure("Invalid video message");return;}
 auto args=parsed->GetDictionary();const std::string op=args->GetString("op");const bool enabled=!config->HasKey("videoTranslationEnabled")||config->GetBool("videoTranslationEnabled");
 const std::string owner=std::to_string(tab->browser->GetIdentifier())+"|"+std::to_string(tab->document_generation);
 auto result=CefDictionaryValue::Create();result->SetBool("ok",true);
 if(op=="abort"){VideoAbort(owner,args->GetString("id"));respond(result);return;}
 if(op=="init"){result->SetBool("enabled",enabled);result->SetBool("incognito",tab->incognito);result->SetString("version","1.12.3");if(enabled){auto values=VideoPreferences(tab->profile_id);if(!values){failure("Video preferences could not be decrypted");return;}result->SetDictionary("values",values);}respond(result);return;}
 if(!enabled){failure("Video translation is disabled");return;}
 if(op=="xhr"){VideoFetch(owner,tab->browser->GetHost()->GetRequestContext(),args,respond);return;}
 if(op!="set"&&op!="delete"){failure("Unknown video operation");return;}
 const std::string key=args->GetString("key");if(key.empty()||key.size()>160||raw.size()>2*1024*1024){failure("Invalid video preference");return;}
 auto values=VideoPreferences(tab->profile_id);if(!values){failure("Video preferences could not be decrypted");return;}
 if(op=="delete")values->Remove(key);else {auto value=args->GetValue("value");if(!value){failure("Missing video preference");return;}values->SetValue(key,value->Copy());}
 if(!SaveVideoPreferences(tab->profile_id,values)){failure("Video preference could not be saved");return;}respond(result);
}
void BrowserWindow::HandleVideoSettings(CefRefPtr<CefDictionaryValue> args,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback){
 auto data=VideoPreferences(active_profile_id_);if(!data){callback->Failure(500,"Video preferences could not be decrypted");return;}
 if(args&&args->HasKey("values")){
  auto patch=args->GetDictionary("values");if(!patch||CefWriteJSON(WrapVideo(patch),JSON_WRITER_DEFAULT).length()>65536){callback->Failure(400,"Invalid video preferences");return;}
  CefDictionaryValue::KeyList keys;patch->GetKeys(keys);if(keys.size()>80){callback->Failure(400,"Too many video preferences");return;}
  for(const auto& key:keys){if(key.length()>100){callback->Failure(400,"Invalid video preference");return;}data->SetValue(key,patch->GetValue(key)->Copy());}
  if(!SaveVideoPreferences(active_profile_id_,data)){callback->Failure(500,"Video preferences could not be saved");return;}
 }
 callback->Success(CefWriteJSON(WrapVideo(data),JSON_WRITER_DEFAULT));
}
}
