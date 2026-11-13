#include "examples/sona/extension_pipe.h"
#include <windows.h>
#include <atomic>
#include <map>
#include <thread>
#include <algorithm>
#include "include/cef_parser.h"
#include "include/cef_task.h"
#include "include/wrapper/cef_helpers.h"
namespace sona { namespace {
class Task final:public CefTask {
 public:explicit Task(std::function<void()> fn):fn_(std::move(fn)){}void Execute()override{fn_();}
 private:std::function<void()> fn_;IMPLEMENT_REFCOUNTING(Task);
};
class Pipe {
 public:
  ~Pipe(){Stop();}
  void Configure(CefRefPtr<CefCommandLine> command){
    if(write_)return;
    HANDLE input=nullptr,output=nullptr;
    if(!CreatePipe(&input,&write_,nullptr,65536)||!CreatePipe(&read_,&output,nullptr,65536)){
      if(input)CloseHandle(input);if(output)CloseHandle(output);
      if(write_)CloseHandle(write_);if(read_)CloseHandle(read_);write_=read_=nullptr;return;
    }
    // Chromium adopts input/output via _open_osfhandle. Only the browser process
    // can read these handles; no names, inheritable handles or socket are used.
    command->AppendSwitch("remote-debugging-pipe");
    command->AppendSwitchWithValue("remote-debugging-io-pipes",std::to_string(reinterpret_cast<uintptr_t>(input))+","+std::to_string(reinterpret_cast<uintptr_t>(output)));
    // This pipe supports Sona's native UI, not a WebDriver session. Preserve
    // ordinary browser navigator.webdriver behavior.
    auto disabled=command->GetSwitchValue("disable-blink-features").ToString();
    if(!disabled.empty())disabled+=",";disabled+="AutomationControlled";
    command->AppendSwitchWithValue("disable-blink-features",disabled);
  }
  void Start(){
    if(!read_||running_)return;running_=true;
    reader_=std::thread([this]{
      std::string buffered;char bytes[8192];
      while(running_){
        DWORD available=0;
        if(!PeekNamedPipe(read_,nullptr,0,nullptr,&available,nullptr))break;
        if(!available){Sleep(10);continue;}
        DWORD count=0;if(!ReadFile(read_,bytes,std::min<DWORD>(available,sizeof(bytes)),&count,nullptr)||!count)break;
        buffered.append(bytes,count);
        for(size_t end;(end=buffered.find('\0'))!=std::string::npos;){
          auto message=buffered.substr(0,end);buffered.erase(0,end+1);
          CefPostTask(TID_UI,new Task([message]{Instance().Receive(message);}));
        }
        if(buffered.size()>1024*1024)break;
      }
    });
  }
  void Stop(){
    running_=false;if(reader_.joinable())reader_.join();
    if(read_)CloseHandle(read_);if(write_)CloseHandle(write_);read_=write_=nullptr;
    pending_.clear();
  }
  void Trigger(const std::string& extension,const std::string& target,ExtensionReply reply){
    CEF_REQUIRE_UI_THREAD();if(!write_||!running_){reply(nullptr,"Native extension action channel is unavailable");return;}
    const int id=++sequence_;auto command=CefDictionaryValue::Create();command->SetInt("id",id);command->SetString("method","Extensions.triggerAction");
    auto params=CefDictionaryValue::Create();params->SetString("id",extension);params->SetString("targetId",target);command->SetDictionary("params",params);
    auto value=CefValue::Create();value->SetDictionary(command);std::string message=CefWriteJSON(value,JSON_WRITER_DEFAULT);message.push_back('\0');
    pending_[id]=std::move(reply);DWORD written=0;
    if(!WriteFile(write_,message.data(),static_cast<DWORD>(message.size()),&written,nullptr)||written!=message.size()){Finish(id,nullptr,"Native extension action channel failed");return;}
    CefPostDelayedTask(TID_UI,new Task([id]{Instance().Finish(id,nullptr,"Native extension action timed out");}),15000);
  }
  static Pipe& Instance(){static Pipe instance;return instance;}
 private:
  void Receive(const std::string& message){
    auto value=CefParseJSON(message,JSON_PARSER_RFC);auto data=value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():nullptr;
    if(!data||!data->HasKey("id"))return;
    auto error=data->GetDictionary("error");auto result=data->GetDictionary("result");
    Finish(data->GetInt("id"),result,error?error->GetString("message").ToString():std::string());
  }
  void Finish(int id,CefRefPtr<CefDictionaryValue> result,const std::string& error){
    auto found=pending_.find(id);if(found==pending_.end())return;auto reply=std::move(found->second);pending_.erase(found);reply(result,error);
  }
  HANDLE read_=nullptr,write_=nullptr;std::atomic<bool> running_{false};std::thread reader_;
  int sequence_=0;std::map<int,ExtensionReply> pending_;
};
}
void ConfigureExtensionPipe(CefRefPtr<CefCommandLine> command){Pipe::Instance().Configure(command);}
void StartExtensionPipe(){Pipe::Instance().Start();}
void StopExtensionPipe(){Pipe::Instance().Stop();}
void TriggerExtensionAction(const std::string& id,const std::string& target,ExtensionReply reply){Pipe::Instance().Trigger(id,target,std::move(reply));}
}
