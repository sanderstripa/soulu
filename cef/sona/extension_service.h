#pragma once
#include <windows.h>
#include <functional>
#include "include/cef_browser.h"
#include "include/cef_request_context.h"
namespace sona {
using ExtensionReply=std::function<void(CefRefPtr<CefDictionaryValue>,const std::string&)>;
class ExtensionService:public virtual CefBaseRefCounted {
 public:
  virtual void List(ExtensionReply)=0;
  virtual void Pin(const std::string&,bool,ExtensionReply)=0;
  virtual void Open(CefRefPtr<CefBrowser>,const std::string&,ExtensionReply)=0;
  virtual void Close(std::function<void()>)=0;
};
CefRefPtr<ExtensionService> CreateExtensionService(CefRefPtr<CefRequestContext>);
}
