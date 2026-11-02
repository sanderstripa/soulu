#include "examples/soulu/extension_service.h"
#include "include/cef_client.h"
#include "include/cef_parser.h"
#include "include/cef_task.h"
#include "include/cef_devtools_message_observer.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_browser_view_delegate.h"
#include "include/views/cef_window.h"
#include "include/views/cef_window_delegate.h"
#include "include/views/cef_fill_layout.h"
#include "include/wrapper/cef_helpers.h"
#include <vector>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
namespace soulu { namespace {
class Task final:public CefTask{public:explicit Task(std::function<void()> fn):fn_(std::move(fn)){}void Execute()override{fn_();}private:std::function<void()> fn_;IMPLEMENT_REFCOUNTING(Task);};
class Call final:public CefDevToolsMessageObserver {
 public:
  void Start(CefRefPtr<CefBrowser> browser,const std::string& method,CefRefPtr<CefDictionaryValue> params,ExtensionReply done){
    browser_=browser;done_=std::move(done);registration_=browser->GetHost()->AddDevToolsMessageObserver(this);
    id_=browser->GetHost()->ExecuteDevToolsMethod(0,method,params);
    if(!id_){Finish(nullptr,"Chromium did not accept the extension request");return;}
    CefRefPtr<Call> self=this;CefPostDelayedTask(TID_UI,new Task([self]{self->Finish(nullptr,"Extension request timed out");}),15000);
  }
  void OnDevToolsAgentDetached(CefRefPtr<CefBrowser>) override {Finish(nullptr,"Extension browser closed");}
  void OnDevToolsMethodResult(CefRefPtr<CefBrowser>,int id,bool ok,const void* bytes,size_t size) override {
    if(id!=id_||!done_)return;
    auto value=CefParseJSON(std::string(static_cast<const char*>(bytes),size),JSON_PARSER_RFC);
    auto data=value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():nullptr;
    std::string error;if(!ok)error=data&&data->HasKey("message")?data->GetString("message").ToString():"Chromium extension request failed";
    if(data&&data->HasKey("exceptionDetails")){
      auto details=data->GetDictionary("exceptionDetails"),exception=details?details->GetDictionary("exception"):nullptr;
      error=exception?exception->GetString("description").ToString():"Extension management script failed";
    }
    Finish(data,error);
  }
 private:
  void Finish(CefRefPtr<CefDictionaryValue> value,const std::string& error){if(!done_)return;auto done=std::move(done_);registration_=nullptr;browser_=nullptr;done(value,error);}
  int id_=0;ExtensionReply done_;CefRefPtr<CefBrowser> browser_;CefRefPtr<CefRegistration> registration_;IMPLEMENT_REFCOUNTING(Call);
};
void Run(CefRefPtr<CefBrowser> browser,const std::string& method,CefRefPtr<CefDictionaryValue> params,ExtensionReply done){CefRefPtr<Call> call=new Call();call->Start(browser,method,params,std::move(done));}
void Evaluate(CefRefPtr<CefBrowser> browser,const std::string& expression,ExtensionReply done){
  auto params=CefDictionaryValue::Create();params->SetString("expression",expression);params->SetBool("awaitPromise",true);params->SetBool("returnByValue",true);
  Run(browser,"Runtime.evaluate",params,[done](CefRefPtr<CefDictionaryValue> data,const std::string& error){auto result=data?data->GetDictionary("result"):nullptr;auto value=result?result->GetDictionary("value"):nullptr;done(value,error.empty()&&!value?"Invalid extension response":error);});
}
std::string DiskIcon(const std::string& root_text){
  if(root_text.empty())return {};
  try{
    const auto root=std::filesystem::weakly_canonical(std::filesystem::u8path(root_text));
    auto read=[](const std::filesystem::path& p,size_t limit)->std::string{
      std::error_code ec;const auto size=std::filesystem::file_size(p,ec);if(ec||size>limit)return {};
      std::ifstream stream(p,std::ios::binary);return std::string(std::istreambuf_iterator<char>(stream),{});
    };
    auto manifest=CefParseJSON(read(root/"manifest.json",512*1024),JSON_PARSER_RFC);
    auto icons=manifest&&manifest->GetType()==VTYPE_DICTIONARY?manifest->GetDictionary()->GetDictionary("icons"):nullptr;
    if(!icons)return {};CefDictionaryValue::KeyList sizes;icons->GetKeys(sizes);std::string path;
    for(const auto& size:sizes)if(icons->GetType(size)==VTYPE_STRING)path=icons->GetString(size);
    if(icons->GetType("48")==VTYPE_STRING)path=icons->GetString("48");
    const auto icon=std::filesystem::weakly_canonical(root/std::filesystem::u8path(path));
    auto a=root.begin(),b=icon.begin();for(;a!=root.end()&&b!=icon.end()&&*a==*b;++a,++b){}
    if(a!=root.end()||b==icon.end())return {};
    const auto bytes=read(icon,256*1024);
    const unsigned char signature[]={137,80,78,71,13,10,26,10};
    if(bytes.size()<8||!std::equal(signature,signature+8,reinterpret_cast<const unsigned char*>(bytes.data())))return {};
    return "data:image/png;base64,"+CefBase64Encode(bytes.data(),bytes.size()).ToString();
  }catch(...){return {};}
}
bool ValidId(const std::string& id){return id.size()==32&&std::all_of(id.begin(),id.end(),[](char c){return c>='a'&&c<='p';});}
class Service final:public ExtensionService,public CefClient,public CefLifeSpanHandler,public CefLoadHandler,public CefWindowDelegate,public CefBrowserViewDelegate {
 public:
  CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler()override{return this;}
  CefRefPtr<CefLoadHandler> GetLoadHandler()override{return this;}
  cef_runtime_style_t GetWindowRuntimeStyle()override{return CEF_RUNTIME_STYLE_CHROME;}
  cef_runtime_style_t GetBrowserRuntimeStyle()override{return CEF_RUNTIME_STYLE_CHROME;}
  CefRect GetInitialBounds(CefRefPtr<CefWindow>)override{return CefRect(0,0,800,600);}
  bool Start(CefRefPtr<CefRequestContext> context){
    context_=context;
    CefBrowserSettings settings;auto extra=CefDictionaryValue::Create();extra->SetBool("souluExtensionsSurface",true);
    view_=CefBrowserView::CreateBrowserView(this,"chrome://extensions/shortcuts?soulu-worker=1",settings,extra,context,this);
    if(view_)window_=CefWindow::CreateTopLevelWindow(this);return window_!=nullptr;
  }
  void OnWindowCreated(CefRefPtr<CefWindow> window)override{window_=window;window->SetToFillLayout();window->AddChildView(view_);}
  bool CanClose(CefRefPtr<CefWindow>)override{return !browser_||browser_->GetHost()->TryCloseBrowser();}
  void OnWindowDestroyed(CefRefPtr<CefWindow>)override{window_=nullptr;view_=nullptr;CompleteClose();}
  void OnAfterCreated(CefRefPtr<CefBrowser> browser)override{browser_=browser;if(closing_)browser->GetHost()->CloseBrowser(true);}
  void OnBeforeClose(CefRefPtr<CefBrowser>)override{browser_=nullptr;if(window_)window_->Close();CompleteClose();}
  void OnLoadEnd(CefRefPtr<CefBrowser>,CefRefPtr<CefFrame> frame,int status)override{
    if(!frame->IsMain()||frame->GetURL().ToString().rfind("chrome://extensions/",0)!=0||closing_)return;
    ready_=true;auto queued=std::move(queued_);queued_.clear();for(auto& task:queued)task();
  }
  void List(ExtensionReply done)override{
    CefRefPtr<Service> self=this;
    Ready([self,done]{Evaluate(self->browser_,R"JS((async()=>{
      const rows=await chrome.developerPrivate.getExtensionsInfo({includeDisabled:true,includeTerminated:true});
      const items=await Promise.all(rows.filter(e=>e.type==='EXTENSION').map(async e=>{
        let icon='';try{const r=await fetch(e.iconUrl);const blob=await r.blob();icon=await new Promise((resolve,reject)=>{const f=new FileReader();f.onload=()=>resolve(f.result);f.onerror=reject;f.readAsDataURL(blob)});}catch{}
        return {id:e.id,name:e.name,version:e.version,enabled:e.state==='ENABLED',pinned:!!e.pinnedToToolbar,action:!!e.isExtensionAction,path:e.path||'',icon:icon.startsWith('data:image/')?icon:''};
      }));return {items};
    })())JS",[self,done](CefRefPtr<CefDictionaryValue> result,const std::string& error){
      auto items=result?result->GetList("items"):nullptr;
      if(items)for(size_t i=0;i<items->GetSize();++i){auto item=items->GetDictionary(i);if(!item)continue;if(item->GetString("icon").empty()){
        auto icon=DiskIcon(item->GetString("path"));const auto id=item->GetString("id").ToString();
        if(icon.empty()&&ValidId(id)&&self->context_){
          std::error_code ec;const auto base=std::filesystem::path(self->context_->GetCachePath().ToWString())/"Extensions"/id;
          for(const auto& folder:std::filesystem::directory_iterator(base,ec)){if(ec)break;icon=DiskIcon(CefString(folder.path().wstring()).ToString());if(!icon.empty())break;}
        }
        item->SetString("icon",icon);
      }item->Remove("path");}
      done(result,error);
    });},done);
  }
  void Pin(const std::string& id,bool pinned,ExtensionReply done)override{
    if(!ValidId(id)){done(nullptr,"Invalid extension ID");return;}
    Ready([this,id,pinned,done]{Evaluate(browser_,"(async()=>{const all=await chrome.developerPrivate.getExtensionsInfo({includeDisabled:true,includeTerminated:true});if(!all.some(e=>e.id==='"+id+"'&&e.isExtensionAction))throw Error('Extension has no action');await chrome.developerPrivate.updateExtensionConfiguration({extensionId:'"+id+"',pinnedToToolbar:"+(pinned?"true":"false")+"});return {ok:true}})()",done);},done);
  }
  void Open(CefRefPtr<CefBrowser> browser,const std::string& id,ExtensionReply done)override{
    if(!ValidId(id)||!browser||browser->GetHost()->GetRuntimeStyle()!=CEF_RUNTIME_STYLE_CHROME){done(nullptr,"A Chrome-style Soulu tab is required");return;}
    Run(browser,"Browser.getWindowForTarget",nullptr,[browser,id,done](CefRefPtr<CefDictionaryValue> info,const std::string& error){
      if(!error.empty()||!info){done(nullptr,error);return;}const int window=info->GetInt("windowId");
      auto params=CefDictionaryValue::Create();auto filter=CefListValue::Create();auto tabs=CefDictionaryValue::Create();tabs->SetString("type","tab");filter->SetDictionary(0,tabs);auto rest=CefDictionaryValue::Create();rest->SetBool("exclude",true);filter->SetDictionary(1,rest);params->SetList("filter",filter);
      Run(browser,"Target.getTargets",params,[browser,id,window,done](CefRefPtr<CefDictionaryValue> data,const std::string& error){
        auto targets=data?data->GetList("targetInfos"):nullptr;if(!error.empty()||!targets){done(nullptr,error);return;}
        auto matching=CefListValue::Create();const std::string url=browser->GetMainFrame()->GetURL();
        for(size_t i=0;i<targets->GetSize();++i){auto t=targets->GetDictionary(i);if(t&&t->GetString("url")==url)matching->SetDictionary(matching->GetSize(),t->Copy(false));}
        FindTarget(browser,id,window,matching,0,done);
      });
    });
  }
  void Close(std::function<void()> done)override{
    closing_=true;closed_=std::move(done);auto queued=std::move(queued_);queued_.clear();for(auto& task:queued)task();
    if(browser_)browser_->GetHost()->CloseBrowser(true);else if(window_)window_->Close();CompleteClose();
  }
 private:
  static void FindTarget(CefRefPtr<CefBrowser> browser,const std::string& id,int window,CefRefPtr<CefListValue> targets,size_t index,ExtensionReply done){
    if(index>=targets->GetSize()){done(nullptr,"Active Soulu tab was not found in Chromium");return;}
    const auto target=targets->GetDictionary(index)->GetString("targetId");auto params=CefDictionaryValue::Create();params->SetString("targetId",target);
    Run(browser,"Browser.getWindowForTarget",params,[browser,id,window,targets,index,target,done](CefRefPtr<CefDictionaryValue> info,const std::string& error){
      if(error.empty()&&info&&info->GetInt("windowId")==window){auto params=CefDictionaryValue::Create();params->SetString("id",id);params->SetString("targetId",target);Run(browser,"Extensions.triggerAction",params,done);}
      else FindTarget(browser,id,window,targets,index+1,done);
    });
  }
  void Ready(std::function<void()> task,ExtensionReply done){
    if(closing_){done(nullptr,"Extension profile is closing");return;}
    if(ready_&&browser_){task();return;}
    CefRefPtr<Service> self=this;queued_.push_back([self,task,done]{if(self->closing_||!self->browser_)done(nullptr,"Extension profile closed");else task();});
  }
  void CompleteClose(){if(closing_&&!browser_&&!window_){auto done=std::move(closed_);if(done)done();}}
  bool ready_=false,closing_=false;std::vector<std::function<void()>> queued_;std::function<void()> closed_;
  CefRefPtr<CefRequestContext> context_;
  CefRefPtr<CefWindow> window_;CefRefPtr<CefBrowserView> view_;CefRefPtr<CefBrowser> browser_;
  IMPLEMENT_REFCOUNTING(Service);
};
}
CefRefPtr<ExtensionService> CreateExtensionService(CefRefPtr<CefRequestContext> context){CefRefPtr<Service> service=new Service();if(!service->Start(context))return nullptr;return service;}
}
