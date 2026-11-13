#pragma once
#include "include/cef_values.h"
#include "include/cef_request_context.h"
#include "examples/sona/home_system.h"
#include <filesystem>
namespace sona {
// All requests run through the tab's CEF context and therefore its proxy policy.
void HomeWeather(const std::string& key,const std::filesystem::path& cache_file,
 CefRefPtr<CefRequestContext> context,CefRefPtr<CefDictionaryValue> config,
 CefRefPtr<CefDictionaryValue> location,HomeResult done);
bool ValidHomeWeather(CefRefPtr<CefDictionaryValue> data);
CefRefPtr<CefDictionaryValue> HomeWeatherSnapshot(CefRefPtr<CefDictionaryValue> data,double now,bool stale=false);
void ForgetPrivateHomeWeather();
}
