#pragma once
#include "include/cef_values.h"
#include <functional>
#include <string>
#include <vector>
namespace soulu {
using HomeResult=std::function<void(CefRefPtr<CefDictionaryValue>)>;
void HomeRecognize(int browser_id,const std::string& language,HomeResult done);
void HomeCancelVoice(int browser_id);
void HomeLocate(HomeResult done);
// Native fixture entry point; never exposed to web pages or the Home bridge.
std::string HomeTranscribeTest(const std::vector<float>& audio,const std::string& language);
}
