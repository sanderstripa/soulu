#include "examples/soulu/video_network.h"
#include "include/cef_urlrequest.h"
#include "include/cef_parser.h"
#include "include/cef_task.h"
#include <algorithm>
#include <cctype>
#include <map>
namespace soulu {
namespace {
bool Allowed(const CefString& raw){
 CefURLParts p;if(!CefParseURL(raw,p)||CefString(&p.scheme)!="https"||!CefString(&p.username).empty()||!CefString(&p.password).empty())return false;
 const std::string host=CefString(&p.host);
 for(const std::string domain:{"youtube.com","youtube-nocookie.com","googlevideo.com","ytimg.com","googleapis.com","yandex.ru","yandex.net","toil.cc","timeweb.cloud","onrender.com","workers.dev","eu.cc","cloudflare-dns.com","raw.githubusercontent.com"})
  if(host==domain||(host.size()>domain.size()&&host.compare(host.size()-domain.size(),domain.size(),domain)==0&&host[host.size()-domain.size()-1]=='.'))return true;
 return false;
}
class Later final:public CefTask {public:explicit Later(std::function<void()> fn):fn_(std::move(fn)){}void Execute() override{fn_();}private:std::function<void()> fn_;IMPLEMENT_REFCOUNTING(Later);};
class Fetch;
std::map<std::string,CefRefPtr<Fetch>> requests;
class Fetch final:public CefURLRequestClient {
 public:Fetch(std::string key,CefRefPtr<CefRequestContext> context,CefRefPtr<CefDictionaryValue> args,VideoResult done):key_(std::move(key)),context_(context),args_(args),done_(std::move(done)){}
 void Start(){
  if(!Allowed(args_->GetString("url"))){Fail("Video request host is not allowed");return;}
  const std::string method=args_->GetString("method");if(method!="GET"&&method!="POST"&&method!="HEAD"&&method!="PUT"){Fail("Video request method is not allowed");return;}
  auto request=CefRequest::Create();request->SetURL(args_->GetString("url"));request->SetMethod(method);
  request->SetFlags(UR_FLAG_SKIP_CACHE|UR_FLAG_STOP_ON_REDIRECT|(args_->GetBool("anonymous")?0:UR_FLAG_ALLOW_STORED_CREDENTIALS));
  if(auto headers=args_->GetDictionary("headers")){CefDictionaryValue::KeyList names;headers->GetKeys(names);if(names.size()>60){Fail("Too many request headers");return;}
   for(const auto& name:names){std::string lower=name;std::transform(lower.begin(),lower.end(),lower.begin(),[](unsigned char c){return static_cast<char>(tolower(c));});
    if(lower=="host"||lower=="connection"||lower=="content-length"||lower=="proxy-authorization"||lower=="cookie")continue;
    if(name.length()>200||headers->GetType(name)!=VTYPE_STRING||headers->GetString(name).length()>16384){Fail("Invalid request header");return;}request->SetHeaderByName(name,headers->GetString(name),true);
   }
  }
  std::string data=args_->GetString("data");
  if(data.size()>3*1024*1024){Fail("Video request body is too large");return;}
  if(args_->GetBool("binary")){auto bytes=CefBase64Decode(data);if(!bytes){Fail("Invalid binary request");return;}data.resize(bytes->GetSize());bytes->GetData(data.data(),data.size(),0);}
  if(!data.empty()){auto post=CefPostData::Create();auto item=CefPostDataElement::Create();item->SetToBytes(data.size(),data.data());post->AddElement(item);request->SetPostData(post);}
  request_=CefURLRequest::Create(request,this,context_);if(!request_)Fail("Video network request could not be started");
 }
 void Cancel(){if(request_)request_->Cancel();Fail("Video request aborted");}
 void Timeout(){if(done_){if(request_)request_->Cancel();Fail("Video request timeout");}}
 void OnRequestComplete(CefRefPtr<CefURLRequest> request) override{
  if(!done_)return;auto response=request->GetResponse();if(!response||request->GetRequestStatus()!=UR_SUCCESS){Fail("Video network request failed");return;}
  const int status=response->GetStatus();const std::string location=response->GetHeaderByName("Location");
  if(status>=300&&status<400&&!location.empty()){
   if(++redirects_>5){Fail("Too many video redirects");return;}CefString target;if(!CefResolveURL(args_->GetString("url"),location,target)||!Allowed(target)){Fail("Video redirect host is not allowed");return;}
   auto next=args_->Copy(false);CefURLParts before,after;CefParseURL(args_->GetString("url"),before);CefParseURL(target,after);
   if(CefString(&before.host)!=CefString(&after.host)){if(auto h=next->GetDictionary("headers")){CefDictionaryValue::KeyList names;h->GetKeys(names);for(const auto& name:names){std::string lower=name;std::transform(lower.begin(),lower.end(),lower.begin(),[](unsigned char c){return static_cast<char>(tolower(c));});if(lower=="authorization")h->Remove(name);}}}
   next->SetString("url",target);if(status==303||((status==301||status==302)&&next->GetString("method")=="POST")){next->SetString("method","GET");next->SetString("data","");}
   args_=next;body_.clear();Start();return;
  }
  auto result=CefDictionaryValue::Create();result->SetBool("ok",true);result->SetInt("status",status);result->SetString("statusText",response->GetStatusText());result->SetString("url",request->GetRequest()->GetURL());result->SetString("body",CefBase64Encode(body_.data(),body_.size()));result->SetString("contentType",response->GetMimeType());
  CefResponse::HeaderMap headers;response->GetHeaderMap(headers);std::string text;for(const auto& [name,value]:headers)text+=name.ToString()+": "+value.ToString()+"\r\n";result->SetString("headers",text);Finish(result);
 }
 void OnUploadProgress(CefRefPtr<CefURLRequest>,int64_t,int64_t) override{}
 void OnDownloadProgress(CefRefPtr<CefURLRequest>,int64_t current,int64_t total) override{if(current>64*1024*1024||total>64*1024*1024){if(request_)request_->Cancel();Fail("Video response exceeds 64 MB");}}
 void OnDownloadData(CefRefPtr<CefURLRequest> request,const void* data,size_t size) override{if(body_.size()+size>64*1024*1024){request->Cancel();Fail("Video response exceeds 64 MB");return;}body_.append(static_cast<const char*>(data),size);}
 bool GetAuthCredentials(bool,const CefString&,int,const CefString&,const CefString&,CefRefPtr<CefAuthCallback>) override{return false;}
 private:void Fail(const std::string& error){auto value=CefDictionaryValue::Create();value->SetBool("ok",false);value->SetString("error",error);Finish(value);}
 void Finish(CefRefPtr<CefDictionaryValue> value){if(!done_)return;auto keep=CefRefPtr<Fetch>(this);auto done=std::move(done_);done_=nullptr;requests.erase(key_);request_=nullptr;body_.clear();done(value);}
 std::string key_,body_;CefRefPtr<CefRequestContext> context_;CefRefPtr<CefDictionaryValue> args_;VideoResult done_;CefRefPtr<CefURLRequest> request_;int redirects_=0;IMPLEMENT_REFCOUNTING(Fetch);
};
}
void VideoFetch(const std::string& owner,CefRefPtr<CefRequestContext> context,CefRefPtr<CefDictionaryValue> args,VideoResult done){
 const std::string id=args->GetString("id"),key=owner+"|"+id;
 if(id.empty()||id.size()>32||requests.size()>=64||requests.count(key)){auto error=CefDictionaryValue::Create();error->SetBool("ok",false);error->SetString("error","Too many video requests");done(error);return;}
 CefRefPtr<Fetch> client=new Fetch(key,context,args->Copy(false),std::move(done));requests.emplace(key,client);
 const int timeout=std::clamp(args->GetInt("timeout"),1000,120000);CefPostDelayedTask(TID_UI,new Later([client]{client->Timeout();}),timeout);client->Start();
}
void VideoAbort(const std::string& owner,const std::string& id){auto it=requests.find(owner+"|"+id);if(it!=requests.end())it->second->Cancel();}
}
