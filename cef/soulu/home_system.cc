#include "examples/soulu/home_system.h"
#include "include/cef_task.h"
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Globalization.h>
#include <winrt/Windows.Media.SpeechRecognition.h>
#include <winrt/Windows.Devices.Geolocation.h>
#include <atomic>
#include <chrono>
#include <cmath>
#include <map>
#include <memory>
#include <mutex>
#include <thread>
namespace soulu { namespace {
class Completion final:public CefTask {public:explicit Completion(std::function<void()> fn):fn_(std::move(fn)){}void Execute() override{fn_();}private:std::function<void()> fn_;IMPLEMENT_REFCOUNTING(Completion);};
struct VoiceJob {std::atomic_bool cancelled=false;std::mutex mutex;winrt::Windows::Foundation::IAsyncInfo operation{nullptr};};
std::mutex jobs_mutex;std::map<int,std::shared_ptr<VoiceJob>> jobs;
void Deliver(HomeResult done,CefRefPtr<CefDictionaryValue> result){CefPostTask(TID_UI,new Completion([done=std::move(done),result]{done(result);}));}
}
void HomeCancelVoice(int id){std::shared_ptr<VoiceJob> job;{std::lock_guard lock(jobs_mutex);auto it=jobs.find(id);if(it==jobs.end())return;job=it->second;jobs.erase(it);}job->cancelled=true;std::lock_guard lock(job->mutex);try{if(job->operation)job->operation.Cancel();}catch(...){} }
void HomeRecognize(int id,const std::string& language,HomeResult done){
 HomeCancelVoice(id);auto job=std::make_shared<VoiceJob>();{std::lock_guard lock(jobs_mutex);jobs[id]=job;}
 std::thread([id,job,language,done=std::move(done)]() mutable {
  auto result=CefDictionaryValue::Create();result->SetString("status","unavailable");
  try{winrt::init_apartment(winrt::apartment_type::multi_threaded);using namespace winrt::Windows::Media::SpeechRecognition;
   SpeechRecognizer recognizer(winrt::Windows::Globalization::Language(winrt::to_hstring(language=="en"?"en-US":"ru-RU")));
   recognizer.Constraints().Append(SpeechRecognitionTopicConstraint(SpeechRecognitionScenario::WebSearch,L"Soulu Home"));
   recognizer.Timeouts().InitialSilenceTimeout(std::chrono::seconds(6));recognizer.Timeouts().EndSilenceTimeout(std::chrono::seconds(2));recognizer.Timeouts().BabbleTimeout(std::chrono::seconds(12));
   auto compilation=recognizer.CompileConstraintsAsync();{std::lock_guard lock(job->mutex);job->operation=compilation;if(job->cancelled)compilation.Cancel();}
   if(compilation.get().Status()==SpeechRecognitionResultStatus::Success&&!job->cancelled){auto operation=recognizer.RecognizeAsync();{std::lock_guard lock(job->mutex);job->operation=operation;if(job->cancelled)operation.Cancel();}auto speech=operation.get();if(!job->cancelled&&speech.Status()==SpeechRecognitionResultStatus::Success){result->SetString("status","recognized");result->SetString("text",winrt::to_string(speech.Text()));}}
   recognizer.Close();
  }catch(const winrt::hresult_error& error){if(error.code()==E_ACCESSDENIED)result->SetString("status","denied");}catch(...){}
  if(job->cancelled)result->SetString("status","cancelled");{std::lock_guard lock(jobs_mutex);auto it=jobs.find(id);if(it!=jobs.end()&&it->second==job)jobs.erase(it);}
  {std::lock_guard lock(job->mutex);job->operation=nullptr;}Deliver(std::move(done),result);
 }).detach();
}
void HomeLocate(HomeResult done){std::thread([done=std::move(done)]() mutable {auto result=CefDictionaryValue::Create();result->SetString("status","unavailable");try{winrt::init_apartment(winrt::apartment_type::multi_threaded);using namespace winrt::Windows::Devices::Geolocation;Geolocator locator;locator.DesiredAccuracy(PositionAccuracy::Default);auto position=locator.GetGeopositionAsync(std::chrono::minutes(15),std::chrono::seconds(10)).get();auto point=position.Coordinate().Point().Position();result->SetString("status","ready");result->SetDouble("latitude",std::round(point.Latitude*100)/100);result->SetDouble("longitude",std::round(point.Longitude*100)/100);}catch(...){}Deliver(std::move(done),result);}).detach();}
}
