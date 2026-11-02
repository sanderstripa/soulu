#include <windows.h>

#include "examples/soulu/app_factory.h"
#include "examples/soulu/extension_pipe.h"
#include "examples/soulu/browser_window.h"

namespace soulu {
class BrowserApp final : public CefApp, public CefBrowserProcessHandler {
 public:
  CefRefPtr<CefBrowserProcessHandler> GetBrowserProcessHandler() override { return this; }

  void OnBeforeCommandLineProcessing(const CefString& process_type,
                                     CefRefPtr<CefCommandLine> command_line) override {
    if (process_type.empty()) {
      wchar_t test_port[12] = {};
      if (GetEnvironmentVariableW(L"SOULU_UI_TEST_PORT", test_port, 12) > 0)
        command_line->AppendSwitchWithValue("remote-allow-origins", "*");
      command_line->AppendSwitch("enable-gpu-rasterization");
      // Native-only action dispatch uses a browser-level anonymous pipe.
      // No network listener or generic UI-to-CDP proxy is exposed.
      command_line->AppendSwitch("enable-unsafe-extension-debugging");
      ConfigureExtensionPipe(command_line);
      command_line->AppendSwitchWithValue("autoplay-policy", "document-user-activation-required");
    }
  }

  CefRefPtr<CefClient> GetDefaultClient() override {return ExtensionDefaultClient();}

  void OnContextInitialized() override { StartExtensionPipe(); BrowserWindow::Create(); }
  bool OnAlreadyRunningAppRelaunch(CefRefPtr<CefCommandLine> command_line,
      const CefString&) override {
    CefCommandLine::ArgumentList arguments;command_line->GetArguments(arguments);
    for(const auto& argument:arguments)BrowserWindow::OpenExternal(argument.ToString());
    return true;
  }

 private:
  IMPLEMENT_REFCOUNTING(BrowserApp);
};

CefRefPtr<CefApp> CreateBrowserApp() { return new BrowserApp(); }
}
