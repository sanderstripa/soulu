#include "examples/soulu/isolated_page_job.h"
#include "include/cef_devtools_message_observer.h"
#include "include/cef_parser.h"
#include "include/cef_task.h"

namespace soulu {
namespace {
class Deadline final:public CefTask {
 public:explicit Deadline(std::function<void()> done):done_(std::move(done)){}void Execute() override{done_();}
 private:std::function<void()> done_;IMPLEMENT_REFCOUNTING(Deadline);
};
class PageJob final:public CefDevToolsMessageObserver {
 public:
  PageJob(CefRefPtr<CefBrowser> browser,std::string url,std::string expression,
      std::function<void(CefRefPtr<CefDictionaryValue>)> done)
      :browser_(browser),url_(std::move(url)),expression_(std::move(expression)),done_(std::move(done)){}
  void Start(){
    registration_=browser_->GetHost()->AddDevToolsMessageObserver(this);
    message_=browser_->GetHost()->ExecuteDevToolsMethod(0,"Page.getFrameTree",nullptr);
    CefRefPtr<PageJob> self=this;
    CefPostDelayedTask(TID_UI,new Deadline([self]{self->Finish(nullptr);}),10000);
  }
  void OnDevToolsMethodResult(CefRefPtr<CefBrowser>,int id,bool success,const void* bytes,size_t length) override {
    if(!done_||id!=message_)return;
    if(!browser_->IsValid()||browser_->GetMainFrame()->GetURL()!=url_){Finish(nullptr);return;}
    auto value=success?CefParseJSON(std::string(static_cast<const char*>(bytes),length),JSON_PARSER_RFC):nullptr;
    if(!value||value->GetType()!=VTYPE_DICTIONARY){Finish(nullptr);return;}
    auto data=value->GetDictionary(),params=CefDictionaryValue::Create();
    if(stage_==0){
      auto tree=data->GetDictionary("frameTree"),frame=tree?tree->GetDictionary("frame"):nullptr;
      if(!frame||frame->GetString("url")!=url_){Finish(nullptr);return;}
      params->SetString("frameId",frame->GetString("id"));params->SetString("worldName","SouluTranslate");
      stage_=1;message_=browser_->GetHost()->ExecuteDevToolsMethod(0,"Page.createIsolatedWorld",params);
    }else if(stage_==1){
      if(!data->HasKey("executionContextId")){Finish(nullptr);return;}
      params->SetInt("contextId",data->GetInt("executionContextId"));params->SetString("expression",expression_);
      params->SetBool("returnByValue",true);stage_=2;
      message_=browser_->GetHost()->ExecuteDevToolsMethod(0,"Runtime.evaluate",params);
    }else{
      auto remote=data->GetDictionary("result");Finish(!data->HasKey("exceptionDetails")&&remote?remote->GetDictionary("value"):nullptr);
    }
  }
 private:
  void Finish(CefRefPtr<CefDictionaryValue> value){if(!done_)return;auto done=std::move(done_);done_=nullptr;registration_=nullptr;browser_=nullptr;done(value);}
  CefRefPtr<CefBrowser> browser_;CefRefPtr<CefRegistration> registration_;
  std::string url_,expression_;int message_=0,stage_=0;
  std::function<void(CefRefPtr<CefDictionaryValue>)> done_;
  IMPLEMENT_REFCOUNTING(PageJob);
};
}
void EvaluateTranslationPage(CefRefPtr<CefBrowser> browser,const std::string& url,
    const std::string& expression,std::function<void(CefRefPtr<CefDictionaryValue>)> done){
  CefRefPtr<PageJob> job=new PageJob(browser,url,expression,std::move(done));job->Start();
}
}
