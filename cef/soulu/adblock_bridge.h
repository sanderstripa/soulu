#pragma once
#include <string>
#include "include/cef_values.h"
namespace soulu {
bool InitializeAdBlock(const std::string& cache,const std::string& fixture="",bool updates=true);
bool MatchAdBlock(const std::string& url,const std::string& source,int type,
                  const std::string& method,std::string* rule=nullptr);
CefRefPtr<CefDictionaryValue> AdBlockStatus();
CefRefPtr<CefListValue> CosmeticSelectors(const std::string& url,const std::string& tokens);
}
