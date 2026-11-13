#pragma once

#include "include/cef_app.h"

namespace sona {
CefRefPtr<CefApp> CreateBrowserApp();
CefRefPtr<CefApp> CreateRendererApp();
CefRefPtr<CefApp> CreateOtherApp();
}
