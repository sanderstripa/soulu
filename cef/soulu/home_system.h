#pragma once
#include "include/cef_values.h"
#include <functional>
#include <string>
namespace soulu {
using HomeResult=std::function<void(CefRefPtr<CefDictionaryValue>)>;
void HomeRecognize(int browser_id,const std::string& language,HomeResult done);
void HomeCancelVoice(int browser_id);
void HomeLocate(HomeResult done);
}
