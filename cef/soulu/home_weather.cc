#include "examples/soulu/home_weather.h"
#include "examples/soulu/profile_data.h"
#include "include/cef_urlrequest.h"
#include "include/cef_parser.h"
#include "include/cef_task.h"
#include <chrono>
#include <cmath>
#include <map>
#include <functional>
namespace soulu {namespace {
using Json=CefRefPtr<CefDictionaryValue>;
double Now(){return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();}
class Task final:public CefTask {public:explicit Task(std::function<void()> fn):fn_(std::move(fn)){}void Execute() override{fn_();}private:std::function<void()> fn_;IMPLEMENT_REFCOUNTING(Task);};
class Request final:public CefURLRequestClient {
 public:explicit Request(std::function<void(Json)> done):done_(std::move(done)){}
 void Timeout(CefRefPtr<CefURLRequest> request){if(done_){if(request)if(request)request->Cancel();Finish(nullptr);}}
 void OnRequestComplete(CefRefPtr<CefURLRequest> r) override {auto response=r->GetResponse();auto v=response&&response->GetStatus()==200?CefParseJSON(body_,JSON_PARSER_RFC):nullptr;Finish(v&&v->GetType()==VTYPE_DICTIONARY?v->GetDictionary():nullptr);}
 void OnUploadProgress(CefRefPtr<CefURLRequest>,int64_t,int64_t) override{}
 void OnDownloadProgress(CefRefPtr<CefURLRequest> r,int64_t current,int64_t total) override{if(current>262144||total>262144){r->Cancel();Finish(nullptr);}}
 void OnDownloadData(CefRefPtr<CefURLRequest> r,const void* p,size_t n) override{if(body_.size()+n>262144){r->Cancel();Finish(nullptr);}else body_.append(static_cast<const char*>(p),n);}
 bool GetAuthCredentials(bool,const CefString&,int,const CefString&,const CefString&,CefRefPtr<CefAuthCallback>) override{return false;}
 private:void Finish(Json value){if(!done_)return;auto done=std::move(done_);done_=nullptr;body_.clear();done(value);}std::string body_;std::function<void(Json)> done_;IMPLEMENT_REFCOUNTING(Request);
};
void Fetch(const std::string& url,CefRefPtr<CefRequestContext> context,std::function<void(Json)> done){auto r=CefRequest::Create();r->SetURL(url);r->SetMethod("GET");r->SetFlags(UR_FLAG_SKIP_CACHE|UR_FLAG_STOP_ON_REDIRECT);CefRefPtr<Request> client=new Request(std::move(done));auto pending=CefURLRequest::Create(r,client,context);if(!pending){client->Timeout(nullptr);return;}CefPostDelayedTask(TID_UI,new Task([client,pending]{client->Timeout(pending);}),15000);}
struct Cache{Json data;double time=0,retry=0;bool pending=false;std::vector<HomeResult> waiting;};
std::map<std::string,Cache> cache;
void Complete(const std::string& key,const std::filesystem::path& file,Json data){auto it=cache.find(key);if(it==cache.end())return;auto& c=it->second;c.pending=false;auto response=CefDictionaryValue::Create();if(data){c.time=Now();c.data=data;data->SetDouble("fetchedAt",c.time);data->SetString("cacheKey",key);data->SetString("status","ready");if(!file.empty()){auto v=CefValue::Create();v->SetDictionary(data->Copy(false));WriteJson(file,v);}}else c.retry=Now()+60;if(c.data&&Now()-c.time<86400){response=c.data->Copy(false);response->SetString("status",data?"ready":"stale");}else response->SetString("status","unavailable");auto waiting=std::move(c.waiting);for(auto& done:waiting)done(response->Copy(false));}
}
void ForgetPrivateHomeWeather(){for(auto it=cache.begin();it!=cache.end();)if(it->first.rfind("__incognito__",0)==0)it=cache.erase(it);else ++it;}
void HomeWeather(const std::string& profile,const std::filesystem::path& file,CefRefPtr<CefRequestContext> context,Json config,Json location,HomeResult done){
 const std::string city=config->GetString("homeWeatherCity"),mode=config->GetString("homeWeatherMode"),units=config->GetString("homeWeatherUnits"),language=config->GetString("language");
 const std::string key=profile+"|"+mode+"|"+city+"|"+units+"|"+language;
 auto& c=cache[key];if(!c.data&&!file.empty()){auto v=ReadJson(file);if(v&&v->GetType()==VTYPE_DICTIONARY){auto d=v->GetDictionary();if(d->GetString("cacheKey")==key&&d->GetDictionary("current")&&d->GetDictionary("daily")){c.data=d;c.time=d->GetDouble("fetchedAt");}}}
 if(c.data&&Now()>=c.time&&Now()-c.time<900){done(c.data->Copy(false));return;}if(c.retry>Now()){auto d=c.data&&Now()-c.time<86400?c.data->Copy(false):CefDictionaryValue::Create();d->SetString("status",d->HasKey("current")?"stale":"unavailable");done(d);return;}c.waiting.push_back(std::move(done));if(c.pending)return;c.pending=true;
 auto forecast=[key,file,context,units](double lat,double lon,const std::string& name){if(!std::isfinite(lat)||!std::isfinite(lon)||std::abs(lat)>90||std::abs(lon)>180){Complete(key,file,nullptr);return;}std::string url="https://api.open-meteo.com/v1/forecast?latitude="+std::to_string(lat)+"&longitude="+std::to_string(lon)+"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,precipitation,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days=5&timezone=auto&temperature_unit="+(units=="fahrenheit"?std::string("fahrenheit"):std::string("celsius"));Fetch(url,context,[key,file,name](Json data){if(!data||!data->GetDictionary("current")||!data->GetDictionary("daily")){Complete(key,file,nullptr);return;}data->SetString("city",name);Complete(key,file,data);});};
 if(mode=="configured"&&!city.empty()){Fetch("https://geocoding-api.open-meteo.com/v1/search?count=1&format=json&language="+language+"&name="+CefURIEncode(city,true).ToString(),context,[key,file,forecast](Json data){auto rows=data?data->GetList("results"):nullptr;auto row=rows&&rows->GetSize()?rows->GetDictionary(0):nullptr;if(!row){Complete(key,file,nullptr);return;}forecast(row->GetDouble("latitude"),row->GetDouble("longitude"),row->GetString("name"));});}
 else if(location&&location->GetString("status")=="ready")forecast(location->GetDouble("latitude"),location->GetDouble("longitude"),config->GetString("language")=="en"?"Current location":"Текущее местоположение");
 else Complete(key,file,nullptr);
}
}
