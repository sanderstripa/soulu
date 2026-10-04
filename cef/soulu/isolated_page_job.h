#pragma once
#include "include/cef_browser.h"
#include "include/cef_values.h"
#include <functional>
namespace soulu {
// Returns a dictionary by value from a named isolated world. Never grants
// universal access or installs a privileged function into the page world.
void EvaluateTranslationPage(CefRefPtr<CefBrowser> browser,const std::string& url,
    const std::string& expression,std::function<void(CefRefPtr<CefDictionaryValue>)> done);
}
