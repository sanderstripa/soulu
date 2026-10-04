#include "examples/soulu/adblock_bridge.h"
#include "include/cef_parser.h"
#include "include/internal/cef_types.h"
extern "C" {
bool soulu_ab_init(const char*,const char*,bool);
char* soulu_ab_check(const char*,const char*,const char*,const char*);
char* soulu_ab_cosmetic(const char*,const char*);
char* soulu_ab_status();
void soulu_ab_free(char*);
}
namespace soulu {
namespace {
CefRefPtr<CefValue> Parse(char* text) {
  auto value=text?CefParseJSON(text,JSON_PARSER_RFC):nullptr;
  soulu_ab_free(text);return value;
}
const char* Kind(int type) {
  switch(type) {
    case RT_MAIN_FRAME:return "document";
    case RT_SUB_FRAME:return "subdocument";
    case RT_SCRIPT:case RT_WORKER:case RT_SHARED_WORKER:case RT_SERVICE_WORKER:return "script";
    case RT_IMAGE:case RT_FAVICON:return "image";
    case RT_STYLESHEET:return "stylesheet";
    case RT_FONT_RESOURCE:return "font";
    case RT_MEDIA:return "media";
    case RT_XHR:return "xmlhttprequest";
    case RT_PING:return "ping";
    default:return "other";
  }
}
}
bool InitializeAdBlock(const std::string& cache,const std::string& fixture,bool updates) {return soulu_ab_init(cache.c_str(),fixture.c_str(),updates);}
bool MatchAdBlock(const std::string& url,const std::string& source,int type,
                  const std::string& method,std::string* rule) {
  auto value=Parse(soulu_ab_check(url.c_str(),source.c_str(),Kind(type),method.c_str()));
  auto result=value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():nullptr;
  if(rule&&result)*rule=result->GetString("rule");
  return result&&result->GetBool("matched");
}
CefRefPtr<CefDictionaryValue> AdBlockStatus() {
  auto value=Parse(soulu_ab_status());
  return value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():CefDictionaryValue::Create();
}
CefRefPtr<CefListValue> CosmeticSelectors(const std::string& url,const std::string& tokens) {
  auto value=Parse(soulu_ab_cosmetic(url.c_str(),tokens.c_str()));
  return value&&value->GetType()==VTYPE_LIST?value->GetList():CefListValue::Create();
}
}
