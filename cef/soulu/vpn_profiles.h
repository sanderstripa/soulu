#pragma once
#include "include/cef_parser.h"
#include <algorithm>
#include <cstdint>
#include <set>
#include <sstream>
#include <string>
namespace soulu {
inline std::string VpnProfileId(const std::string& link){uint64_t hash=14695981039346656037ULL;for(unsigned char c:link){hash^=c;hash*=1099511628211ULL;}std::ostringstream out;out<<"vpn-"<<std::hex<<hash;return out.str();}
inline CefRefPtr<CefDictionaryValue> VpnProfileById(CefRefPtr<CefDictionaryValue> settings,const std::string& id){auto rows=settings?settings->GetList("profiles"):nullptr;if(rows)for(size_t i=0;i<rows->GetSize();++i){auto row=rows->GetDictionary(i);if(row&&row->GetString("id")==id)return row;}return nullptr;}
inline bool NormalizeVpnProfiles(CefRefPtr<CefDictionaryValue> settings,std::string& error){
 if(!settings){error="VPN: отсутствует конфигурация.";return false;}
 auto rows=settings->GetList("profiles");
 if(!rows){rows=CefListValue::Create();const std::string link=settings->GetString("link");if(!link.empty()){auto row=CefDictionaryValue::Create();for(const char* key:{"link","protocol","address","region"})row->SetString(key,settings->GetString(key));std::string id=settings->GetString("lastProfileId");if(id.empty())id=VpnProfileId(link);row->SetString("id",id);row->SetString("name",settings->GetString("region"));rows->SetDictionary(0,row);settings->SetString("defaultProfileId",id);}settings->SetList("profiles",rows);rows=settings->GetList("profiles");}
 std::set<std::string> ids;size_t total=0;
 for(size_t i=0;i<rows->GetSize();++i){auto row=rows->GetDictionary(i);if(!row){error="VPN: некорректная запись подключения.";return false;}
  const std::string id=row->GetString("id"),link=row->GetString("link");total+=link.size()+row->GetString("name").size();
  if(id.empty()||id.size()>80||id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")!=std::string::npos||!ids.insert(id).second||link.empty()||link.size()>16384||total>8*1024*1024){error="VPN: некорректный идентификатор или размер списка ключей.";return false;}
  std::string protocol,address;
  if(link.rfind("vless://",0)==0){protocol="vless";CefURLParts parts;if(!CefParseURL("https://"+link.substr(8),parts)||CefString(&parts.host).empty()||CefString(&parts.username).empty()){error="VPN: в VLESS-ключе отсутствует сервер или идентификатор.";return false;}address=CefString(&parts.host);const std::string port=CefString(&parts.port);if(!port.empty())address+=":"+port;}
  else if(link.rfind("sudoku://",0)==0){protocol="sudoku";std::string encoded=link.substr(9);std::replace(encoded.begin(),encoded.end(),'-','+');std::replace(encoded.begin(),encoded.end(),'_','/');while(encoded.size()%4)encoded+='=';auto decoded=CefBase64Decode(encoded);if(!decoded||decoded->GetSize()>16384){error="VPN: неверный Sudoku-ключ.";return false;}std::string text(decoded->GetSize(),'\0');decoded->GetData(text.data(),text.size(),0);auto value=CefParseJSON(text,JSON_PARSER_RFC);auto data=value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():nullptr;if(!data||data->GetString("h").empty()||data->GetString("k").empty()||data->GetInt("p")<1||data->GetInt("p")>65535){error="VPN: в Sudoku-ключе отсутствует сервер, порт или ключ.";return false;}address=data->GetString("h");if(address.find(':')!=std::string::npos)address="["+address+"]";address+=":"+std::to_string(data->GetInt("p"));}
  else{error="VPN: поддерживаются VLESS и Sudoku.";return false;}
  if(row->GetString("name").size()>160){error="VPN: название подключения слишком длинное.";return false;}
  if(row->GetString("name").empty()||row->GetString("name")=="Не указан")row->SetString("name",address);row->SetString("protocol",protocol);row->SetString("address",address);
 }
 std::string selected=settings->GetString("defaultProfileId");if(selected.empty())selected=settings->GetString("lastProfileId");if(!rows->GetSize())selected="";else if(selected.empty())selected=rows->GetDictionary(0)->GetString("id");
 auto active=VpnProfileById(settings,selected);if(!selected.empty()&&!active){error="VPN: выберите существующее подключение по умолчанию.";return false;}
 settings->SetString("defaultProfileId",selected);settings->SetString("lastProfileId",selected);
 for(const char* key:{"link","protocol","address","region"})settings->SetString(key,active?active->GetString(key):CefString(key==std::string("protocol")?"vless":""));return true;
}
inline void MergeLegacyVpnSelection(CefRefPtr<CefDictionaryValue> next,CefRefPtr<CefDictionaryValue> previous){
 auto rows=next->GetList("profiles"),old=previous?previous->GetList("profiles"):nullptr;
 if(!rows||!old||!rows->IsEqual(old)||next->GetString("defaultProfileId")!=previous->GetString("defaultProfileId")||next->GetString("link")==previous->GetString("link")||next->GetString("link").empty())return;
 const std::string link=next->GetString("link");std::string id;
 for(size_t i=0;i<rows->GetSize();++i)if(rows->GetDictionary(i)->GetString("link")==link)id=rows->GetDictionary(i)->GetString("id");
 if(id.empty()){id=VpnProfileId(link);auto row=CefDictionaryValue::Create();row->SetString("id",id);row->SetString("name",next->GetString("region"));for(const char* key:{"link","protocol","address","region"})row->SetString(key,next->GetString(key));rows->SetDictionary(rows->GetSize(),row);}next->SetString("defaultProfileId",id);next->SetString("lastProfileId",id);
}
}
