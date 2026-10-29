#pragma once
#include "include/cef_values.h"
#include <string>
namespace soulu {
CefRefPtr<CefDictionaryValue> ReadProtectedStore(const std::string& profile,const std::string& purpose);
bool WriteProtectedStore(const std::string& profile,const std::string& purpose,CefRefPtr<CefDictionaryValue> value);
}
