#pragma once
#include "include/cef_command_line.h"
#include "examples/sona/extension_service.h"
namespace sona {
// Private, non-inheritable anonymous handles. No listening network endpoint.
void ConfigureExtensionPipe(CefRefPtr<CefCommandLine> command_line);
void StartExtensionPipe();
void StopExtensionPipe();
void TriggerExtensionAction(const std::string& id,const std::string& target,ExtensionReply reply);
}
