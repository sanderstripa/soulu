"""Adapt the audited CEF capture/inference component without linking CEF."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
s=(root/'cef/soulu/home_system.cc').read_text()
core=s[s.index('bool MicrophoneDenied()'):s.index('\n}\nvoid HomeCancelVoice')]
core=core.replace('return std::filesystem::path(path).parent_path()/L"ui"/L"speech"/L"ggml-tiny.bin";', 'return std::filesystem::path(path).parent_path()/L"ggml-tiny.bin";')
core=core.replace('CefString(path.wstring()).ToString()', 'Utf8(path.wstring())')
# Short search utterances do not need a full 30-second encoder window.
core=core.replace('params.language=language==', 'params.audio_ctx=std::clamp(static_cast<int>((audio.size()+319)/320+127)/128*128,384,1500);\n params.language=language==')
includes='''// Soulu CEF local speech component, isolated from the browser process.
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
'''
main=r'''
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
'''
(root/'gecko/speech/main.cpp').write_text(includes+core+main,encoding='utf-8')
