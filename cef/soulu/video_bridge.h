#pragma once
#include "include/cef_values.h"
#include <string>
namespace soulu {
CefRefPtr<CefDictionaryValue> VideoPreferences(const std::string& profile);
bool SaveVideoPreferences(const std::string& profile,CefRefPtr<CefDictionaryValue>);
void ForgetPrivateVideoPreferences();
CefRefPtr<CefDictionaryValue> BundledVideoLocaleResponse(CefRefPtr<CefDictionaryValue> args);
}
