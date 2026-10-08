#include "examples/soulu/browser_import.h"
#include "examples/soulu/history_store.h"
#include "examples/soulu/third_party/sqlite3.h"
#include "include/cef_parser.h"
#include <windows.h>
#include <algorithm>
#include <cmath>
#include <cctype>
#include <cwctype>
#include <fstream>
#include <functional>
#include <map>
#include <set>
#include <stdexcept>
#include <tuple>

namespace soulu {
namespace {
struct BrowserSpec { const char *id,*exe,*family; const wchar_t *directory,*application; bool roaming, single; };
const BrowserSpec specs[]={
  {"Chrome","chrome.exe","chromium",L"Google/Chrome/User Data",L"Google/Chrome/Application/chrome.exe",false,false},
  {"Edge","msedge.exe","chromium",L"Microsoft/Edge/User Data",L"Microsoft/Edge/Application/msedge.exe",false,false},
  {"Brave","brave.exe","chromium",L"BraveSoftware/Brave-Browser/User Data",L"BraveSoftware/Brave-Browser/Application/brave.exe",false,false},
  {"Opera","opera.exe","chromium",L"Opera Software/Opera Stable",L"Programs/Opera/opera.exe",true,true},
  {"Opera GX","opera.exe","chromium",L"Opera Software/Opera GX Stable",L"Programs/Opera GX/opera.exe",true,true},
  {"Vivaldi","vivaldi.exe","chromium",L"Vivaldi/User Data",L"Vivaldi/Application/vivaldi.exe",false,false},
  {"Yandex","browser.exe","chromium",L"Yandex/YandexBrowser/User Data",L"Yandex/YandexBrowser/Application/browser.exe",false,false},
  {"Chromium","chrome.exe","chromium",L"Chromium/User Data",L"Chromium/Application/chrome.exe",false,false},
  {"Firefox","firefox.exe","firefox",L"Mozilla/Firefox",L"Mozilla Firefox/firefox.exe",true,false}
};
std::filesystem::path Env(const wchar_t* key){wchar_t b[32768]={};auto n=GetEnvironmentVariableW(key,b,32768);return n&&n<32768?std::filesystem::path(b):std::filesystem::path();}
bool File(const std::filesystem::path& p){std::error_code e;return LocalImportPath(p)&&std::filesystem::is_regular_file(p,e);}
bool Directory(const std::filesystem::path& p){std::error_code e;return LocalImportPath(p)&&std::filesystem::is_directory(p,e);}
bool Profile(const std::filesystem::path& p,const std::string& family){
  // Presence only: no credential, bookmark or history content during discovery.
  if(!Directory(p))return false;
  return family=="firefox"?(File(p/L"prefs.js")||File(p/L"places.sqlite")):
    (File(p/L"Preferences")||File(p/L"Bookmarks")||File(p/L"History"));
}
bool Installed(const BrowserSpec& s){
  for(auto env:{L"LOCALAPPDATA",L"ProgramW6432",L"PROGRAMFILES",L"PROGRAMFILES(X86)"}){
    auto root=Env(env);if(!root.empty()&&File(root/s.application))return true;
  }
  // Shared executable names (Opera/Chromium) cannot identify an installation.
  if(std::string(s.id)=="Chromium"||std::string(s.id)=="Opera"||std::string(s.id)=="Opera GX")return false;
  auto key=L"Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\"+CefString(s.exe).ToWString();
  for(auto hive:{HKEY_CURRENT_USER,HKEY_LOCAL_MACHINE}){wchar_t b[32768]={};DWORD bytes=sizeof(b);
    if(RegGetValueW(hive,key.c_str(),nullptr,RRF_RT_REG_SZ,nullptr,b,&bytes)==ERROR_SUCCESS&&File(b)){
      std::wstring path=b;std::transform(path.begin(),path.end(),path.begin(),[](wchar_t c){return std::towlower(c);});
      if(std::string(s.id)=="Chrome"&&path.find(L"google\\chrome\\")==std::wstring::npos)continue;
      if(std::string(s.id)=="Yandex"&&path.find(L"yandex\\")==std::wstring::npos)continue;
      return true;
    }
  }return false;
}
std::filesystem::path Root(const BrowserSpec& s){auto base=Env(s.roaming?L"APPDATA":L"LOCALAPPDATA");return base.empty()?base:base/s.directory;}
std::string ReadText(const std::filesystem::path& p,size_t limit){
  if(!File(p))throw std::runtime_error("Source is missing or inaccessible");
  std::ifstream f(p,std::ios::binary|std::ios::ate);auto size=f.tellg();
  if(!f||size<0||static_cast<size_t>(size)>limit)throw std::runtime_error("Source exceeds the supported size limit");
  std::string data(static_cast<size_t>(size),'\0');f.seekg(0);if(!f.read(data.data(),data.size()))throw std::runtime_error("Source read failed");
  if(data.rfind("\xef\xbb\xbf",0)==0)data.erase(0,3);
  if(data.find('\0')!=std::string::npos)throw std::runtime_error("Use a UTF-8 export");
  if(!data.empty()&&!MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,data.data(),static_cast<int>(data.size()),nullptr,0))throw std::runtime_error("Use a UTF-8 export");
  return data;
}
// Lock the database and WAL as a set before copying. Do not open source SQLite:
// even a read-only connection can create a SHM file in a live source directory.
class DatabaseSnapshot {
 public:
  explicit DatabaseSnapshot(const std::filesystem::path& source){
    auto temp=Env(L"TEMP");if(!Directory(temp))throw std::runtime_error("Local temporary storage unavailable");
    root_=temp/std::filesystem::u8path("soulu-import-"+RandomId());
    try{
      std::filesystem::create_directory(root_);
      for(auto suffix:{L"",L"-wal"}){
        auto path=std::filesystem::path(source.wstring()+suffix);
        std::error_code error;bool exists=std::filesystem::exists(path,error);
        if(error)throw std::runtime_error("Source is inaccessible");
        if(!exists){if(!*suffix)throw std::runtime_error("Source database missing");continue;}
        if(!File(path))throw std::runtime_error("Unsupported source path");
        auto h=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
        if(h==INVALID_HANDLE_VALUE)throw std::runtime_error("Close the source browser and retry: database is locked or inaccessible");
        handles_.push_back(h);names_.push_back(path.filename());
        wchar_t final[32768]={};auto n=GetFinalPathNameByHandleW(h,final,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
        std::wstring resolved(final);if(!n||n>=32768||resolved.rfind(L"\\\\?\\UNC\\",0)==0)throw std::runtime_error("Unsupported source path");
        if(resolved.rfind(L"\\\\?\\",0)==0)resolved.erase(0,4);
        if(!LocalImportPath(resolved))throw std::runtime_error("Unsupported source path");
      }
      for(size_t i=0;i<handles_.size();++i){LARGE_INTEGER size={};
        if(!GetFileSizeEx(handles_[i],&size)||size.QuadPart>256LL*1024*1024)throw std::runtime_error("Database exceeds 256 MB");
        std::ofstream out(root_/names_[i],std::ios::binary);char b[65536];DWORD n;
        while(true){if(!ReadFile(handles_[i],b,sizeof(b),&n,nullptr))throw std::runtime_error("Source read failed");if(!n)break;out.write(b,n);}
        out.flush();if(!out||out.tellp()!=size.QuadPart)throw std::runtime_error("Snapshot write failed");
      }
      auto filename=CefString((root_/source.filename()).wstring()).ToString();
      // Only the private snapshot may create WAL/SHM or recover an existing WAL.
      if(sqlite3_open_v2(filename.c_str(),&db_,SQLITE_OPEN_READWRITE,nullptr)!=SQLITE_OK)throw std::runtime_error("Corrupt or unsupported source database");
      sqlite3_db_config(db_,SQLITE_DBCONFIG_DEFENSIVE,1,nullptr);sqlite3_db_config(db_,SQLITE_DBCONFIG_TRUSTED_SCHEMA,0,nullptr);
      sqlite3_limit(db_,SQLITE_LIMIT_LENGTH,1024*1024);sqlite3_exec(db_,"PRAGMA query_only=ON",nullptr,nullptr,nullptr);
    }catch(...){Clear();throw;}
  }
  ~DatabaseSnapshot(){Clear();}
  sqlite3* db()const{return db_;}
 private:
  void Clear(){sqlite3_close(db_);db_=nullptr;for(auto h:handles_)CloseHandle(h);handles_.clear();std::error_code e;if(!root_.empty())std::filesystem::remove_all(root_,e);}
  sqlite3* db_=nullptr;std::filesystem::path root_;std::vector<HANDLE> handles_;std::vector<std::filesystem::path> names_;
};
class Query {
 public:
  Query(sqlite3* db,const char* sql){if(sqlite3_prepare_v2(db,sql,-1,&s_,nullptr)!=SQLITE_OK)throw std::runtime_error("Unsupported source database schema");}
  ~Query(){sqlite3_finalize(s_);}
  bool Next(){int code=sqlite3_step(s_);if(code==SQLITE_ROW)return true;if(code!=SQLITE_DONE)throw std::runtime_error("Source database read failed");return false;}
  std::string Text(int c){auto p=sqlite3_column_text(s_,c);return p?reinterpret_cast<const char*>(p):"";}
  int Int(int c){return sqlite3_column_int(s_,c);}
  sqlite3_int64 Int64(int c){return sqlite3_column_int64(s_,c);}
  double Number(int c){return sqlite3_column_double(s_,c);}
 private:sqlite3_stmt* s_=nullptr;
};
CefRefPtr<CefDictionaryValue> Report(){auto r=CefDictionaryValue::Create();r->SetInt("imported",0);r->SetInt("skipped",0);r->SetInt("failed",0);r->SetString("status","ok");return r;}
void Increment(CefRefPtr<CefDictionaryValue> r,const char* key){r->SetInt(key,r->GetInt(key)+1);}
CefRefPtr<CefDictionaryValue> Node(const std::string& type,const std::string& title,const std::string& url=""){
  auto n=CefDictionaryValue::Create();n->SetString("type",type);n->SetString("name",title);if(type=="folder")n->SetList("children",CefListValue::Create());else n->SetString("url",url);return n;
}
}

std::vector<ImportSource> BrowserImportSources(){
  std::vector<ImportSource> out;
  for(const auto& s:specs){auto root=Root(s);if(root.empty()||!Directory(root))continue;
    if(std::string(s.family)=="firefox"){
      if(!File(root/L"profiles.ini"))continue;
      std::ifstream f(root/L"profiles.ini");std::string line,section;std::map<std::string,std::string> values;
      auto append=[&](){if(section.rfind("Profile",0)!=0||!values.count("Path"))return;
        auto path=std::filesystem::u8path(values["Path"]);if(values["IsRelative"]!="0")path=root/path;
        if(Profile(path,"firefox"))out.push_back({std::string(s.id)+":"+section,s.id,values.count("Name")?values["Name"]:section,"firefox",path});};
      while(std::getline(f,line)){if(!line.empty()&&line.back()=='\r')line.pop_back();if(line.size()>1&&line.front()=='['&&line.back()==']'){append();values.clear();section=line.substr(1,line.size()-2);}else{auto eq=line.find('=');if(eq!=std::string::npos)values[line.substr(0,eq)]=line.substr(eq+1);}}append();continue;
    }
    if(s.single&&Profile(root,"chromium"))out.push_back({std::string(s.id)+":Root",s.id,"Default","chromium",root});
    // Local State profile names are discovery metadata, not imported data.
    CefRefPtr<CefDictionaryValue> cache;
    if(File(root/L"Local State")){try{auto state=CefParseJSON(ReadText(root/L"Local State",8*1024*1024),JSON_PARSER_RFC);
      if(state&&state->GetType()==VTYPE_DICTIONARY){auto p=state->GetDictionary()->GetDictionary("profile");if(p){auto names=p->GetDictionary("info_cache");if(names)cache=names->Copy(false);}}}catch(...) {}}
    std::error_code e;size_t count=0;
    for(std::filesystem::directory_iterator it(root,e),end;!e&&it!=end&&count++<512;it.increment(e)){
      auto filename=CefString(it->path().filename().wstring()).ToString();
      if(filename!="Default"&&filename.rfind("Profile ",0)!=0)continue;
      if(!Profile(it->path(),"chromium"))continue;std::string name=filename;
      if(cache){auto p=cache->GetDictionary(filename);if(p&&!p->GetString("name").empty())name=p->GetString("name");}
      out.push_back({std::string(s.id)+":"+filename,s.id,name,"chromium",it->path()});
    }
  }return out;
}
std::string ReadImportFile(const std::filesystem::path& path){return ReadText(path,20*1024*1024);}
CefRefPtr<CefListValue> BrowserImportCatalog(){auto sources=BrowserImportSources();auto rows=CefListValue::Create();
  for(const auto& s:specs){auto profiles=CefListValue::Create();for(const auto& p:sources)if(p.browser==s.id){auto row=CefDictionaryValue::Create();row->SetString("id",p.id);row->SetString("name",p.name);row->SetString("family",p.family);profiles->SetDictionary(profiles->GetSize(),row);}
    bool installed=Installed(s);if(!installed&&!profiles->GetSize())continue;
    auto row=CefDictionaryValue::Create();row->SetString("browser",s.id);row->SetBool("installed",installed);row->SetList("profiles",profiles);rows->SetDictionary(rows->GetSize(),row);
  }return rows;
}
ImportSource PortableImportSource(const std::filesystem::path& root){
  std::string family=File(root/L"places.sqlite")?"firefox":File(root/L"Bookmarks")||File(root/L"Preferences")||File(root/L"History")?"chromium":"";
  if(family.empty()||!Profile(root,family))throw std::runtime_error("Select a Chromium or Firefox profile directory");
  return {"portable:"+RandomId(),"Portable",CefString(root.filename().wstring()).ToString(),family,root};
}

namespace {
std::string ReadBinary(const std::filesystem::path& path) {
  if(!File(path))throw std::runtime_error("Session data not found");
  HANDLE h=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
  if(h==INVALID_HANDLE_VALUE)throw std::runtime_error("Close the source browser and retry: session file is locked");
  struct Close{HANDLE h;~Close(){CloseHandle(h);}} close{h};
  wchar_t final[32768]={};auto n=GetFinalPathNameByHandleW(h,final,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);std::wstring resolved(final);
  if(!n||n>=32768||resolved.rfind(L"\\\\?\\UNC\\",0)==0)throw std::runtime_error("Unsupported session path");
  if(resolved.rfind(L"\\\\?\\",0)==0)resolved.erase(0,4);if(!LocalImportPath(resolved))throw std::runtime_error("Unsupported session path");
  LARGE_INTEGER size{};
  if(!GetFileSizeEx(h,&size)||size.QuadPart<0||size.QuadPart>32*1024*1024)throw std::runtime_error("Session exceeds 32 MB");
  std::string bytes(static_cast<size_t>(size.QuadPart),'\0');DWORD read=0;
  if(!ReadFile(h,bytes.data(),static_cast<DWORD>(bytes.size()),&read,nullptr)||read!=bytes.size())throw std::runtime_error("Session read failed");return bytes;
}
uint32_t U32(const std::string& b,size_t at){if(at>b.size()||b.size()-at<4)throw std::runtime_error("Invalid session record");return static_cast<unsigned char>(b[at])|(static_cast<uint32_t>(static_cast<unsigned char>(b[at+1]))<<8)|(static_cast<uint32_t>(static_cast<unsigned char>(b[at+2]))<<16)|(static_cast<uint32_t>(static_cast<unsigned char>(b[at+3]))<<24);}
std::string MozillaLz4(const std::string& b){
  if(b.size()<12||b.compare(0,8,std::string("mozLz40\0",8)))throw std::runtime_error("Unsupported Firefox session format");
  size_t expected=U32(b,8),at=12;if(expected>32*1024*1024)throw std::runtime_error("Session expands beyond 32 MB");
  std::string out;out.reserve(expected);
  auto length=[&](size_t n){if(n==15){unsigned x;do{if(at>=b.size())throw std::runtime_error("Truncated LZ4 session");x=static_cast<unsigned char>(b[at++]);n+=x;if(n>expected)throw std::runtime_error("Invalid LZ4 length");}while(x==255);}return n;};
  while(at<b.size()){unsigned token=static_cast<unsigned char>(b[at++]);size_t literals=length(token>>4);
    if(literals>b.size()-at||literals>expected-out.size())throw std::runtime_error("Invalid LZ4 literals");out.append(b,at,literals);at+=literals;if(at==b.size())break;
    if(b.size()-at<2)throw std::runtime_error("Truncated LZ4 offset");size_t offset=static_cast<unsigned char>(b[at])|(static_cast<unsigned char>(b[at+1])<<8);at+=2;
    size_t count=length(token&15)+4;if(!offset||offset>out.size()||count>expected-out.size())throw std::runtime_error("Invalid LZ4 match");
    while(count--)out.push_back(out[out.size()-offset]);
  }if(out.size()!=expected)throw std::runtime_error("Truncated LZ4 output");return out;
}
std::filesystem::path SessionPath(const ImportSource& s){
  if(s.family=="firefox"){for(auto rel:{L"sessionstore.jsonlz4",L"sessionstore-backups/recovery.jsonlz4",L"sessionstore-backups/recovery.baklz4",L"sessionstore-backups/previous.jsonlz4"})if(File(s.root/rel))return s.root/rel;}
  else{auto directory=s.root/L"Sessions";std::filesystem::path latest;std::error_code e;size_t n=0;
    if(Directory(directory))for(std::filesystem::directory_iterator it(directory,e),end;!e&&it!=end&&n++<512;it.increment(e)){
      auto name=it->path().filename().wstring();if(name.rfind(L"Session_",0)==0&&File(it->path())&&(latest.empty()||name>latest.filename().wstring()))latest=it->path();}
    if(!latest.empty())return latest;for(auto rel:{L"Current Session",L"Last Session"})if(File(s.root/rel))return s.root/rel;
  }throw std::runtime_error("Session data not found");
}
}
CefRefPtr<CefListValue> ReadImportTabs(const ImportSource& source,const std::shared_ptr<ImportControl>& control,CefRefPtr<CefDictionaryValue> report){
  auto rows=CefListValue::Create();auto bytes=ReadBinary(SessionPath(source));std::set<std::string> seen;
  auto append=[&](const std::string& url){
    CefURLParts parts;bool safe=CefParseURL(url,parts)&&CefString(&parts.username).empty()&&CefString(&parts.password).empty();
    if(safe&&url.size()<=65536&&!WebOrigin(url).empty()&&seen.insert(url).second){if(rows->GetSize()>=500)throw std::runtime_error("Session exceeds 500 tabs");rows->SetString(rows->GetSize(),url);}else if(report)Increment(report,"skipped");};
  if(source.family=="firefox"){
    auto plain=MozillaLz4(bytes);auto json=CefParseJSON(plain,JSON_PARSER_RFC);SecureZeroMemory(plain.data(),plain.size());
    auto object=json&&json->GetType()==VTYPE_DICTIONARY?json->GetDictionary():nullptr;
    auto windows=object?object->GetList("windows"):nullptr;if(!windows||windows->GetSize()>100)throw std::runtime_error("Invalid Firefox session");
    for(size_t w=0;w<windows->GetSize();++w){auto window=windows->GetDictionary(w);if(!window||window->GetBool("isPrivate"))continue;auto tabs=window->GetList("tabs");if(!tabs)continue;
      for(size_t t=0;t<tabs->GetSize();++t){if(control->cancelled)return rows;++control->processed;auto tab=tabs->GetDictionary(t);if(!tab||tab->GetBool("isPrivate"))continue;
        auto entries=tab->GetList("entries");int index=tab->GetInt("index")-1;if(!entries||index<0||static_cast<size_t>(index)>=entries->GetSize())continue;
        auto entry=entries->GetDictionary(index);if(entry)append(entry->GetString("url"));}}
  }else{
    if(bytes.size()<8||bytes.compare(0,4,"SNSS"))throw std::runtime_error("Invalid Chromium session");auto version=U32(bytes,4);
    if(version!=1&&version!=3)throw std::runtime_error("Encrypted or unsupported session: export the open tabs as bookmarks and import their HTML file");
    struct Tab{int window=0,index=0,selected=-1;std::map<int,std::string> urls;};std::map<int,Tab> tabs;std::map<int,int> windows;std::set<int> closed;bool marker=version==1;
    for(size_t at=8;at<bytes.size();){if(control->cancelled)return rows;++control->processed;
      if(bytes.size()-at<3)throw std::runtime_error("Truncated session command");size_t count=static_cast<unsigned char>(bytes[at])|(static_cast<unsigned char>(bytes[at+1])<<8);at+=2;
      if(!count||count>bytes.size()-at)throw std::runtime_error("Invalid session command length");unsigned id=static_cast<unsigned char>(bytes[at]);std::string p=bytes.substr(at+1,count-1);at+=count;
      if(id==255){marker=true;continue;}if(tabs.size()>10000)throw std::runtime_error("Oversized session");
      if(id==0||id==2||id==7||id==9){int key=static_cast<int>(U32(p,0)),value=static_cast<int>(U32(p,4));if(id==0)tabs[value].window=key;else if(id==2)tabs[key].index=value;else if(id==7)tabs[key].selected=value;else windows[key]=value;}
      else if(id==16)tabs.erase(static_cast<int>(U32(p,0)));else if(id==17)closed.insert(static_cast<int>(U32(p,0)));
      else if(id==6){if(p.size()<16||U32(p,0)!=p.size()-4)throw std::runtime_error("Invalid navigation pickle");int key=static_cast<int>(U32(p,4)),index=static_cast<int>(U32(p,8));size_t length=U32(p,12);
        if(length>p.size()-16||length>65536)throw std::runtime_error("Invalid navigation URL");tabs[key].urls[index]=p.substr(16,length);}
      else if(id==5){int key=static_cast<int>(U32(p,0)),start=static_cast<int>(U32(p,4));auto& urls=tabs[key].urls;urls.erase(urls.lower_bound(start),urls.end());}
      else if(id==11||id==24){ // Do not guess selected URLs after index-changing prune operations.
        tabs.erase(static_cast<int>(U32(p,0)));
      }
    }
    if(!marker)throw std::runtime_error("Incomplete session snapshot");std::vector<std::pair<int,Tab>> sorted(tabs.begin(),tabs.end());
    std::sort(sorted.begin(),sorted.end(),[](const auto& a,const auto& b){return std::tie(a.second.window,a.second.index)<std::tie(b.second.window,b.second.index);});
    for(const auto& item:sorted){const auto& tab=item.second;if(closed.count(tab.window)||!windows.count(tab.window)||windows[tab.window]!=0)continue;auto found=tab.urls.find(tab.selected);if(found!=tab.urls.end())append(found->second);}
  }SecureZeroMemory(bytes.data(),bytes.size());return rows;
}
namespace {
bool HasTable(sqlite3* db,const char* name){std::string sql="SELECT count(*) FROM sqlite_master WHERE type='table' AND name='"+std::string(name)+"'";Query q(db,sql.c_str());return q.Next()&&q.Int(0)>0;}
bool PaymentLikeValue(const std::string& value){
  std::string digits;for(unsigned char c:value){if(c>='0'&&c<='9')digits+=static_cast<char>(c);else if(c!=' '&&c!='-')return false;}
  if(digits.size()<13||digits.size()>19)return false;int total=0;bool twice=false;
  for(auto it=digits.rbegin();it!=digits.rend();++it){int n=*it-'0';if(twice){n*=2;if(n>9)n-=9;}total+=n;twice=!twice;}return total%10==0;
}
CefRefPtr<CefListValue> AutofillSource(const ImportSource& source,const std::shared_ptr<ImportControl>& control){
  auto rows=CefListValue::Create();std::set<std::pair<std::string,std::string>> seen;size_t scanned=0;
  auto append=[&](const std::string& name,const std::string& value){if(++scanned>50000)throw std::runtime_error("Autofill source exceeds 50000 records");
    if(ValidAutofillField(name)&&!value.empty()&&value.size()<=4096&&!PaymentLikeValue(value)&&seen.emplace(name,value).second){if(rows->GetSize()>=20000)throw std::runtime_error("Autofill exceeds 20000 values");auto r=CefDictionaryValue::Create();r->SetString("name",name);r->SetString("value",value);rows->SetDictionary(rows->GetSize(),r);}};
  auto path=source.root/(source.family=="firefox"?L"formhistory.sqlite":L"Web Data");
  if(File(path)){DatabaseSnapshot db(path);const char* table=source.family=="firefox"?"moz_formhistory":"autofill";
    if(HasTable(db.db(),table)){Query q(db.db(),source.family=="firefox"?"SELECT fieldname,value FROM moz_formhistory":"SELECT name,value FROM autofill");while(q.Next()){if(control->cancelled)return rows;++control->processed;append(q.Text(0),q.Text(1));}}
    if(source.family=="chromium"){
      const std::map<int,std::string> types={{3,"given-name"},{4,"additional-name"},{5,"family-name"},{7,"name"},{9,"email"},{14,"tel"},{30,"address-line1"},{31,"address-line2"},{33,"address-level2"},{34,"address-level1"},{35,"postal-code"},{36,"country"},{60,"organization"},{77,"street-address"}};
      for(auto token_table:{"address_type_tokens","local_addresses_type_tokens","contact_info_type_tokens"})if(HasTable(db.db(),token_table)){
        std::string sql="SELECT type,value FROM "+std::string(token_table);Query q(db.db(),sql.c_str());while(q.Next()){if(control->cancelled)return rows;++control->processed;auto found=types.find(q.Int(0));if(found!=types.end())append("autocomplete:"+found->second,q.Text(1));}}
      const std::vector<std::tuple<const char*,const char*,const char*>> legacy={
        {"autofill_profile_names","first_name","given-name"},{"autofill_profile_names","middle_name","additional-name"},{"autofill_profile_names","last_name","family-name"},{"autofill_profile_names","full_name","name"},
        {"autofill_profile_emails","email","email"},{"autofill_profile_phones","number","tel"},
        {"autofill_profiles","company_name","organization"},{"autofill_profiles","street_address","street-address"},{"autofill_profiles","city","address-level2"},{"autofill_profiles","state","address-level1"},{"autofill_profiles","zipcode","postal-code"},{"autofill_profiles","country_code","country"}};
      for(const auto& spec:legacy)if(HasTable(db.db(),std::get<0>(spec))){std::string sql="SELECT "+std::string(std::get<1>(spec))+" FROM "+std::get<0>(spec);Query q(db.db(),sql.c_str());while(q.Next()){if(control->cancelled)return rows;++control->processed;append("autocomplete:"+std::string(std::get<2>(spec)),q.Text(0));}}
    }
  }
  if(source.family=="firefox"&&File(source.root/L"autofill-profiles.json")){
    auto json=CefParseJSON(ReadText(source.root/L"autofill-profiles.json",20*1024*1024),JSON_PARSER_RFC);auto object=json&&json->GetType()==VTYPE_DICTIONARY?json->GetDictionary():nullptr;auto addresses=object?object->GetList("addresses"):nullptr;
    if(!addresses)throw std::runtime_error("Unsupported Firefox address store");
    for(size_t i=0;i<addresses->GetSize();++i){if(control->cancelled)return rows;++control->processed;auto r=addresses->GetDictionary(i);if(!r)continue;
      for(auto key:{"given-name","additional-name","family-name","name","email","tel","street-address","address-level1","address-level2","postal-code","country","organization"})if(r->GetType(key)==VTYPE_STRING)append("autocomplete:"+std::string(key),r->GetString(key));
    }
  }return rows;
}
}
CefRefPtr<CefDictionaryValue> ImportBrowserAutofill(const ImportSource& source,const std::string& target,const std::shared_ptr<ImportControl>& control){
  auto report=Report();try{
    auto incoming=AutofillSource(source,control),rows=ReadAutofill(target);std::set<std::pair<std::string,std::string>> seen;
    for(size_t i=0;i<rows->GetSize();++i){auto r=rows->GetDictionary(i);if(r)seen.emplace(r->GetString("name"),r->GetString("value"));}
    for(size_t i=0;i<incoming->GetSize();++i){if(control->cancelled)break;auto r=incoming->GetDictionary(i);std::string name=r->GetString("name"),value=r->GetString("value");
      if(!seen.emplace(name,value).second){Increment(report,"skipped");continue;}if(rows->GetSize()>=20000)throw std::runtime_error("Autofill exceeds 20000 values");rows->SetDictionary(rows->GetSize(),r->Copy(false));Increment(report,"imported");
    }
    if(control->cancelled){report->SetInt("imported",0);report->SetString("status","cancelled");}
    else if(!SaveAutofill(target,rows))throw std::runtime_error("Autofill write failed");
  }catch(const std::exception& e){report->SetInt("imported",0);report->SetInt("failed",1);report->SetString("status","error");report->SetString("message",e.what());}return report;
}
namespace {
std::string ImportHeader(const std::filesystem::path& path,size_t count){
  if(!File(path))throw std::runtime_error("Source data not found");
  HANDLE h=CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
  if(h==INVALID_HANDLE_VALUE)throw std::runtime_error("Close the source browser and retry: source file is locked or inaccessible");
  struct Close{HANDLE h;~Close(){CloseHandle(h);}} close{h};
  wchar_t final[32768]={};auto n=GetFinalPathNameByHandleW(h,final,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);std::wstring resolved(final);
  if(!n||n>=32768||resolved.rfind(L"\\\\?\\UNC\\",0)==0)throw std::runtime_error("Unsupported source path");
  if(resolved.rfind(L"\\\\?\\",0)==0)resolved.erase(0,4);if(!LocalImportPath(resolved))throw std::runtime_error("Unsupported source path");
  std::string bytes(count,'\0');DWORD read=0;if(!ReadFile(h,bytes.data(),static_cast<DWORD>(count),&read,nullptr))throw std::runtime_error("Source header read failed");bytes.resize(read);return bytes;
}
}
CefRefPtr<CefDictionaryValue> BrowserImportCapabilities(const ImportSource& source){
  // No bookmark URLs, form values, login records or session bodies before Import.
  // Probe only filenames, size, locks and known container signatures. Exact entry
  // counts and schema/record validation belong to the explicitly started reader.
  auto caps=CefDictionaryValue::Create();
  auto add=[&](const char* key,const char* status,const std::string& reason){auto r=CefDictionaryValue::Create();r->SetString("status",status);r->SetString("reason",reason);caps->SetDictionary(key,r);};
  auto probe=[&](const char* key,const std::filesystem::path& path,bool sqlite){
    if(!File(path)){std::error_code error;bool exists=std::filesystem::exists(path,error);add(key,!error&&!exists?"not_found":"blocked",!error&&!exists?"Source data not found":"Source path inaccessible");return;}
    try{auto header=ImportHeader(path,16);if(header.empty()){add(key,"not_found","Source store is empty");return;}
      if(sqlite&&header!=std::string("SQLite format 3\0",16))throw std::runtime_error("Unsupported database format");
      add(key,"available","Supported source container; entries are validated when Import starts");
    }catch(const std::exception& e){add(key,"blocked",e.what());}
  };
  probe("bookmarks",source.root/(source.family=="firefox"?L"places.sqlite":L"Bookmarks"),source.family=="firefox");
  probe("history",source.root/(source.family=="firefox"?L"places.sqlite":L"History"),true);
  probe("passwords",source.root/(source.family=="firefox"?L"logins.json":L"Login Data"),source.family!="firefox");
  if(source.family=="firefox"&&File(source.root/L"autofill-profiles.json"))probe("autofill",source.root/L"autofill-profiles.json",false);
  else probe("autofill",source.root/(source.family=="firefox"?L"formhistory.sqlite":L"Web Data"),true);
  try{auto header=ImportHeader(SessionPath(source),12);
    if(source.family=="firefox"){if(header.size()<12||header.compare(0,8,std::string("mozLz40\0",8)))throw std::runtime_error("Unsupported Firefox session format");}
    else{if(header.size()<8||header.compare(0,4,"SNSS"))throw std::runtime_error("Invalid Chromium session");auto version=U32(header,4);if(version!=1&&version!=3)throw std::runtime_error("Encrypted or unsupported session: use Open tabs HTML export");}
    add("tabs","available","Only normal-tab URLs; source records are checked when Import starts");
  }catch(const std::exception& e){add("tabs",std::string(e.what())=="Session data not found"?"not_found":"blocked",e.what());}
  add("favicons","unsupported","Separate favicon database conversion unavailable; safe HTML icons can be imported");
  add("preferences","unsupported","Foreign settings have no verified mapping");
  add("other","unsupported","Downloads and extension transfer have no verified binding");return caps;
}
CefRefPtr<CefListValue> ReadImportBookmarks(const ImportSource& source,const std::shared_ptr<ImportControl>& control){
  auto nodes=CefListValue::Create();size_t total=0;
  if(source.family=="chromium"){
    auto json=CefParseJSON(ReadText(source.root/L"Bookmarks",20*1024*1024),JSON_PARSER_RFC);
    auto roots=json&&json->GetType()==VTYPE_DICTIONARY?json->GetDictionary()->GetDictionary("roots"):nullptr;
    if(!roots)throw std::runtime_error("Invalid Chromium bookmarks file");
    std::function<CefRefPtr<CefDictionaryValue>(CefRefPtr<CefDictionaryValue>,int)> parse=[&](CefRefPtr<CefDictionaryValue> n,int depth)->CefRefPtr<CefDictionaryValue>{
      if(control->cancelled)return nullptr;if(!n||depth>64||++total>20000)throw std::runtime_error("Invalid or oversized bookmark hierarchy");
      std::string type=n->GetString("type"),name=n->GetString("name");if(name.size()>8192)throw std::runtime_error("Bookmark title too long");
      if(type=="url"){std::string url=n->GetString("url");if(url.size()>65536||WebOrigin(url).empty())return nullptr;return Node(type,name,url);}
      if(type!="folder"||n->GetType("children")!=VTYPE_LIST)throw std::runtime_error("Invalid bookmark node");
      auto result=Node(type,name);auto list=n->GetList("children"),children=result->GetList("children");
      for(size_t i=0;i<list->GetSize();++i){auto child=parse(list->GetDictionary(i),depth+1);if(child)children->SetDictionary(children->GetSize(),child);}return result;
    };
    CefDictionaryValue::KeyList keys;roots->GetKeys(keys);
    for(const auto& key:keys){auto root=parse(roots->GetDictionary(key),0);if(root)nodes->SetDictionary(nodes->GetSize(),root);}
  }else if(source.family=="firefox"){
    DatabaseSnapshot db(source.root/L"places.sqlite");
    Query q(db.db(),"SELECT b.id,b.parent,b.type,b.title,p.url,b.guid FROM moz_bookmarks b LEFT JOIN moz_places p ON b.fk=p.id ORDER BY b.parent,b.position");
    struct Entry{int id,parent,type;std::string title,url,guid;};std::vector<Entry> entries;std::map<int,std::vector<size_t>> children;int root=0;
    while(q.Next()){if(control->cancelled)return nodes;if(entries.size()>=20000)throw std::runtime_error("Too many bookmarks");Entry e={q.Int(0),q.Int(1),q.Int(2),q.Text(3),q.Text(4),q.Text(5)};if(e.guid=="root________")root=e.id;children[e.parent].push_back(entries.size());entries.push_back(e);}
    if(!root)throw std::runtime_error("Firefox bookmarks root missing");std::set<int> ancestors;
    std::function<void(int,CefRefPtr<CefListValue>,int)> walk=[&](int parent,CefRefPtr<CefListValue> dest,int depth){
      if(depth>64||!ancestors.insert(parent).second)throw std::runtime_error("Invalid Firefox bookmark hierarchy");
      for(auto index:children[parent]){if(control->cancelled)break;const auto& e=entries[index];if(e.guid=="tags________")continue;
        if(e.type==2){auto n=Node("folder",e.title.empty()?(e.guid=="toolbar_____"?"Bookmarks toolbar":e.guid=="menu________"?"Bookmarks menu":"Other bookmarks"):e.title);walk(e.id,n->GetList("children"),depth+1);dest->SetDictionary(dest->GetSize(),n);}
        else if(e.type==1&&!WebOrigin(e.url).empty())dest->SetDictionary(dest->GetSize(),Node("url",e.title,e.url));
      }ancestors.erase(parent);
    };walk(root,nodes,0);
  }else throw std::runtime_error("Unsupported source adapter");
  return nodes;
}
CefRefPtr<CefListValue> MergeImportBookmarks(CefRefPtr<CefListValue> existing,CefRefPtr<CefListValue> nodes,const std::string& target,CefRefPtr<CefDictionaryValue> report,const std::shared_ptr<ImportControl>& control){
  if(!ValidProfileId(target)||!nodes)throw std::runtime_error("Invalid target or bookmarks");
  auto merged=existing->Copy();int id=1;size_t target_count=0,seen=0;
  using Key=std::tuple<int,std::string,std::string,std::string>;
  std::map<Key,CefRefPtr<CefDictionaryValue>> index;std::map<int,int> orders;
  for(size_t i=0;i<merged->GetSize();++i){auto row=merged->GetDictionary(i);if(row){if(row->GetInt("id")>=2147483646)throw std::runtime_error("Bookmark ID capacity reached");id=std::max(id,row->GetInt("id")+1);if(row->GetString("profileId")==target){++target_count;int parent=row->GetInt("parentId");std::string type=row->GetString("type");index[{parent,type,row->GetString("title"),type=="folder"?"":row->GetString("url").ToString()}]=row;orders[parent]=std::max(orders[parent],row->GetInt("order")+1);}}}
  std::function<void(CefRefPtr<CefListValue>,int,int)> walk=[&](CefRefPtr<CefListValue> list,int parent,int depth){
    if(depth>64)throw std::runtime_error("Bookmarks nesting exceeds 64");
    for(size_t i=0;i<list->GetSize();++i){if(control->cancelled)return;if(++seen>20000)throw std::runtime_error("Too many imported bookmarks");auto n=list->GetDictionary(i);
      if(!n)throw std::runtime_error("Invalid bookmark");std::string type=n->GetString("type"),title=n->GetString("name"),url=n->GetString("url");
      if(title.size()>8192||url.size()>65536||(type!="folder"&&type!="url"))throw std::runtime_error("Invalid bookmark fields");
      if(type=="folder"&&n->GetType("children")!=VTYPE_LIST)throw std::runtime_error("Folder children missing");
      if(type=="url"&&WebOrigin(url).empty()){Increment(report,"skipped");continue;}
      Key key={parent,type,title,type=="folder"?"":url};CefRefPtr<CefDictionaryValue> match;
      auto found=index.find(key);if(found!=index.end())match=found->second;int order=orders[parent];
      if(match)Increment(report,"skipped");else{
        if(++target_count>20000||id>=2147483647)throw std::runtime_error("Target bookmark capacity reached");
        match=CefDictionaryValue::Create();match->SetInt("id",id++);match->SetString("type",type);match->SetString("title",title);match->SetString("url",url);match->SetInt("parentId",parent);match->SetInt("order",order);match->SetString("profileId",target);match->SetDouble("createdAt",HistoryNow());
        std::string icon=n->GetString("favicon");if(icon.size()<=65536&&(icon.rfind("data:image/png;base64,",0)==0||icon.rfind("data:image/x-icon;base64,",0)==0))match->SetString("favicon",icon);
        merged->SetDictionary(merged->GetSize(),match->Copy(false));index[key]=match;orders[parent]=order+1;Increment(report,"imported");
      }if(type=="folder")walk(n->GetList("children"),match->GetInt("id"),depth+1);
    }
  };walk(nodes,0,0);return merged;
}
CefRefPtr<CefDictionaryValue> ImportBrowserHistory(const ImportSource& source,const std::string& target,const std::shared_ptr<ImportControl>& control){
  auto report=Report();try{if(!ValidProfileId(target))throw std::runtime_error("Invalid target profile");if(!LocalImportPath(DataRoot()))throw std::runtime_error("Target must use local storage without symbolic links");
    DatabaseSnapshot db(source.root/(source.family=="firefox"?L"places.sqlite":L"History"));HistoryStore store(target);if(!store.Healthy())throw std::runtime_error("Target history store unavailable");
    Query q(db.db(),source.family=="firefox"?"SELECT p.url,p.title,v.visit_date FROM moz_historyvisits v JOIN moz_places p ON p.id=v.place_id ORDER BY v.visit_date":"SELECT u.url,u.title,v.visit_time FROM visits v JOIN urls u ON u.id=v.url ORDER BY v.visit_time");
    int total=0;while(!control->cancelled&&q.Next()){
      if(++total>500000)throw std::runtime_error("History exceeds 500000 visits");
      auto url=q.Text(0),title=q.Text(1);auto raw=q.Int64(2);
      // Subtract the Chromium epoch in integer microseconds before converting
      // to double; converting the 1601-based value first loses visit precision.
      if(raw<0){Increment(report,"skipped");continue;}
      if(source.family!="firefox")raw-=11644473600000000LL;
      double time=static_cast<double>(raw)/1000.0;
      if(WebOrigin(url).empty()||url.size()>65536||title.size()>8192||!std::isfinite(time)||time<0||time>HistoryNow()+86400000){Increment(report,"skipped");continue;}
      int result=store.ImportVisit(url,title,time);Increment(report,result>0?"imported":result==0?"skipped":"failed");++control->processed;
      if(result<0)throw std::runtime_error("History write failed; earlier visits remain imported");
    }if(control->cancelled)report->SetString("status","cancelled");
  }catch(const std::exception& e){report->SetString("status",report->GetInt("imported")?"partial":"error");report->SetString("message",e.what());}
  return report;
}
CefRefPtr<CefDictionaryValue> ImportPasswordCsv(const std::filesystem::path& path,const std::string& target,const std::shared_ptr<ImportControl>& control){
  auto report=Report();std::string text,field;std::vector<std::vector<std::string>> rows;
  struct Wiper{std::string& text;std::string& field;std::vector<std::vector<std::string>>& rows;~Wiper(){if(!text.empty())SecureZeroMemory(text.data(),text.size());if(!field.empty())SecureZeroMemory(field.data(),field.size());for(auto& r:rows)for(auto& v:r)if(!v.empty())SecureZeroMemory(v.data(),v.size());}}wipe{text,field,rows};
  try{if(!ValidProfileId(target))throw std::runtime_error("Invalid target profile");if(!LocalImportPath(DataRoot()))throw std::runtime_error("Target must use local storage without symbolic links");text=ReadText(path,20*1024*1024);
    rows.emplace_back();bool quoted=false,closed=false,start=true;
    auto cell=[&](){rows.back().push_back(std::move(field));field.clear();closed=false;start=true;if(rows.back().size()>32)throw std::runtime_error("Too many CSV columns");};
    for(size_t i=0;i<text.size();++i){char c=text[i];if(quoted){if(c=='"'){if(i+1<text.size()&&text[i+1]=='"'){field+='"';++i;}else{quoted=false;closed=true;}}else field+=c;}
      else if(c==','||c=='\n'||c=='\r'){cell();if(c!=','){if(c=='\r'&&i+1<text.size()&&text[i+1]=='\n')++i;rows.emplace_back();if(rows.size()>20001)throw std::runtime_error("Too many CSV entries");}}
      else if(c=='"'&&start){quoted=true;start=false;}else{if(closed||c=='"')throw std::runtime_error("Invalid CSV quoting");field+=c;start=false;}
      if(field.size()>65536)throw std::runtime_error("CSV field too long");
    }if(quoted)throw std::runtime_error("Unclosed CSV quote");if(!field.empty()||closed||!rows.back().empty())cell();else rows.pop_back();
    if(rows.empty())throw std::runtime_error("Empty CSV");std::map<std::string,size_t> header;
    for(size_t i=0;i<rows[0].size();++i){auto name=rows[0][i];std::transform(name.begin(),name.end(),name.begin(),[](unsigned char c){return static_cast<char>(tolower(c));});if(!header.emplace(name,i).second)throw std::runtime_error("Duplicate CSV headers");}
    std::string urlKey=header.count("url")?"url":"origin";
    if(!header.count(urlKey)||!header.count("username")||!header.count("password"))throw std::runtime_error("CSV requires url, username and password columns");
    // Validate the entire export before writing a single credential.
    for(size_t i=1;i<rows.size();++i){auto& r=rows[i];if(r.size()!=rows[0].size()||WebOrigin(r[header[urlKey]]).empty()||r[header["password"]].empty())throw std::runtime_error("Invalid credential row; no passwords imported");}
    PasswordVault vault(target);for(size_t i=1;i<rows.size()&&!control->cancelled;++i){auto& r=rows[i];auto origin=WebOrigin(r[header[urlKey]]);auto& user=r[header["username"]];auto& secret=r[header["password"]];
      if(vault.Contains(origin,user))Increment(report,"skipped");else if(vault.Put(origin,user,secret,false))Increment(report,"imported");else{Increment(report,"failed");throw std::runtime_error("Password write failed; earlier entries remain imported");}++control->processed;
    }if(control->cancelled)report->SetString("status","cancelled");
  }catch(const std::exception& e){report->SetString("status",report->GetInt("imported")?"partial":"error");report->SetString("message",e.what());}return report;
}
}
