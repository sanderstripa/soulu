#include "examples/soulu/video_renderer.h"
#include "include/cef_parser.h"
#include "include/cef_process_message.h"
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <map>
#include <iterator>
namespace soulu {
namespace {
struct Pending {CefRefPtr<CefV8Context> context;CefRefPtr<CefV8Value> callback;bool persistent=false;};
std::map<int,Pending> pending;int next_id=0;
bool Supported(const CefString& raw){CefURLParts parts;if(!CefParseURL(raw,parts)||CefString(&parts.scheme)!="https")return false;
 const std::string host=CefString(&parts.host);return host=="youtube.com"||host=="www.youtube.com"||host=="m.youtube.com"||host=="music.youtube.com"||host=="www.youtube-nocookie.com";}
class Submit final:public CefV8Handler {
 public:bool Execute(const CefString&,CefRefPtr<CefV8Value>,const CefV8ValueList& args,CefRefPtr<CefV8Value>& result,CefString& exception) override {
  const auto context=CefV8Context::GetCurrentContext();if(!context||!context->GetFrame()->IsMain()||!Supported(context->GetFrame()->GetURL())||args.size()!=2||!args[0]->IsString()||!args[1]->IsFunction()||args[0]->GetStringValue().length()>4*1024*1024||pending.size()>=128){exception="Video bridge unavailable";return true;}
  const int id=++next_id;auto parsed=CefParseJSON(args[0]->GetStringValue(),JSON_PARSER_RFC);const bool watch=parsed&&parsed->GetType()==VTYPE_DICTIONARY&&parsed->GetDictionary()->GetString("op")=="watch";pending.emplace(id,Pending{context,args[1],watch});auto message=CefProcessMessage::Create("soulu.video.request");
  message->GetArgumentList()->SetInt(0,id);message->GetArgumentList()->SetString(1,args[0]->GetStringValue());context->GetFrame()->SendProcessMessage(PID_BROWSER,message);result=CefV8Value::CreateInt(id);return true;
 }
 private:IMPLEMENT_REFCOUNTING(Submit);
};
std::string ReadScript(const wchar_t* name){
 wchar_t file[32768]={};GetModuleFileNameW(nullptr,file,32768);const auto path=std::filesystem::path(file).parent_path()/L"ui"/name;
 std::error_code error;const auto size=std::filesystem::file_size(path,error);if(error||size>4*1024*1024)return {};
 std::ifstream input(path,std::ios::binary);return std::string(std::istreambuf_iterator<char>(input),{});
}
}
void InstallVideoRuntime(CefRefPtr<CefBrowser>,CefRefPtr<CefFrame> frame,CefRefPtr<CefV8Context> context){
 if(!frame->IsMain()||!Supported(frame->GetURL()))return;
 static const auto bootstrap=ReadScript(L"video-runtime.js"),bundle=ReadScript(L"third_party/vot/vot.user.js");
 if(bootstrap.empty()||bundle.empty())return;
 context->GetGlobal()->SetValue("__souluVideoNative",CefV8Value::CreateFunction("request",new Submit()),V8_PROPERTY_ATTRIBUTE_NONE);
 CefRefPtr<CefV8Value> result;CefRefPtr<CefV8Exception> error;
 const std::string code="("+bootstrap+")(function(GM,GM_getValue,GM_setValue,GM_deleteValue,GM_listValues,GM_addStyle,GM_info,GM_xmlhttpRequest,GM_notification){\n"+bundle+"\n});";
 context->Eval(code,frame->GetURL(),0,result,error);
}
void ForgetVideoContext(CefRefPtr<CefV8Context> context){for(auto it=pending.begin();it!=pending.end();)if(it->second.context->IsSame(context))it=pending.erase(it);else ++it;}
bool HandleVideoResponse(CefRefPtr<CefFrame> frame,CefProcessId source,CefRefPtr<CefProcessMessage> message){
 if(source!=PID_BROWSER||message->GetName()!="soulu.video.response"||!frame||!frame->IsMain())return false;
 auto args=message->GetArgumentList();if(args->GetSize()!=2||args->GetType(0)!=VTYPE_INT||args->GetType(1)!=VTYPE_STRING)return true;
 auto it=pending.find(args->GetInt(0));if(it==pending.end())return true;auto item=it->second;if(!item.persistent)pending.erase(it);
 if(item.context->IsValid()){item.context->Enter();item.callback->ExecuteFunction(nullptr,{CefV8Value::CreateString(args->GetString(1))});item.context->Exit();}return true;
}
}
