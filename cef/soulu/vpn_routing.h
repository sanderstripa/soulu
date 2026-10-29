#pragma once
#include "include/cef_parser.h"
#include <sstream>
#include <set>
#include <algorithm>
namespace soulu {
inline bool NormalizeVpnRouting(CefRefPtr<CefDictionaryValue> vpn,std::string& error){
 if(!vpn)return false;
 if(vpn->HasKey("directDomains")&&vpn->GetType("directDomains")!=VTYPE_STRING){error="VPN: неверный список сайтов.";return false;}
 const std::string raw=vpn->GetString("directDomains");
 if(raw.size()>65536){error="VPN: слишком длинный список маршрутизации.";return false;}
 std::istringstream input(raw);std::string line,normalized;std::set<std::string> seen;
 while(std::getline(input,line)){
  const auto begin=line.find_first_not_of(" \t\r");if(begin==std::string::npos)continue;
  line=line.substr(begin,line.find_last_not_of(" \t\r")-begin+1);
  if(line.rfind("*.",0)==0)line.erase(0,2);
  if(line.find("://")==std::string::npos)line="https://"+line;
  CefURLParts parts;if(!CefParseURL(line,parts)){error="VPN: неверный сайт в списке прямого подключения.";return false;}
  const std::string scheme=CefString(&parts.scheme),host=CefString(&parts.host);
  if((scheme!="https"&&scheme!="http")||!CefString(&parts.username).empty()||!CefString(&parts.password).empty()||host.empty()||host.size()>253||
     !std::all_of(host.begin(),host.end(),[](unsigned char c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='.'||c=='-';})){
   error="VPN: укажите домен или HTTP/HTTPS-адрес сайта.";return false;
  }
  if(seen.insert(host).second){if(seen.size()>500){error="VPN: максимум 500 сайтов.";return false;}if(!normalized.empty())normalized+='\n';normalized+=host;}
 }
 vpn->SetString("directDomains",normalized);return true;
}
inline std::string VpnBypassList(CefRefPtr<CefDictionaryValue> vpn){
 auto copy=vpn->Copy(false);std::string error;if(!NormalizeVpnRouting(copy,error))return "<-loopback>";
 std::istringstream input(copy->GetString("directDomains").ToString());std::string domain,result="<-loopback>";
 while(std::getline(input,domain))if(!domain.empty())result+=';'+domain+";*."+domain;
 return result;
}
}
