#include "examples/soulu/vpn_helper.h"
#include "include/cef_parser.h"
#include "include/cef_task.h"
#include <windows.h>
#include <filesystem>
#include <mutex>
#include <memory>
#include <algorithm>
#include <functional>
#include <cstdint>
namespace soulu {
namespace {
class Task final:public CefTask{public:explicit Task(std::function<void()> fn):fn_(std::move(fn)){}void Execute()override{fn_();}private:std::function<void()> fn_;IMPLEMENT_REFCOUNTING(Task);};
CefRefPtr<CefDictionaryValue> Failure(const std::string& message){auto value=CefDictionaryValue::Create();value->SetBool("ok",false);value->SetString("error",message);return value;}
std::string Json(CefRefPtr<CefDictionaryValue> row){auto value=CefValue::Create();value->SetDictionary(row);return CefWriteJSON(value,JSON_WRITER_DEFAULT);}
std::filesystem::path HostPath(){wchar_t exe[32768]={};GetModuleFileNameW(nullptr,exe,32768);return std::filesystem::path(exe).parent_path()/L"vpn"/L"native-host"/L"SouluVpnHost.exe";}
struct Process{
 HANDLE process=nullptr,job=nullptr,input=nullptr,output=nullptr;
 ~Process(){if(input)CloseHandle(input);if(process){if(WaitForSingleObject(process,3000)==WAIT_TIMEOUT&&job)TerminateJobObject(job,1);CloseHandle(process);}if(output)CloseHandle(output);if(job)CloseHandle(job);}
 bool Alive()const{return process&&WaitForSingleObject(process,0)==WAIT_TIMEOUT;}
 bool Start(bool component){
  const auto path=HostPath();std::error_code error;if(!std::filesystem::is_regular_file(path,error))return false;
  SECURITY_ATTRIBUTES security={sizeof(SECURITY_ATTRIBUTES),nullptr,TRUE};HANDLE in_read=nullptr,out_write=nullptr;
  if(!CreatePipe(&in_read,&input,&security,0))return false;
  if(!CreatePipe(&output,&out_write,&security,0)){CloseHandle(in_read);return false;}
  SetHandleInformation(input,HANDLE_FLAG_INHERIT,0);SetHandleInformation(output,HANDLE_FLAG_INHERIT,0);
  HANDLE null=CreateFileW(L"NUL",GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,&security,OPEN_EXISTING,0,nullptr);
  STARTUPINFOW startup={sizeof(startup)};startup.dwFlags=STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;startup.wShowWindow=SW_HIDE;startup.hStdInput=in_read;startup.hStdOutput=out_write;startup.hStdError=null;
  PROCESS_INFORMATION pi={};std::wstring command=L"\""+path.wstring()+L"\""+(component?L" --components":L"");
  const bool started=CreateProcessW(nullptr,command.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW|CREATE_SUSPENDED,nullptr,path.parent_path().c_str(),&startup,&pi)!=0;
  CloseHandle(in_read);CloseHandle(out_write);if(null!=INVALID_HANDLE_VALUE)CloseHandle(null);if(!started)return false;process=pi.hProcess;
  job=CreateJobObjectW(nullptr,nullptr);JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits={};limits.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
  if(!job||!SetInformationJobObject(job,JobObjectExtendedLimitInformation,&limits,sizeof(limits))||!AssignProcessToJobObject(job,process)){TerminateProcess(process,1);CloseHandle(pi.hThread);return false;}
  ResumeThread(pi.hThread);CloseHandle(pi.hThread);return true;
 }
 bool Read(void* buffer,size_t size,ULONGLONG deadline){
  auto* bytes=static_cast<char*>(buffer);size_t offset=0;
  while(offset<size&&GetTickCount64()<deadline){DWORD available=0;if(!PeekNamedPipe(output,nullptr,0,nullptr,&available,nullptr))return false;if(!available){if(!Alive())return false;Sleep(10);continue;}DWORD count=0;const DWORD chunk=static_cast<DWORD>(std::min<size_t>(available,size-offset));if(!ReadFile(output,bytes+offset,chunk,&count,nullptr)||!count)return false;offset+=count;}
  return offset==size;
 }
 CefRefPtr<CefDictionaryValue> Exchange(CefRefPtr<CefDictionaryValue> request,bool component){
  const auto data=Json(request);if(data.empty()||data.size()>1024*1024)return Failure("Invalid VPN request");
  const uint32_t length=static_cast<uint32_t>(data.size());DWORD count=0;
  if(!WriteFile(input,&length,sizeof(length),&count,nullptr)||count!=sizeof(length)||!WriteFile(input,data.data(),length,&count,nullptr)||count!=length)return Failure("VPN helper input failed");
  const auto deadline=GetTickCount64()+(component?180000:18000);uint32_t size=0;
  if(!Read(&size,sizeof(size),deadline)||!size||size>8*1024*1024)return Failure("VPN helper did not respond");
  std::string raw(size,'\0');if(!Read(raw.data(),raw.size(),deadline))return Failure("VPN helper response timed out");
  auto value=CefParseJSON(raw,JSON_PARSER_RFC);return value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():Failure("Invalid VPN helper response");
 }
};
std::mutex host_mutex;std::unique_ptr<Process> host;
}
CefRefPtr<CefDictionaryValue> VpnHelperRequest(CefRefPtr<CefDictionaryValue> request){
 std::lock_guard lock(host_mutex);if(!host||!host->Alive()){host=std::make_unique<Process>();if(!host->Start(false)){host.reset();return Failure("VPN helper is unavailable");}}
 return host->Exchange(request,false);
}
void ShutdownVpnHelper(){std::lock_guard lock(host_mutex);host.reset();}
void VpnComponentRequest(CefRefPtr<CefDictionaryValue> request,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback){
 if(!request){callback->Failure(400,"Missing component request");return;}
 const std::string component=request->GetString("component"),operation=request->GetString("operation"),version=request->GetString("version");
 if((component!="xray"&&component!="sudoku")||(operation!="status"&&operation!="list"&&operation!="install"&&operation!="rollback")||version.size()>80){callback->Failure(400,"Invalid component operation");return;}
 auto args=CefDictionaryValue::Create();args->SetString("action","components");args->SetString("component",component);args->SetString("name",operation);args->SetString("version",version);args->SetBool("check",request->GetBool("check"));args->SetBool("proxy",request->GetBool("proxy"));
 CefPostTask(TID_FILE_USER_BLOCKING,new Task([args,callback]{Process process;auto result=process.Start(true)?process.Exchange(args,true):Failure("Component helper is unavailable");const auto json=Json(result);CefPostTask(TID_UI,new Task([callback,json]{callback->Success(json);}));}));
}
}
