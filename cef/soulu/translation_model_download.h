#pragma once
#include "include/wrapper/cef_message_router.h"
namespace soulu {
void DownloadTranslationModel(const std::string& sha256,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback);
void TranslationModelCache(const std::string& operation,const std::string& sha256,CefRefPtr<CefMessageRouterBrowserSide::Callback> callback);
}
