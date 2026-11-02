#pragma once
#include "include/cef_command_line.h"
#include "examples/soulu/extension_service.h"
namespace soulu {
// Private, non-inheritable anonymous handles. No listening network endpoint.
void ConfigureExtensionPipe(CefRefPtr<CefCommandLine> command_line);
void StartExtensionPipe();
void StopExtensionPipe();
void TriggerExtensionAction(const std::string& id,const std::string& target,ExtensionReply reply);
}
