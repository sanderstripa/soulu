#pragma once
#include "include/cef_render_process_handler.h"
namespace soulu {
void InstallVideoRuntime(CefRefPtr<CefBrowser>,CefRefPtr<CefFrame>,CefRefPtr<CefV8Context>);
void ForgetVideoContext(CefRefPtr<CefV8Context>);
bool HandleVideoResponse(CefRefPtr<CefFrame>,CefProcessId,CefRefPtr<CefProcessMessage>);
}
