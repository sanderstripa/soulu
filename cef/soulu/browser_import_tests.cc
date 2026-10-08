#include "examples/soulu/browser_import.h"
#include "examples/soulu/history_store.h"
#include "examples/soulu/third_party/sqlite3.h"
#include <windows.h>
#include <wincrypt.h>
#include <fstream>
#include <stdexcept>

namespace soulu {
// Invoked only with all AppData variables redirected to an explicit fixture root.
int RunBrowserImportTests(const std::filesystem::path& output){
  int checks=0;
  auto check=[&](bool ok,const char* name){++checks;if(!ok)throw std::runtime_error(name);};
  auto write=[](const std::filesystem::path& path,const std::string& text){std::filesystem::create_directories(path.parent_path());std::ofstream f(path,std::ios::binary);f<<text;if(!f)throw std::runtime_error("fixture-write");};
  auto database=[&](const std::filesystem::path& path,const char* sql){sqlite3* db=nullptr;check(sqlite3_open(CefString(path.wstring()).ToString().c_str(),&db)==SQLITE_OK,"fixture-open");int code=sqlite3_exec(db,sql,nullptr,nullptr,nullptr);sqlite3_close(db);check(code==SQLITE_OK,"fixture-schema");};
  try{
    auto fixture=DataRoot().parent_path().parent_path();
    check(std::filesystem::is_empty(fixture),"fixture-root-must-be-empty-never-use-real-appdata");
    auto chrome=fixture/L"Google/Chrome/User Data/Default";
    const std::string bookmarks=R"({"roots":{"bookmark_bar":{"type":"folder","name":"Toolbar","children":[{"type":"folder","name":"Work","children":[{"type":"url","name":"One","url":"https://example.test/"}]},{"type":"url","name":"Other structure","url":"https://example.test/"}]}}})";
    write(chrome/L"Bookmarks",bookmarks);write(fixture/L"Google/Chrome/User Data/Profile 1/Preferences","{}");
    write(fixture/L"Google/Chrome/User Data/Local State",R"({"profile":{"info_cache":{"Default":{"name":"Fixture name"}}}})");
    for(const auto& relative:{L"Microsoft/Edge/User Data/Default",L"BraveSoftware/Brave-Browser/User Data/Default",L"Opera Software/Opera Stable",L"Opera Software/Opera GX Stable",L"Vivaldi/User Data/Default",L"Yandex/YandexBrowser/User Data/Default",L"Chromium/User Data/Default"})write(fixture/relative/L"Preferences","{}");
    auto firefox=fixture/L"Mozilla/Firefox/Profiles/fixture";write(firefox/L"prefs.js","");
    write(fixture/L"Mozilla/Firefox/profiles.ini","[Profile0]\nName=Firefox fixture\nIsRelative=1\nPath=Profiles/fixture\n");
    auto sources=BrowserImportSources();check(sources.size()==10,"all-nine-browser-profile-discovery-without-login-data");
    ImportSource source;for(const auto& s:sources)if(s.id=="Chrome:Default")source=s;
    check(source.name=="Fixture name","discovery-profile-display-name");
    auto control=std::make_shared<ImportControl>();auto nodes=ReadImportBookmarks(source,control);
    auto report=CefDictionaryValue::Create();auto merged=MergeImportBookmarks(CefListValue::Create(),nodes,"import-one",report,control);
    check(merged->GetSize()==4&&report->GetInt("imported")==4,"nested-bookmarks-and-same-url-different-structure");
    auto repeated=CefDictionaryValue::Create();check(MergeImportBookmarks(merged,nodes,"import-one",repeated,control)->GetSize()==4&&repeated->GetInt("skipped")==4,"bookmark-repeat-deduplication");
    auto isolated=CefDictionaryValue::Create();check(MergeImportBookmarks(merged,nodes,"import-two",isolated,control)->GetSize()==8,"bookmark-profile-isolation");
    auto cancelled=std::make_shared<ImportControl>();cancelled->cancelled=true;auto cancelReport=CefDictionaryValue::Create();check(MergeImportBookmarks(merged,nodes,"import-one",cancelReport,cancelled)->GetSize()==4,"bookmark-cancellation");
    database(chrome/L"History","CREATE TABLE urls(id INTEGER,url TEXT,title TEXT); CREATE TABLE visits(url INTEGER,visit_time INTEGER); INSERT INTO urls VALUES(1,'https://example.test/','Fixture'); INSERT INTO visits VALUES(1,13344473600123000);");
    auto history=ImportBrowserHistory(source,"import-one",control);check(history->GetString("status")=="ok"&&history->GetInt("imported")==1,"chromium-history-reader");
    auto visits=HistoryStore("import-one").Query("",0,HistoryNow(),0,10);check(visits&&visits->GetSize()==1&&visits->GetDictionary(0)->GetDouble("visited")==1700000000123.0,"chromium-timestamp-conversion");
    check(ImportBrowserHistory(source,"import-one",control)->GetInt("skipped")==1,"history-repeat-deduplication");
    check(HistoryStore("import-two").Query("",0,HistoryNow(),0,10)->GetSize()==0,"history-profile-isolation");
    database(firefox/L"places.sqlite","CREATE TABLE moz_places(id INTEGER,url TEXT,title TEXT); CREATE TABLE moz_historyvisits(place_id INTEGER,visit_date INTEGER); CREATE TABLE moz_bookmarks(id INTEGER,parent INTEGER,type INTEGER,title TEXT,fk INTEGER,guid TEXT,position INTEGER); INSERT INTO moz_places VALUES(1,'https://example.test/firefox','Firefox fixture'); INSERT INTO moz_historyvisits VALUES(1,1700000000123000); INSERT INTO moz_bookmarks VALUES(1,0,2,'',NULL,'root________',0),(2,1,2,'Toolbar',NULL,'toolbar_____',0),(3,2,1,'Fixture',1,'fixture_____',0);");
    ImportSource ff=PortableImportSource(firefox);check(ReadImportBookmarks(ff,control)->GetDictionary(0)->GetList("children")->GetSize()==1,"firefox-separate-bookmark-adapter");
    check(ImportBrowserHistory(ff,"import-two",control)->GetInt("imported")==1,"firefox-history-reader");
    check(HistoryStore("import-two").Query("",0,HistoryNow(),0,10)->GetDictionary(0)->GetDouble("visited")==1700000000123.0,"firefox-timestamp-conversion");
    auto csv=fixture/L"fixture.csv";write(csv,"name,url,username,password\r\nFixture,https://example.test/,fixture,\"synthetic,secret\"\r\n");
    auto passwords=ImportPasswordCsv(csv,"import-one",control);check(passwords->GetString("status")=="ok"&&passwords->GetInt("imported")==1,"password-csv-quoted-field");
    check(ImportPasswordCsv(csv,"import-one",control)->GetInt("skipped")==1,"password-repeat-preserves-existing");
    check(PasswordVault("import-two").List()->GetSize()==0,"password-profile-isolation");
    write(csv,"url,username,password\nhttps://other.test/,fixture,valid\ninvalid,fixture,invalid\n");
    check(ImportPasswordCsv(csv,"import-one",control)->GetString("status")=="error"&&PasswordVault("import-one").List()->GetSize()==1,"csv-validation-before-any-write");

    database(chrome/L"Web Data","CREATE TABLE autofill(name TEXT,value TEXT); INSERT INTO autofill VALUES('email','fixture@example.test'),('email','fixture@example.test'),('card-number','4111111111111111'),('unclassified','4111 1111 1111 1111'); CREATE TABLE address_type_tokens(guid TEXT,type INTEGER,value TEXT); INSERT INTO address_type_tokens VALUES('fixture',3,'Synthetic name'),('fixture',35,'00000'),('fixture',52,'4111111111111111');");
    auto forms=ImportBrowserAutofill(source,"import-one",control);check(forms->GetString("status")=="ok"&&forms->GetInt("imported")==3,"autofill-form-values-address-types-payment-exclusion");
    check(ReadAutofill("import-one")->GetSize()==3&&ReadAutofill("import-two")->GetSize()==0,"autofill-decryption-profile-isolation");
    check(ImportBrowserAutofill(source,"import-one",control)->GetInt("skipped")==3,"autofill-repeat-deduplication");
    std::ifstream encryptedForms(ProfileRoot("import-one")/L"soulu-autofill.json",std::ios::binary);std::string encryptedText((std::istreambuf_iterator<char>(encryptedForms)),{});
    check(encryptedText.find("fixture@example.test")==std::string::npos&&encryptedText.find("Synthetic name")==std::string::npos,"autofill-no-plaintext-on-disk");
    write(firefox/L"autofill-profiles.json",R"({"version":1,"addresses":[{"given-name":"Firefox name","email":"ff@example.test"}],"creditCards":[{"cc-number":"4111111111111111"}]})");
    check(ImportBrowserAutofill(ff,"import-two",control)->GetInt("imported")==2,"firefox-address-import-excludes-credit-cards");
    check(ImportBrowserAutofill(source,"import-two",cancelled)->GetString("status")=="cancelled"&&ReadAutofill("import-two")->GetSize()==2,"autofill-cancellation-before-write");
    auto u32=[](uint32_t value){std::string b;for(int i=0;i<4;++i)b.push_back(static_cast<char>((value>>(i*8))&255));return b;};
    auto command=[](unsigned char id,const std::string& payload){size_t n=payload.size()+1;std::string b;b.push_back(static_cast<char>(n&255));b.push_back(static_cast<char>(n>>8));b.push_back(static_cast<char>(id));return b+payload;};
    const std::string tabUrl="https://example.test/tab";std::string nav=u32(10)+u32(0)+u32(static_cast<uint32_t>(tabUrl.size()))+tabUrl;while(nav.size()%4)nav.push_back(0);
    nav+=u32(0)+u32(0)+u32(0); // Empty title and page state; transition LINK.
    std::string snss="SNSS"+u32(3)+command(0,u32(10)+u32(1))+command(9,u32(1)+u32(0))+command(6,u32(static_cast<uint32_t>(nav.size()))+nav)+command(7,u32(10)+u32(0))+command(255,"");
    write(chrome/L"Sessions/Session_1",snss);check(ReadImportTabs(source,control)->GetSize()==1&&ReadImportTabs(source,control)->GetString(0)==tabUrl,"chromium-current-navigation-session-reader");
    write(chrome/L"Sessions/Session_1",snss+command(16,u32(10)+u32(0)+u32(0)+u32(0)));check(ReadImportTabs(source,control)->GetSize()==0,"chromium-closed-tab-exclusion");
    write(chrome/L"Sessions/Session_1","SNSS"+u32(5));bool protectedSession=false;try{ReadImportTabs(source,control);}catch(...){protectedSession=true;}check(protectedSession,"encrypted-chromium-session-rejected-without-bypass");
    write(chrome/L"Sessions/Session_1",snss.substr(0,snss.size()-1));bool truncated=false;try{ReadImportTabs(source,control);}catch(...){truncated=true;}check(truncated,"truncated-session-rejected");write(chrome/L"Sessions/Session_1",snss);
    const std::string session=R"JSON({"windows":[{"tabs":[{"index":2,"entries":[{"url":"https://example.test/old"},{"url":"https://example.test/current"}]},{"index":1,"entries":[{"url":"javascript:alert(1)"}]}]},{"isPrivate":true,"tabs":[{"index":1,"entries":[{"url":"https://example.test/private"}]}]}]})JSON";
    std::string literals;literals.push_back(static_cast<char>(0xf0));size_t remaining=session.size()-15;while(remaining>=255){literals.push_back(static_cast<char>(255));remaining-=255;}literals.push_back(static_cast<char>(remaining));literals+=session;
    write(firefox/L"sessionstore.jsonlz4",std::string("mozLz40\0",8)+u32(static_cast<uint32_t>(session.size()))+literals);
    auto ffTabs=ReadImportTabs(ff,control);check(ffTabs->GetSize()==1&&ffTabs->GetString(0)=="https://example.test/current","firefox-jsonlz4-selected-url-private-and-executable-exclusion");
    check(ReadImportTabs(ff,cancelled)->GetSize()==0,"tab-reader-cancellation");
    auto caps=BrowserImportCapabilities(source);check(caps->GetDictionary("bookmarks")->GetString("status")=="available"&&caps->GetDictionary("passwords")->GetString("status")=="not_found","truthful-capability-matrix");

    const std::string syntheticSecret="synthetic-only-secret";DATA_BLOB input{static_cast<DWORD>(syntheticSecret.size()),reinterpret_cast<BYTE*>(const_cast<char*>(syntheticSecret.data()))},sealed{};
    check(CryptProtectData(&input,L"Synthetic import fixture",nullptr,nullptr,nullptr,CRYPTPROTECT_UI_FORBIDDEN,&sealed)!=0,"fixture-password-dpapi");
    database(chrome/L"Login Data","CREATE TABLE logins(origin_url TEXT,username_value TEXT,password_value BLOB,blacklisted_by_user INTEGER)");sqlite3* loginDb=nullptr;
    check(sqlite3_open(CefString((chrome/L"Login Data").wstring()).ToString().c_str(),&loginDb)==SQLITE_OK,"fixture-logins-open");sqlite3_stmt* insert=nullptr;
    check(sqlite3_prepare_v2(loginDb,"INSERT INTO logins VALUES('https://native.example.test/','fixture',?,0)",-1,&insert,nullptr)==SQLITE_OK,"fixture-logins-prepare");sqlite3_bind_blob(insert,1,sealed.pbData,static_cast<int>(sealed.cbData),SQLITE_TRANSIENT);check(sqlite3_step(insert)==SQLITE_DONE,"fixture-logins-insert");sqlite3_finalize(insert);sqlite3_close(loginDb);SecureZeroMemory(sealed.pbData,sealed.cbData);LocalFree(sealed.pbData);
    auto direct=ImportBrowserPasswords(source,"import-two",control);check(direct->GetString("status")=="ok"&&direct->GetInt("imported")==1,"new-browser-adapter-direct-password-import");
    check(ImportBrowserPasswords(source,"import-two",control)->GetInt("skipped")==1,"direct-password-deduplication");
    check(ImportBrowserPasswords(source,"import-one",cancelled)->GetString("status")=="cancelled"&&PasswordVault("import-one").List()->GetSize()==1,"direct-password-cancellation-isolation");
    std::ifstream original(chrome/L"Bookmarks",std::ios::binary);std::string after((std::istreambuf_iterator<char>(original)),{});check(after==bookmarks,"source-bookmarks-unchanged");
    check(!std::filesystem::exists(chrome/L"History-shm")&&!std::filesystem::exists(firefox/L"places.sqlite-shm"),"no-source-sqlite-sidecars-created");
    std::ofstream out(output);out<<"{\"ok\":true,\"checks\":"<<checks<<"}";return out?0:2;
  }catch(const std::exception& e){std::ofstream out(output);out<<"{\"ok\":false,\"checks\":"<<checks<<",\"failedCheck\":\""<<e.what()<<"\"}";return 2;}
}
}
