#include "examples/soulu/protected_store.h"
#include "examples/soulu/profile_data.h"
#include "include/cef_parser.h"
#include <windows.h>
#include <wincrypt.h>
namespace soulu {
namespace {
bool SafePurpose(const std::string& name){if(name.empty()||name.size()>30)return false;for(char c:name)if(c<'a'||c>'z')return false;return true;}
bool Protect(const std::string& input,const std::string& entropy,bool encrypt,std::string& output){
 DATA_BLOB in={static_cast<DWORD>(input.size()),reinterpret_cast<BYTE*>(const_cast<char*>(input.data()))};
 DATA_BLOB salt={static_cast<DWORD>(entropy.size()),reinterpret_cast<BYTE*>(const_cast<char*>(entropy.data()))},out={};
 const bool ok=encrypt?CryptProtectData(&in,L"Soulu private settings",&salt,nullptr,nullptr,CRYPTPROTECT_UI_FORBIDDEN,&out)!=0:
 CryptUnprotectData(&in,nullptr,&salt,nullptr,nullptr,CRYPTPROTECT_UI_FORBIDDEN,&out)!=0;
 if(ok)output.assign(reinterpret_cast<const char*>(out.pbData),out.cbData);
 if(out.pbData){SecureZeroMemory(out.pbData,out.cbData);LocalFree(out.pbData);}return ok;
}
}
CefRefPtr<CefDictionaryValue> ReadProtectedStore(const std::string& profile,const std::string& purpose){
 if(!ValidProfileId(profile)||!SafePurpose(purpose))return nullptr;
 const auto file=ProfileRoot(profile)/("soulu-private-"+purpose+".json");std::error_code error;
 if(!std::filesystem::exists(file,error)&&!error)return CefDictionaryValue::Create();
 auto root=ReadJson(file);if(!root||root->GetType()!=VTYPE_DICTIONARY)return nullptr;
 auto binary=CefBase64Decode(root->GetDictionary()->GetString("protected"));
 if(!binary||binary->GetSize()>8*1024*1024)return nullptr;
 std::string bytes(binary->GetSize(),'\0'),plain;binary->GetData(bytes.data(),bytes.size(),0);
 if(!Protect(bytes,profile+"|"+purpose,false,plain))return nullptr;
 auto value=CefParseJSON(plain,JSON_PARSER_RFC);if(!plain.empty())SecureZeroMemory(plain.data(),plain.size());
 return value&&value->GetType()==VTYPE_DICTIONARY?value->GetDictionary():nullptr;
}
bool WriteProtectedStore(const std::string& profile,const std::string& purpose,CefRefPtr<CefDictionaryValue> value){
 if(!ValidProfileId(profile)||!SafePurpose(purpose)||!value)return false;
 auto wrap=CefValue::Create();wrap->SetDictionary(value);std::string plain=CefWriteJSON(wrap,JSON_WRITER_DEFAULT),bytes;
 if(plain.size()>8*1024*1024)return false;bool ok=Protect(plain,profile+"|"+purpose,true,bytes);
 if(!plain.empty())SecureZeroMemory(plain.data(),plain.size());if(!ok)return false;
 auto row=CefDictionaryValue::Create();row->SetString("protected",CefBase64Encode(bytes.data(),bytes.size()));
 auto root=CefValue::Create();root->SetDictionary(row);return WriteJson(ProfileRoot(profile)/("soulu-private-"+purpose+".json"),root);
}
}
