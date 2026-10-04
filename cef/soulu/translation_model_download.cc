#include "examples/soulu/translation_model_download.h"
#include "include/cef_urlrequest.h"
#include "include/cef_parser.h"
#include "include/cef_task.h"
#include "examples/soulu/profile_data.h"
#include <windows.h>
#include <bcrypt.h>
#include <filesystem>
#include <fstream>
#include <functional>
#include <map>
#include <mutex>
#include <set>
#include <memory>
#include <stdexcept>
namespace soulu {
namespace {
std::mutex pending_mutex;
std::map<std::string,std::shared_ptr<std::string>> pending_models;
std::map<std::string,std::string> ModelUrls(){
  wchar_t module[32768]={};GetModuleFileNameW(nullptr,module,32768);
  std::ifstream input(std::filesystem::path(module).parent_path()/L"ui"/L"translation-models.json",std::ios::binary);
  const std::string text((std::istreambuf_iterator<char>(input)),{});
  auto manifest=CefParseJSON(text,JSON_PARSER_RFC);auto data=manifest&&manifest->GetType()==VTYPE_DICTIONARY?manifest->GetDictionary():nullptr;
  auto pairs=data?data->GetList("pairs"):nullptr;std::map<std::string,std::string> urls;
  if(pairs)for(size_t i=0;i<pairs->GetSize();++i){auto pair=pairs->GetDictionary(i),files=pair?pair->GetDictionary("files"):nullptr;if(!files)continue;
    for(const auto& name:{"model","lexicalShortlist","vocab"}){auto file=files->GetDictionary(name);if(file)urls.emplace(file->GetString("sha256").ToString(),file->GetString("url").ToString());}}
  return urls;
}
std::string Digest(const std::string& bytes){
  BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;unsigned char digest[32]={};
  if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return {};
  const bool valid=BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)>=0&&BCryptHashData(hash,reinterpret_cast<PUCHAR>(const_cast<char*>(bytes.data())),static_cast<ULONG>(bytes.size()),0)>=0&&BCryptFinishHash(hash,digest,sizeof(digest),0)>=0;
  if(hash)BCryptDestroyHash(hash);BCryptCloseAlgorithmProvider(algorithm,0);
  if(!valid)return {};const char digits[]="0123456789abcdef";std::string result;for(auto byte:digest){result+=digits[byte>>4];result+=digits[byte&15];}return result;
}
std::filesystem::path CacheRoot(){
  auto root=DataRoot();for(const auto& component:{L"Translation",L"Models",L"v1"}){root/=component;
    const auto attributes=GetFileAttributesW(root.c_str());if(attributes!=INVALID_FILE_ATTRIBUTES&&(attributes&FILE_ATTRIBUTE_REPARSE_POINT))throw std::runtime_error("Unsafe model cache path");std::filesystem::create_directories(root);}
  return root;
}
bool RegularFile(const std::filesystem::path& path){const auto attributes=GetFileAttributesW(path.c_str());return attributes!=INVALID_FILE_ATTRIBUTES&&!(attributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY));}
void Drop(const std::filesystem::path& root,const std::string& key){std::error_code error;std::filesystem::remove(root/(key+".model"),error);std::filesystem::remove(root/(key+".sha256"),error);}
class Deadline final:public CefTask {
 public:explicit Deadline(std::function<void()> done):done_(std::move(done)){}void Execute() override{done_();}
 private:std::function<void()> done_;IMPLEMENT_REFCOUNTING(Deadline);
};
class ModelDownload final:public CefURLRequestClient {
 public:ModelDownload(std::string key,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback):key_(std::move(key)),callback_(callback){}
  void Timeout(CefRefPtr<CefURLRequest> request){if(callback_){request->Cancel();Fail();}}
  void OnRequestComplete(CefRefPtr<CefURLRequest> request) override {
    if(!callback_)return;auto response=request->GetResponse();
    if(request->GetRequestStatus()!=UR_SUCCESS||!response||response->GetStatus()!=200||body_.empty()){Fail();return;}
    auto bytes=std::make_shared<std::string>(std::move(body_));
    {std::lock_guard lock(pending_mutex);size_t total=0;for(const auto& row:pending_models)total+=row.second->size();if(total+bytes->size()>128000000){Fail();return;}pending_models[key_]=bytes;}
    auto callback=callback_;callback_=nullptr;callback->Success(bytes->data(),bytes->size());
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
  std::string key_,body_;CefRefPtr<CefMessageRouterBrowserSide::Callback> callback_;IMPLEMENT_REFCOUNTING(ModelDownload);
};
}
void DownloadTranslationModel(const std::string& sha256,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback){
  if(sha256.size()!=64){callback->Failure(400,"Invalid model key");return;}
  const auto urls=ModelUrls();auto found=urls.find(sha256);const std::string url=found==urls.end()?"":found->second;
  // A caller can request only a bundled, pinned resource. It cannot supply an
  // arbitrary URL, headers, request body, filesystem path or page origin.
  if(url.rfind("https://storage.googleapis.com/moz-fx-translations-data--303e-prod-translations-data/models/",0)!=0){callback->Failure(400,"Unknown model");return;}
  auto request=CefRequest::Create();request->SetURL(url);request->SetMethod("GET");
  request->SetFlags(UR_FLAG_SKIP_CACHE|UR_FLAG_STOP_ON_REDIRECT);
  CefRefPtr<ModelDownload> client=new ModelDownload(sha256,callback);auto pending=CefURLRequest::Create(request,client,nullptr);
  if(!pending){callback->Failure(500,"Model request unavailable");return;}
  CefPostDelayedTask(TID_UI,new Deadline([client,pending]{client->Timeout(pending);}),120000);
}
void TranslationModelCache(const std::string& operation,const std::string& sha256,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback){
  const auto urls=ModelUrls();if(sha256.size()!=64||urls.find(sha256)==urls.end()){callback->Failure(400,"Unknown model key");return;}
  if(operation!="read"&&operation!="approve"&&operation!="drop"){callback->Failure(400,"Unknown cache operation");return;}
  std::shared_ptr<std::string> payload;
  if(operation!="read"){std::lock_guard lock(pending_mutex);auto row=pending_models.find(sha256);if(row!=pending_models.end()){payload=row->second;pending_models.erase(row);}}
  CefPostTask(TID_FILE_USER_BLOCKING,new Deadline([operation,sha256,urls,payload,callback]{
    try{
      const auto root=CacheRoot();static bool cleaned=false;
      if(!cleaned){for(const auto& item:std::filesystem::directory_iterator(root)){if(!RegularFile(item.path()))continue;const auto name=item.path().filename().string();bool valid=false;for(const auto& row:urls)if(name==row.first+".model"||name==row.first+".sha256"){valid=true;break;}if(!valid){std::error_code error;std::filesystem::remove(item.path(),error);}}cleaned=true;}
      const auto file=root/(sha256+".model"),hash_file=root/(sha256+".sha256");
      if(operation=="drop"){Drop(root,sha256);callback->Success("true");return;}
      if(operation=="read"){
        if(RegularFile(file)&&RegularFile(hash_file)&&std::filesystem::file_size(file)<=100000000&&std::filesystem::file_size(hash_file)==64){
          std::ifstream input(file,std::ios::binary),hash_input(hash_file,std::ios::binary);std::string bytes((std::istreambuf_iterator<char>(input)),{}),hash((std::istreambuf_iterator<char>(hash_input)),{});
          if(!bytes.empty()&&Digest(bytes)==hash){callback->Success(bytes.data(),bytes.size());return;}}
        Drop(root,sha256);callback->Success(nullptr,0);return;
      }
      if(!payload){if(RegularFile(file)){callback->Success("true");return;}callback->Failure(409,"No verified download to cache");return;}
      const auto hash=Digest(*payload);if(hash.empty())throw std::runtime_error("Model hash unavailable");
      const auto temporary=root/(sha256+".tmp"),hash_temporary=root/(sha256+".hash.tmp");
      for(const auto& path:{temporary,hash_temporary}){const auto attributes=GetFileAttributesW(path.c_str());if(attributes!=INVALID_FILE_ATTRIBUTES&&(attributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY)))throw std::runtime_error("Unsafe model cache file");}
      std::ofstream output(temporary,std::ios::binary|std::ios::trunc);output.write(payload->data(),payload->size());output.close();if(!output)throw std::runtime_error("Model cache write failed");
      std::ofstream hash_output(hash_temporary,std::ios::binary|std::ios::trunc);hash_output<<hash;hash_output.close();if(!hash_output)throw std::runtime_error("Model cache hash write failed");
      if(!MoveFileExW(temporary.c_str(),file.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)||!MoveFileExW(hash_temporary.c_str(),hash_file.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))throw std::runtime_error("Model cache replacement failed");
      callback->Success("true");
    }catch(const std::exception&){callback->Failure(500,"Model cache unavailable");}
  }));
}
}
