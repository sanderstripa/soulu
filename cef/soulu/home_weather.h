#pragma once
#include "include/cef_values.h"
#include "include/cef_request_context.h"
#include "examples/soulu/home_system.h"
#include <filesystem>
namespace soulu {
// All requests run through the tab's CEF context and therefore its proxy policy.
void HomeWeather(const std::string& key,const std::filesystem::path& cache_file,
 CefRefPtr<CefRequestContext> context,CefRefPtr<CefDictionaryValue> config,
 CefRefPtr<CefDictionaryValue> location,HomeResult done);
void ForgetPrivateHomeWeather();
}
