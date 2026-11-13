#pragma once
#include "include/cef_app.h"
namespace sona {
// CEF permits one enable/disable pair, including when native dialogs or menus
// nest inside another application-owned native message loop on the UI thread.
class NestableTasksScope final {
 public:
  NestableTasksScope(){if(depth_++==0)CefSetNestableTasksAllowed(true);}
  ~NestableTasksScope(){if(--depth_==0)CefSetNestableTasksAllowed(false);}
  NestableTasksScope(const NestableTasksScope&)=delete;
  NestableTasksScope& operator=(const NestableTasksScope&)=delete;
 private:inline static thread_local unsigned depth_=0;
};
}
