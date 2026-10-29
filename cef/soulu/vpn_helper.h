#pragma once
#include "include/cef_values.h"
#include "include/wrapper/cef_message_router.h"
namespace soulu {
CefRefPtr<CefDictionaryValue> VpnHelperRequest(CefRefPtr<CefDictionaryValue>);
void VpnComponentRequest(CefRefPtr<CefDictionaryValue>,CefRefPtr<CefMessageRouterBrowserSide::Callback>);
void ShutdownVpnHelper();
}
