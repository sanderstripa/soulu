#include "examples/soulu/browser_window.h"
#include "examples/soulu/video_bridge.h"
#include "examples/soulu/video_network.h"
#include "examples/soulu/protected_store.h"
#include "examples/soulu/profile_data.h"
#include "include/cef_parser.h"
#include "include/cef_process_message.h"
#include <vector>
#include <windows.h>
#include <bcrypt.h>
#include <chrono>
#include <map>
#include <fstream>
#include <iterator>
namespace soulu {
namespace {
CefRefPtr<CefDictionaryValue> private_values;

struct AuthPending {std::string verifier,state;std::chrono::steady_clock::time_point expires;};
std::map<std::string,AuthPending> auth_pending;
std::string B64Url(const unsigned char* data,size_t size){std::string value=CefBase64Encode(data,size);for(auto& c:value){if(c=='+')c='-';else if(c=='/')c='_';}while(!value.empty()&&value.back()=='=')value.pop_back();return value;}
std::string StartAuth(const std::string& profile){
 unsigned char random[64]={},hash[32]={};if(BCryptGenRandom(nullptr,random,sizeof(random),BCRYPT_USE_SYSTEM_PREFERRED_RNG)<0)return {};
 const auto verifier=B64Url(random,32),state=B64Url(random+32,32);
 BCRYPT_ALG_HANDLE algorithm=nullptr;if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return {};
 const auto status=BCryptHash(algorithm,nullptr,0,reinterpret_cast<PUCHAR>(const_cast<char*>(verifier.data())),static_cast<ULONG>(verifier.size()),hash,sizeof(hash));BCryptCloseAlgorithmProvider(algorithm,0);if(status<0)return {};
 auth_pending[profile]={verifier,state,std::chrono::steady_clock::now()+std::chrono::minutes(10)};
 return "https://oauth.yandex.ru/authorize?client_id=1666fbe22f3749c581002a4f97b2592d&response_type=code&redirect_uri=https%3A%2F%2Foauth.yandex.ru%2Fverification_code&force_confirm=1&state="+state+"&code_challenge="+B64Url(hash,32)+"&code_challenge_method=S256";
}
bool IsAuthPage(const CefString& url){CefURLParts p;return CefParseURL(url,p)&&CefString(&p.scheme)=="https"&&CefString(&p.host)=="oauth.yandex.ru"&&CefString(&p.path)=="/verification_code";}
CefRefPtr<CefDictionaryValue> JsonResponse(CefRefPtr<CefDictionaryValue> response){
 if(!response||!response->GetBool("ok")||response->GetInt("status")!=200)return nullptr;auto bytes=CefBase64Decode(response->GetString("body"));if(!bytes||bytes->GetSize()>1024*1024)return nullptr;
 std::string text(bytes->GetSize(),'\0');bytes->GetData(text.data(),text.size(),0);auto value=CefParseJSON(text,JSON_PARSER_RFC);return value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():nullptr;
}
void CompleteAuth(const std::string& profile,CefRefPtr<CefRequestContext> context,CefRefPtr<CefDictionaryValue> args,VideoResult done){
 auto fail=[done](const std::string& error){auto r=CefDictionaryValue::Create();r->SetBool("ok",false);r->SetString("error",error);done(r);};
 auto it=auth_pending.find(profile);const std::string code=args->GetString("code");
 if(it==auth_pending.end()||it->second.state!=args->GetString("state").ToString()||it->second.expires<std::chrono::steady_clock::now()||code.empty()||code.size()>4096){fail("OAuth state is invalid or expired");return;}
 const auto pending=it->second;auth_pending.erase(it);
 auto request=CefDictionaryValue::Create();request->SetString("id","token");request->SetString("url","https://oauth.yandex.ru/token");request->SetString("method","POST");request->SetBool("anonymous",true);request->SetInt("timeout",60000);auto headers=CefDictionaryValue::Create();headers->SetString("Content-Type","application/x-www-form-urlencoded");request->SetDictionary("headers",headers);
 request->SetString("data","grant_type=authorization_code&client_id=1666fbe22f3749c581002a4f97b2592d&redirect_uri=https%3A%2F%2Foauth.yandex.ru%2Fverification_code&code="+CefURIEncode(code,true).ToString()+"&code_verifier="+pending.verifier);
 VideoFetch("auth|"+profile,context,request,[profile,context,done,fail](CefRefPtr<CefDictionaryValue> response){
  auto token=JsonResponse(response);if(!token||token->GetString("access_token").empty()){fail("Yandex authorization failed");return;}
  const std::string access=token->GetString("access_token");double seconds=token->GetType("expires_in")==VTYPE_INT?token->GetInt("expires_in"):token->GetDouble("expires_in");
  if(seconds<=0||seconds>10.0*366*24*3600){fail("Invalid Yandex token lifetime");return;}
  auto request=CefDictionaryValue::Create();request->SetString("id","identity");request->SetString("url","https://login.yandex.ru/info?format=json");request->SetString("method","GET");request->SetBool("anonymous",true);request->SetInt("timeout",60000);auto headers=CefDictionaryValue::Create();headers->SetString("Authorization","OAuth "+access);request->SetDictionary("headers",headers);
  VideoFetch("auth|"+profile,context,request,[profile,done,fail,access,seconds](CefRefPtr<CefDictionaryValue> response){
   auto identity=JsonResponse(response);if(!identity||identity->GetString("login").empty()){fail("Yandex account details unavailable");return;}
   auto values=VideoPreferences(profile);if(!values){fail("Video preferences could not be decrypted");return;}
   auto account=CefDictionaryValue::Create();account->SetString("token",access);account->SetString("username",identity->GetString("login"));account->SetString("avatarId",identity->GetString("default_avatar_id"));const auto now=std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();account->SetDouble("expires",now+seconds*1000);values->SetDictionary("account",account);
   if(!SaveVideoPreferences(profile,values)){fail("Account could not be saved");return;}auto result=CefDictionaryValue::Create();result->SetBool("ok",true);done(result);
  });
 });
}

struct Watch {std::string profile;CefRefPtr<CefFrame> frame;int id;};
std::vector<Watch> watches;
bool IsVideoPage(const CefString& raw){CefURLParts p;if(!CefParseURL(raw,p)||CefString(&p.scheme)!="https")return false;const std::string host=CefString(&p.host);return host=="youtube.com"||host=="www.youtube.com"||host=="m.youtube.com"||host=="music.youtube.com"||host=="www.youtube-nocookie.com";}
CefRefPtr<CefValue> WrapVideo(CefRefPtr<CefDictionaryValue> value){auto wrapper=CefValue::Create();wrapper->SetDictionary(value);return wrapper;}

void Broadcast(const std::string& profile,CefRefPtr<CefDictionaryValue> value){
 auto result=CefDictionaryValue::Create();result->SetBool("ok",true);result->SetDictionary("values",value);
 const auto json=CefWriteJSON(WrapVideo(result),JSON_WRITER_DEFAULT);
 for(auto it=watches.begin();it!=watches.end();){
  if(!it->frame->IsValid()||!IsVideoPage(it->frame->GetURL())){it=watches.erase(it);continue;}
  if(it->profile==profile){auto message=CefProcessMessage::Create("soulu.video.response");message->GetArgumentList()->SetInt(0,it->id);message->GetArgumentList()->SetString(1,json);it->frame->SendProcessMessage(PID_RENDERER,message);}++it;
 }
}
}

CefRefPtr<CefDictionaryValue> BundledVideoLocaleResponse(CefRefPtr<CefDictionaryValue> args){
 if(!args||args->GetString("method")!="GET")return nullptr;
 CefURLParts parts;if(!CefParseURL(args->GetString("url"),parts)||CefString(&parts.scheme)!="https"||CefString(&parts.host)!="raw.githubusercontent.com")return nullptr;
 const std::string path=CefString(&parts.path);
 const std::string prefix="/ilyhalight/voice-over-translation/";
 if(path.rfind(prefix,0)!=0)return nullptr;
 const auto start=path.find("/src/localization/",prefix.size());if(start==std::string::npos)return nullptr;
 const std::string branch=path.substr(prefix.size(),start-prefix.size());
 if(branch!="master"&&branch!="1.12.3"&&branch!="f32ee1670f6b7b26e5cdeffc0010a03842c960b2")return nullptr;
 const std::string relative=path.substr(start+18);
 if(relative!="hashes.json"&&relative!="locales/en.json"&&relative!="locales/ru.json")return nullptr;
 wchar_t executable[32768]={};GetModuleFileNameW(nullptr,executable,32768);
 const auto file=std::filesystem::path(executable).parent_path()/L"ui"/L"third_party"/L"vot"/relative;
 std::error_code error;const auto size=std::filesystem::file_size(file,error);if(error||size>1024*1024)return nullptr;
 std::ifstream stream(file,std::ios::binary);const std::string body(std::istreambuf_iterator<char>(stream),{});
 auto parsed=CefParseJSON(body,JSON_PARSER_RFC);if(!parsed||parsed->GetType()!=VTYPE_DICTIONARY)return nullptr;
 auto result=CefDictionaryValue::Create();result->SetBool("ok",true);result->SetInt("status",200);result->SetString("statusText","OK");result->SetString("url",args->GetString("url"));result->SetString("body",CefBase64Encode(body.data(),body.size()));result->SetString("contentType","application/json");result->SetString("headers","Content-Type: application/json; charset=utf-8\r\n");return result;
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
 if(profile=="__incognito__"){private_values=value->Copy(false);Broadcast(profile,value);return true;}
 if(!WriteProtectedStore(profile,"video",value))return false;Broadcast(profile,value);return true;
}
void ForgetPrivateVideoPreferences(){private_values=nullptr;}
void BrowserWindow::HandleVideoRequest(int tab_id,CefRefPtr<CefFrame> frame,int id,const std::string& raw){
 auto respond=[frame,id](CefRefPtr<CefDictionaryValue> data){if(!frame||!frame->IsValid())return;auto message=CefProcessMessage::Create("soulu.video.response");message->GetArgumentList()->SetInt(0,id);message->GetArgumentList()->SetString(1,CefWriteJSON(WrapVideo(data),JSON_WRITER_DEFAULT));frame->SendProcessMessage(PID_RENDERER,message);};
 auto failure=[respond](const std::string& text){auto result=CefDictionaryValue::Create();result->SetBool("ok",false);result->SetString("error",text);respond(result);};
 auto* auth_tab=FindTab(tab_id);
 if(auth_tab&&auth_tab->browser&&frame&&frame->IsMain()&&frame->GetBrowser()->GetIdentifier()==auth_tab->browser->GetIdentifier()&&IsAuthPage(frame->GetURL())){
  auto parsed=CefParseJSON(raw,JSON_PARSER_RFC);if(!parsed||parsed->GetType()!=VTYPE_DICTIONARY){failure("Invalid OAuth callback");return;}
  auto args=parsed->GetDictionary();if(args->GetString("op")!="auth"){failure("Invalid OAuth operation");return;}
  CefRefPtr<BrowserWindow> self=this;CompleteAuth(auth_tab->profile_id,auth_tab->browser->GetHost()->GetRequestContext(),args,[self,tab_id,respond](CefRefPtr<CefDictionaryValue> value){respond(value);if(value->GetBool("ok")&&!self->closing_)self->CloseTab(tab_id);});return;
 }
 auto* tab=FindTab(tab_id);if(!tab||!tab->browser||!frame||!frame->IsMain()||!IsVideoPage(frame->GetURL())||frame->GetBrowser()->GetIdentifier()!=tab->browser->GetIdentifier()){failure("Video runtime unavailable");return;}
 auto config=PageSettings(*tab);
 auto parsed=CefParseJSON(raw,JSON_PARSER_RFC);if(!parsed||parsed->GetType()!=VTYPE_DICTIONARY){failure("Invalid video message");return;}
 auto args=parsed->GetDictionary();const std::string op=args->GetString("op");const bool enabled=!config->HasKey("videoTranslationEnabled")||config->GetBool("videoTranslationEnabled");
 const std::string owner=std::to_string(tab->browser->GetIdentifier())+"|"+std::to_string(tab->document_generation);
 auto result=CefDictionaryValue::Create();result->SetBool("ok",true);
 if(op=="abort"){VideoAbort(owner,args->GetString("id"));respond(result);return;}
 if(op=="init"){result->SetBool("enabled",enabled);result->SetBool("incognito",tab->incognito);result->SetString("version","1.12.3");if(enabled){auto values=VideoPreferences(tab->profile_id);if(!values){failure("Video preferences could not be decrypted");return;}result->SetDictionary("values",values);}respond(result);return;}
 if(!enabled){failure("Video translation is disabled");return;}
 if(op=="watch"){
  for(auto it=watches.begin();it!=watches.end();)if(!it->frame->IsValid()||it->frame->GetIdentifier()==frame->GetIdentifier())it=watches.erase(it);else ++it;
  if(watches.size()>=256){failure("Too many video preference listeners");return;}
  watches.push_back({tab->profile_id,frame,id});auto values=VideoPreferences(tab->profile_id);if(values)result->SetDictionary("values",values);respond(result);return;
 }
 if(op=="xhr"){if(auto local=BundledVideoLocaleResponse(args)){respond(local);return;}VideoFetch(owner,tab->browser->GetHost()->GetRequestContext(),args,respond);return;}
 if(op!="set"&&op!="delete"){failure("Unknown video operation");return;}
 const std::string key=args->GetString("key");if(key.empty()||key.size()>160||raw.size()>2*1024*1024){failure("Invalid video preference");return;}
 auto values=VideoPreferences(tab->profile_id);if(!values){failure("Video preferences could not be decrypted");return;}
 if(op=="delete")values->Remove(key);else {auto value=args->GetValue("value");if(!value){failure("Missing video preference");return;}values->SetValue(key,value->Copy());}
 if(!SaveVideoPreferences(tab->profile_id,values)){failure("Video preference could not be saved");return;}respond(result);
}
void BrowserWindow::HandleVideoSettings(CefRefPtr<CefDictionaryValue> args,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback){
 if(args&&args->GetString("operation")=="authStart"){const auto url=StartAuth(active_profile_id_);if(url.empty()){callback->Failure(500,"OAuth could not be initialized");return;}auto result=CefDictionaryValue::Create();result->SetString("url",url);callback->Success(CefWriteJSON(WrapVideo(result),JSON_WRITER_DEFAULT));return;}
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
