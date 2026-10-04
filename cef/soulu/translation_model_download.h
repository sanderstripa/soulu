#pragma once
#include "include/wrapper/cef_message_router.h"
namespace soulu {
void DownloadTranslationModel(const std::string& sha256,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback);
}
