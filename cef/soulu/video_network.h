#pragma once
#include "include/cef_request_context.h"
#include "include/cef_values.h"
#include <functional>
namespace soulu {
using VideoResult=std::function<void(CefRefPtr<CefDictionaryValue>)>;
void VideoFetch(const std::string& owner,CefRefPtr<CefRequestContext>,CefRefPtr<CefDictionaryValue>,VideoResult);
void VideoAbort(const std::string& owner,const std::string& id);
}
