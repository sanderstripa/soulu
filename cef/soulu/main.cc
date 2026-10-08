#include <windows.h>

#include <filesystem>
#include <cstdlib>
#include <fstream>
#include "examples/soulu/engine_version.h"
#include "examples/soulu/adblock_bridge.h"

#include "examples/soulu/app_factory.h"
#include "examples/soulu/profile_data.h"
#include "examples/soulu/home_system.h"
#include "include/cef_command_line.h"
namespace soulu { int RunDataSecurityTests(const std::filesystem::path&); int RunBrowserImportTests(const std::filesystem::path&); }

namespace {
std::filesystem::path SouluDataRoot() {
  // Chrome-style CEF requires disk profiles to be immediate children of
  // root_cache_path. BrowserWindow uses Soulu/User Data/Profiles/<id>.
  // Keep those paths unchanged and align the CEF root with their parent.
  auto root=soulu::DataRoot()/L"Profiles";root.make_preferred();return root;
}

std::wstring LocalDataPath() {
  return (SouluDataRoot() / L"CEF").wstring();
}
}

int APIENTRY wWinMain(HINSTANCE instance, HINSTANCE, wchar_t*, int) {
  CefMainArgs main_args(instance);
  auto command_line = CefCommandLine::CreateCommandLine();
  command_line->InitFromString(GetCommandLineW());
  if(command_line->HasSwitch("home-speech-test-file")){
    wchar_t enabled[12]={};if(!GetEnvironmentVariableW(L"SOULU_UI_TEST_PORT",enabled,12))return 2;
    const std::filesystem::path input(command_line->GetSwitchValue("home-speech-test-file").ToWString());
    std::error_code error;const auto size=std::filesystem::file_size(input,error);
    if(error||size<16000||size>640000||size%2)return 2;
    std::ifstream stream(input,std::ios::binary);std::vector<short> pcm(static_cast<size_t>(size/2));
    stream.read(reinterpret_cast<char*>(pcm.data()),static_cast<std::streamsize>(size));if(!stream)return 2;
    std::vector<float> audio;audio.reserve(pcm.size());for(auto sample:pcm)audio.push_back(sample/32768.0f);
    const std::string language=command_line->GetSwitchValue("home-speech-test-language");if(language!="ru"&&language!="en")return 2;
    const auto text=soulu::HomeTranscribeTest(audio,language);
    std::ofstream report(std::filesystem::path(command_line->GetSwitchValue("home-speech-test-report").ToWString()),std::ios::binary);report<<text;
    return report&&!text.empty()?0:2;
  }
  if(command_line->HasSwitch("browser-import-test-report")){
    wchar_t enabled[12]={},test_root[32768]={},local[32768]={},roaming[32768]={};
    if(!GetEnvironmentVariableW(L"SOULU_UI_TEST_PORT",enabled,12)||
       !GetEnvironmentVariableW(L"SOULU_DATA_SECURITY_TEST_ROOT",test_root,32768)||
       !GetEnvironmentVariableW(L"LOCALAPPDATA",local,32768)||
       !GetEnvironmentVariableW(L"APPDATA",roaming,32768)||
       std::wstring(test_root)!=local||std::wstring(test_root)!=roaming)return 2;
    return soulu::RunBrowserImportTests(std::filesystem::path(command_line->GetSwitchValue("browser-import-test-report").ToWString()));
  }
  if(command_line->HasSwitch("data-security-test-report")){
    wchar_t enabled[12]={};
    if(!GetEnvironmentVariableW(L"SOULU_UI_TEST_PORT",enabled,12))return 2;
    wchar_t test_root[32768]={},local[32768]={},roaming[32768]={};
    if(!GetEnvironmentVariableW(L"SOULU_DATA_SECURITY_TEST_ROOT",test_root,32768)||
       !GetEnvironmentVariableW(L"LOCALAPPDATA",local,32768)||
       !GetEnvironmentVariableW(L"APPDATA",roaming,32768)||
       std::wstring(test_root)!=local||std::wstring(test_root)!=roaming)return 2;
    auto test_cache=(soulu::DataRoot()/L"AdBlock"/L"filters-v1.json").u8string();
    soulu::InitializeAdBlock(std::string(test_cache.begin(),test_cache.end()),"",false);
    return soulu::RunDataSecurityTests(std::filesystem::path(command_line->GetSwitchValue("data-security-test-report").ToWString()));
  }
  // CI probes the linked libcef before profile initialization or message loops.
  if (command_line->HasSwitch("engine-version-file")) {
    const std::filesystem::path output(
        command_line->GetSwitchValue("engine-version-file").ToWString());
    std::ofstream report(output);
    report << "{\"cef\":\"" << soulu::EngineVersion(0, 3)
           << "\",\"chromium\":\"" << soulu::EngineVersion(4, 4)
           << "\",\"cef_build\":\"" << soulu::RuntimeCEFBuild() << "\"}";
    report.close();
    return report && soulu::ApprovedEngine() ? 0 : 2;
  }
  if (!soulu::ApprovedEngine()) return 2;
  const auto process_type = command_line->GetSwitchValue("type");

  CefRefPtr<CefApp> app;
  if (process_type == "renderer") app = soulu::CreateRendererApp();
  else if (process_type.empty()) app = soulu::CreateBrowserApp();
  else app = soulu::CreateOtherApp();

  const int code = CefExecuteProcess(main_args, app, nullptr);
  if (code >= 0) return code;

  CefSettings settings;
  settings.no_sandbox = true;
  settings.windowless_rendering_enabled = true;
  // Expose DevTools only in the dedicated CI test process.
  wchar_t test_port[12] = {};
  if (GetEnvironmentVariableW(L"SOULU_UI_TEST_PORT", test_port, 12) > 0)
    settings.remote_debugging_port = _wtoi(test_port);
  settings.multi_threaded_message_loop = false;
  CefString(&settings.cache_path) = LocalDataPath();
  CefString(&settings.root_cache_path) = SouluDataRoot().wstring();
  settings.persist_session_cookies = 1;
  CefString(&settings.locale) = "ru-RU";
  CefString(&settings.accept_language_list) = "ru-RU,ru,en-US,en";
  // Compile bundled/cache rules before CEF can load the first web page.
  auto cache=soulu::DataRoot()/L"AdBlock"/L"filters-v1.json";
  auto cache_utf8=cache.u8string();
  // Fixture loading/update suppression is restricted to the explicit test process.
  wchar_t fixture[32768]={},no_update[12]={};
  const bool testing=GetEnvironmentVariableW(L"SOULU_UI_TEST_PORT",test_port,12)>0;
  if(testing)GetEnvironmentVariableW(L"SOULU_ADBLOCK_TEST_RULES",fixture,32768);
  const bool updates=!(testing&&GetEnvironmentVariableW(L"SOULU_ADBLOCK_NO_UPDATE",no_update,12)>0);
  soulu::InitializeAdBlock(std::string(cache_utf8.begin(),cache_utf8.end()),CefString(fixture).ToString(),updates);
  if (!CefInitialize(main_args, settings, app, nullptr)) return 1;
  CefRunMessageLoop();
  const auto deletions=soulu::PendingProfileDeletions();
  CefShutdown();
  soulu::CleanupDeletedProfiles(deletions);
  return 0;
}

