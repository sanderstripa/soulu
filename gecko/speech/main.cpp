// Soulu CEF local speech component, isolated from the browser process.
#include <windows.h>
#include <mmsystem.h>
#include <bcrypt.h>
#include "whisper.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <memory>
#include <mutex>
#include <thread>
#include <vector>
#include <iostream>
#include <string>
std::mutex recognition_mutex;
std::string Utf8(const std::wstring& w){int n=WideCharToMultiByte(CP_UTF8,0,w.data(),int(w.size()),nullptr,0,nullptr,nullptr);std::string s(n,' ');WideCharToMultiByte(CP_UTF8,0,w.data(),int(w.size()),s.data(),n,nullptr,nullptr);return s;}
bool MicrophoneDenied(){
 const wchar_t* base=L"Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone";
 for(HKEY root:{HKEY_CURRENT_USER,HKEY_LOCAL_MACHINE})for(const std::wstring suffix:{L"",L"\\NonPackaged"}){
  wchar_t value[32]={};DWORD bytes=sizeof(value);
  if(RegGetValueW(root,(std::wstring(base)+suffix).c_str(),L"Value",RRF_RT_REG_SZ,nullptr,value,&bytes)==ERROR_SUCCESS&&_wcsicmp(value,L"Deny")==0)return true;
 }
 return false;
}
std::filesystem::path ModelPath(){wchar_t path[32768]={};GetModuleFileNameW(nullptr,path,32768);return std::filesystem::path(path).parent_path()/L"ggml-tiny.bin";}
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
struct SecureAudio {
 std::vector<float> samples;
 ~SecureAudio(){if(!samples.empty())SecureZeroMemory(samples.data(),samples.size()*sizeof(float));}
};
std::string Transcribe(const std::vector<float>& audio,const std::string& language,std::atomic_bool& cancelled,bool* timed_out=nullptr){
 // One inference at a time; cancelled jobs never queue additional model loads.
 std::unique_lock lock(recognition_mutex);if(cancelled||audio.size()<8000||audio.size()>320000)return "";
 const auto path=ModelPath();if(!VerifiedModel(path)||cancelled)return "";
 whisper_log_set(QuietLog,nullptr);auto options=whisper_context_default_params();options.use_gpu=false;
 const auto filename=Utf8(path.wstring());
 std::unique_ptr<whisper_context,decltype(&whisper_free)> context(whisper_init_from_file_with_params(filename.c_str(),options),whisper_free);
 if(!context||cancelled)return "";
 // Camera microphones can deliver speech far below the model's normal PCM
 // level. Gain only quiet, already voice-qualified input, with a bounded gain.
 // Both this working copy and the original capture are securely cleared.
 SecureAudio prepared;prepared.samples=audio;float peak=0;
 for(float sample:prepared.samples)peak=std::max(peak,std::abs(sample));
 if(peak>0&&peak<.5f){const float gain=std::min(32.f,.5f/peak);for(auto& sample:prepared.samples)sample*=gain;}
 auto params=whisper_full_default_params(WHISPER_SAMPLING_GREEDY);params.n_threads=std::clamp(static_cast<int>(std::thread::hardware_concurrency()),1,4);
 params.language=language=="en"?"en":"ru";params.translate=false;params.no_context=true;params.no_timestamps=true;params.single_segment=true;
 params.print_realtime=false;params.print_progress=false;params.print_timestamps=false;params.max_tokens=128;
 struct AbortState{std::atomic_bool& cancelled;std::chrono::steady_clock::time_point deadline;bool timed_out=false;};
 AbortState abort{cancelled,std::chrono::steady_clock::now()+std::chrono::seconds(60)};
 params.abort_callback=[](void* data){auto& state=*static_cast<AbortState*>(data);state.timed_out=std::chrono::steady_clock::now()>=state.deadline;return state.cancelled.load()||state.timed_out;};params.abort_callback_user_data=&abort;
 const int inference=whisper_full(context.get(),params,prepared.samples.data(),static_cast<int>(prepared.samples.size()));
 if(timed_out)*timed_out=abort.timed_out;
 if(inference!=0||cancelled||abort.timed_out)return "";
 std::string text;for(int i=0;i<whisper_full_n_segments(context.get());++i)text+=whisper_full_get_segment_text(context.get(),i);
 const auto begin=text.find_first_not_of(" \t\r\n");return begin==std::string::npos?"":text.substr(begin,text.find_last_not_of(" \t\r\n")-begin+1);
}
class Capture {
 public:~Capture(){if(input){waveInReset(input);for(auto& header:headers)if(header.dwFlags&WHDR_PREPARED)waveInUnprepareHeader(input,&header,sizeof(header));waveInClose(input);}if(event)CloseHandle(event);SecureZeroMemory(samples.data(),sizeof(samples));}
 HWAVEIN input=nullptr;HANDLE event=nullptr;std::array<std::array<short,1600>,2> samples{};std::array<WAVEHDR,2> headers{};
 bool Start(){event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;WAVEFORMATEX format{};format.wFormatTag=WAVE_FORMAT_PCM;format.nChannels=1;format.nSamplesPerSec=16000;format.wBitsPerSample=16;format.nBlockAlign=2;format.nAvgBytesPerSec=32000;
 if(waveInOpen(&input,WAVE_MAPPER,&format,reinterpret_cast<DWORD_PTR>(event),0,CALLBACK_EVENT)!=MMSYSERR_NOERROR)return false;
 for(size_t i=0;i<headers.size();++i){auto& header=headers[i];header.lpData=reinterpret_cast<LPSTR>(samples[i].data());header.dwBufferLength=3200;if(waveInPrepareHeader(input,&header,sizeof(header))!=MMSYSERR_NOERROR||waveInAddBuffer(input,&header,sizeof(header))!=MMSYSERR_NOERROR)return false;}
 return waveInStart(input)==MMSYSERR_NOERROR;}
};
int main(int argc,char** argv){
 std::string language=argc>1&&std::string(argv[1])=="en"?"en":"ru";
 std::atomic_bool cancelled=false;SecureAudio storage;auto& audio=storage.samples;
 try{
  if(argc==4&&std::string(argv[2])=="--pcm-test"){
   std::ifstream f(argv[3],std::ios::binary);short sample;while(f.read(reinterpret_cast<char*>(&sample),2)&&audio.size()<=320000)audio.push_back(sample/32768.f);
  }else{
   if(MicrophoneDenied()){std::cout<<"denied\n";return 0;}
   bool voiced=false;int silent=0;size_t calibration=0;std::array<double,5> noise{};double threshold=.003;
   {Capture capture;if(!capture.Start()){std::cout<<"unavailable\n";return 0;}
    const auto start=std::chrono::steady_clock::now();
    while(std::chrono::steady_clock::now()-start<std::chrono::seconds(15)){
     WaitForSingleObject(capture.event,100);
     for(size_t i=0;i<capture.headers.size();i++){
      auto& header=capture.headers[i];if(!(header.dwFlags&WHDR_DONE))continue;double energy=0;const size_t count=header.dwBytesRecorded/2;
      for(size_t j=0;j<count;j++){const float value=capture.samples[i][j]/32768.f;audio.push_back(value);energy+=value*value;}
      const double rms=count?std::sqrt(energy/count):0;
      if(count&&calibration<noise.size()){noise[calibration++]=rms;if(calibration==noise.size()){std::sort(noise.begin(),noise.end());threshold=std::max(.003,noise[2]*2.5);std::cerr<<"listening\n"<<std::flush;}}
      else if(count&&rms>threshold){voiced=true;silent=0;}else ++silent;
      header.dwBytesRecorded=0;waveInAddBuffer(capture.input,&header,sizeof(header));
     }
     if((voiced&&silent>=15)||(!voiced&&silent>=60))break;
    }
   }
   if(!voiced){std::cout<<"no_speech\n";return 0;}
  }
  std::cerr<<"processing\n"<<std::flush;bool timeout=false;auto text=Transcribe(audio,language,cancelled,&timeout);
  std::cout<<(text.empty()?(timeout?"unavailable":"unrecognized"):"recognized")<<"\n"<<text;
 }catch(...){std::cout<<"unavailable\n";return 1;}
}
