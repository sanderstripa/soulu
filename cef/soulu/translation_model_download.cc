#include "examples/soulu/translation_model_download.h"
#include "include/cef_urlrequest.h"
#include "include/cef_parser.h"
#include "include/cef_task.h"
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <functional>
namespace soulu {
namespace {
class Deadline final:public CefTask {
 public:explicit Deadline(std::function<void()> done):done_(std::move(done)){}void Execute() override{done_();}
 private:std::function<void()> done_;IMPLEMENT_REFCOUNTING(Deadline);
};
class ModelDownload final:public CefURLRequestClient {
 public:explicit ModelDownload(CefRefPtr<CefMessageRouterBrowserSide::Callback> callback):callback_(callback){}
  void Timeout(CefRefPtr<CefURLRequest> request){if(callback_){request->Cancel();Fail();}}
  void OnRequestComplete(CefRefPtr<CefURLRequest> request) override {
    if(!callback_)return;auto response=request->GetResponse();
    if(request->GetRequestStatus()!=UR_SUCCESS||!response||response->GetStatus()!=200||body_.empty()){Fail();return;}
    auto callback=callback_;callback_=nullptr;callback->Success(body_.data(),body_.size());body_.clear();
  }
  void OnUploadProgress(CefRefPtr<CefURLRequest>,int64_t,int64_t) override{}
  void OnDownloadProgress(CefRefPtr<CefURLRequest> request,int64_t current,int64_t total) override {
    if(current>100000000||total>100000000){request->Cancel();Fail();}
  }
  void OnDownloadData(CefRefPtr<CefURLRequest> request,const void* bytes,size_t length) override {
    if(body_.size()+length>100000000){request->Cancel();Fail();return;}body_.append(static_cast<const char*>(bytes),length);
  }
  bool GetAuthCredentials(bool,const CefString&,int,const CefString&,const CefString&,CefRefPtr<CefAuthCallback>) override{return false;}
 private:void Fail(){if(!callback_)return;auto callback=callback_;callback_=nullptr;body_.clear();callback->Failure(502,"Language model download failed");}
  std::string body_;CefRefPtr<CefMessageRouterBrowserSide::Callback> callback_;IMPLEMENT_REFCOUNTING(ModelDownload);
};
}
void DownloadTranslationModel(const std::string& sha256,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback){
  if(sha256.size()!=64){callback->Failure(400,"Invalid model key");return;}
  wchar_t module[32768]={};GetModuleFileNameW(nullptr,module,32768);
  std::ifstream input(std::filesystem::path(module).parent_path()/L"ui"/L"translation-models.json",std::ios::binary);
  const std::string text((std::istreambuf_iterator<char>(input)),{});
  auto manifest=CefParseJSON(text,JSON_PARSER_RFC);auto data=manifest&&manifest->GetType()==VTYPE_DICTIONARY?manifest->GetDictionary():nullptr;
  auto pairs=data?data->GetList("pairs"):nullptr;std::string url;
  if(pairs)for(size_t i=0;i<pairs->GetSize();++i){auto pair=pairs->GetDictionary(i),files=pair?pair->GetDictionary("files"):nullptr;if(!files)continue;
    for(const auto& name:{"model","lexicalShortlist","vocab"}){auto file=files->GetDictionary(name);if(file&&file->GetString("sha256")==sha256)url=file->GetString("url");}}
  // A caller can request only a bundled, pinned resource. It cannot supply an
  // arbitrary URL, headers, request body, filesystem path or page origin.
  if(url.rfind("https://storage.googleapis.com/moz-fx-translations-data--303e-prod-translations-data/models/",0)!=0){callback->Failure(400,"Unknown model");return;}
  auto request=CefRequest::Create();request->SetURL(url);request->SetMethod("GET");
  request->SetFlags(UR_FLAG_SKIP_CACHE|UR_FLAG_STOP_ON_REDIRECT);
  CefRefPtr<ModelDownload> client=new ModelDownload(callback);auto pending=CefURLRequest::Create(request,client,nullptr);
  if(!pending){callback->Failure(500,"Model request unavailable");return;}
  CefPostDelayedTask(TID_UI,new Deadline([client,pending]{client->Timeout(pending);}),120000);
}
}
