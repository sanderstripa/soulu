#include "examples/soulu/home_system.h"
#include "include/cef_task.h"
#include "include/cef_parser.h"
#include <windows.h>
#include <mmsystem.h>
#include <bcrypt.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Devices.Geolocation.h>
#include "whisper.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>
namespace soulu { namespace {
class Completion final:public CefTask {public:explicit Completion(std::function<void()> fn):fn_(std::move(fn)){}void Execute() override{fn_();}private:std::function<void()> fn_;IMPLEMENT_REFCOUNTING(Completion);};
struct VoiceJob {std::atomic_bool cancelled=false;};
std::mutex jobs_mutex;std::map<int,std::shared_ptr<VoiceJob>> jobs;
std::mutex recognition_mutex;
void Deliver(HomeResult done,CefRefPtr<CefDictionaryValue> result){CefPostTask(TID_UI,new Completion([done=std::move(done),result]{done(result);}));}
bool MicrophoneDenied(){
 const wchar_t* base=L"Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone";
 for(HKEY root:{HKEY_CURRENT_USER,HKEY_LOCAL_MACHINE})for(const std::wstring suffix:{L"",L"\\NonPackaged"}){
  wchar_t value[32]={};DWORD bytes=sizeof(value);
  if(RegGetValueW(root,(std::wstring(base)+suffix).c_str(),L"Value",RRF_RT_REG_SZ,nullptr,value,&bytes)==ERROR_SUCCESS&&_wcsicmp(value,L"Deny")==0)return true;
 }
 return false;
}
std::filesystem::path ModelPath(){wchar_t path[32768]={};GetModuleFileNameW(nullptr,path,32768);return std::filesystem::path(path).parent_path()/L"ui"/L"speech"/L"ggml-tiny.bin";}
// Verify the bundled model before handing bytes to the inference library.
bool VerifiedModel(const std::filesystem::path& path){
 std::error_code error;if(std::filesystem::file_size(path,error)!=77691713||error)return false;
 BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;
 if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return false;
 bool ok=BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)>=0;std::ifstream stream(path,std::ios::binary);std::array<unsigned char,65536> buffer;
 while(ok&&stream){stream.read(reinterpret_cast<char*>(buffer.data()),buffer.size());if(stream.gcount())ok=BCryptHashData(hash,buffer.data(),static_cast<ULONG>(stream.gcount()),0)>=0;}
 std::array<unsigned char,32> digest{};if(ok)ok=BCryptFinishHash(hash,digest.data(),static_cast<ULONG>(digest.size()),0)>=0;
 if(hash)BCryptDestroyHash(hash);BCryptCloseAlgorithmProvider(algorithm,0);if(!ok)return false;
 std::string hex;const char* digits="0123456789abcdef";for(auto byte:digest){hex+=digits[byte>>4];hex+=digits[byte&15];}
 return hex=="be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21";
}
void QuietLog(enum ggml_log_level,const char*,void*){}
std::string Transcribe(const std::vector<float>& audio,const std::string& language,std::atomic_bool& cancelled,bool* timed_out=nullptr){
 // One inference at a time; cancelled jobs never queue additional model loads.
 std::unique_lock lock(recognition_mutex);if(cancelled||audio.size()<8000||audio.size()>320000)return "";
 const auto path=ModelPath();if(!VerifiedModel(path)||cancelled)return "";
 whisper_log_set(QuietLog,nullptr);auto options=whisper_context_default_params();options.use_gpu=false;
 const auto filename=CefString(path.wstring()).ToString();
 std::unique_ptr<whisper_context,decltype(&whisper_free)> context(whisper_init_from_file_with_params(filename.c_str(),options),whisper_free);
 if(!context||cancelled)return "";
 auto params=whisper_full_default_params(WHISPER_SAMPLING_GREEDY);params.n_threads=std::clamp(static_cast<int>(std::thread::hardware_concurrency()),1,4);
 params.language=language=="en"?"en":"ru";params.translate=false;params.no_context=true;params.no_timestamps=true;params.single_segment=true;
 params.print_realtime=false;params.print_progress=false;params.print_timestamps=false;params.max_tokens=128;
 struct AbortState{std::atomic_bool& cancelled;std::chrono::steady_clock::time_point deadline;bool timed_out=false;};
 AbortState abort{cancelled,std::chrono::steady_clock::now()+std::chrono::seconds(60)};
 params.abort_callback=[](void* data){auto& state=*static_cast<AbortState*>(data);state.timed_out=std::chrono::steady_clock::now()>=state.deadline;return state.cancelled.load()||state.timed_out;};params.abort_callback_user_data=&abort;
 const int inference=whisper_full(context.get(),params,audio.data(),static_cast<int>(audio.size()));
 if(timed_out)*timed_out=abort.timed_out;
 if(inference!=0||cancelled||abort.timed_out)return "";
 std::string text;for(int i=0;i<whisper_full_n_segments(context.get());++i)text+=whisper_full_get_segment_text(context.get(),i);
 const auto begin=text.find_first_not_of(" \t\r\n");return begin==std::string::npos?"":text.substr(begin,text.find_last_not_of(" \t\r\n")-begin+1);
}
struct SecureAudio {
 std::vector<float> samples;
 ~SecureAudio(){if(!samples.empty())SecureZeroMemory(samples.data(),samples.size()*sizeof(float));}
};
class Capture {
 public:~Capture(){if(input){waveInReset(input);for(auto& header:headers)if(header.dwFlags&WHDR_PREPARED)waveInUnprepareHeader(input,&header,sizeof(header));waveInClose(input);}if(event)CloseHandle(event);SecureZeroMemory(samples.data(),sizeof(samples));}
 HWAVEIN input=nullptr;HANDLE event=nullptr;std::array<std::array<short,1600>,2> samples{};std::array<WAVEHDR,2> headers{};
 bool Start(){event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;WAVEFORMATEX format{};format.wFormatTag=WAVE_FORMAT_PCM;format.nChannels=1;format.nSamplesPerSec=16000;format.wBitsPerSample=16;format.nBlockAlign=2;format.nAvgBytesPerSec=32000;
 if(waveInOpen(&input,WAVE_MAPPER,&format,reinterpret_cast<DWORD_PTR>(event),0,CALLBACK_EVENT)!=MMSYSERR_NOERROR)return false;
 for(size_t i=0;i<headers.size();++i){auto& header=headers[i];header.lpData=reinterpret_cast<LPSTR>(samples[i].data());header.dwBufferLength=3200;if(waveInPrepareHeader(input,&header,sizeof(header))!=MMSYSERR_NOERROR||waveInAddBuffer(input,&header,sizeof(header))!=MMSYSERR_NOERROR)return false;}
 return waveInStart(input)==MMSYSERR_NOERROR;}
};
}
void HomeCancelVoice(int id){std::lock_guard lock(jobs_mutex);auto it=jobs.find(id);if(it!=jobs.end()){it->second->cancelled=true;jobs.erase(it);}}
double HomeSpeechThreshold(std::array<double,5> noise){std::sort(noise.begin(),noise.end());return std::max(.003,noise[2]*2.5);}
void HomeRecognize(int id,const std::string& language,HomeResult done,std::function<void(const std::string&)> progress){
 HomeCancelVoice(id);auto job=std::make_shared<VoiceJob>();{std::lock_guard lock(jobs_mutex);jobs[id]=job;}
 std::thread([id,job,language,done=std::move(done),progress=std::move(progress)]() mutable {
  const auto phase=[&](const std::string& value){CefPostTask(TID_UI,new Completion([job,progress,value]{if(!job->cancelled)progress(value);}));};
  auto result=CefDictionaryValue::Create();result->SetString("status","unavailable");
  try{
   if(MicrophoneDenied())result->SetString("status","denied");
   else {SecureAudio storage;auto& audio=storage.samples;bool voiced=false;int silent=0;size_t calibration=0;std::array<double,5> noise{};double threshold=.003;
    {Capture capture;if(capture.Start()){
     const auto start=std::chrono::steady_clock::now();
     while(!job->cancelled&&std::chrono::steady_clock::now()-start<std::chrono::seconds(15)){
      WaitForSingleObject(capture.event,100);
      for(size_t i=0;i<capture.headers.size();++i){auto& header=capture.headers[i];if(!(header.dwFlags&WHDR_DONE))continue;
       double energy=0;const size_t count=header.dwBytesRecorded/2;
       for(size_t j=0;j<count;++j){const float value=capture.samples[i][j]/32768.0f;audio.push_back(value);energy+=value*value;}
       const double rms=count?std::sqrt(energy/count):0;
       // Calibrate before announcing readiness; a single click must not set the noise floor.
       if(count&&calibration<noise.size()){
        noise[calibration++]=rms;
        if(calibration==noise.size()){threshold=HomeSpeechThreshold(noise);phase("listening");}
       }else if(count&&rms>threshold){voiced=true;silent=0;}else ++silent;
       header.dwBytesRecorded=0;if(!job->cancelled)waveInAddBuffer(capture.input,&header,sizeof(header));
      }
      if((voiced&&silent>=15)||(!voiced&&silent>=60))break;
     }
    }} // Release the microphone before inference. Audio never touches disk.
    if(voiced&&!job->cancelled){phase("processing");bool timed_out=false;const auto text=Transcribe(audio,language,job->cancelled,&timed_out);if(!text.empty()){result->SetString("status","recognized");result->SetString("text",text);}else result->SetString("status",timed_out?"unavailable":"unrecognized");}
    else if(!job->cancelled&&audio.size()>=8000)result->SetString("status","no_speech");
   }
  }catch(...){}
  if(job->cancelled)result->SetString("status","cancelled");{std::lock_guard lock(jobs_mutex);auto it=jobs.find(id);if(it!=jobs.end()&&it->second==job)jobs.erase(it);}
  Deliver(std::move(done),result);
 }).detach();
}
std::string HomeTranscribeTest(const std::vector<float>& audio,const std::string& language){std::atomic_bool cancelled=false;std::string text;std::thread worker([&]{try{text=Transcribe(audio,language,cancelled);}catch(...){}});worker.join();return text;}
void HomeLocate(HomeResult done){std::thread([done=std::move(done)]() mutable {auto result=CefDictionaryValue::Create();result->SetString("status","unavailable");try{winrt::init_apartment(winrt::apartment_type::multi_threaded);using namespace winrt::Windows::Devices::Geolocation;Geolocator locator;locator.DesiredAccuracy(PositionAccuracy::Default);auto position=locator.GetGeopositionAsync(std::chrono::minutes(15),std::chrono::seconds(10)).get();auto point=position.Coordinate().Point().Position();result->SetString("status","ready");result->SetDouble("latitude",std::round(point.Latitude*100)/100);result->SetDouble("longitude",std::round(point.Longitude*100)/100);}catch(...){}Deliver(std::move(done),result);}).detach();}
}
