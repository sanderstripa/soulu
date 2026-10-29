#include "examples/soulu/vpn_routing.h"
#include "examples/soulu/vpn_profiles.h"
#include "examples/soulu/protected_store.h"
#include "examples/soulu/video_bridge.h"
#include "examples/soulu/profile_data.h"
#include "include/cef_parser.h"
#include <fstream>
#include <iterator>
namespace soulu {
int RunComponentTests(const std::filesystem::path& output){
 auto report=CefDictionaryValue::Create();auto checks=CefListValue::Create();bool passed=true;
 auto check=[&](bool ok,const std::string& label){auto row=CefDictionaryValue::Create();row->SetBool("passed",ok);row->SetString("check",label);checks->SetDictionary(checks->GetSize(),row);passed=passed&&ok;};
 auto locale_request=CefDictionaryValue::Create();locale_request->SetString("method","GET");locale_request->SetString("url","https://raw.githubusercontent.com/ilyhalight/voice-over-translation/master/src/localization/locales/ru.json?timestamp=1");
 auto locale=BundledVideoLocaleResponse(locale_request);check(locale&&locale->GetInt("status")==200&&!locale->GetString("body").empty(),"VOT Russian locale is available without a network request");
 locale_request->SetString("url","https://raw.githubusercontent.com/evil/repository/master/src/localization/locales/ru.json");check(!BundledVideoLocaleResponse(locale_request),"Packaged locale cache is restricted to the pinned upstream repository");
 auto vpn=CefDictionaryValue::Create();vpn->SetString("directDomains"," https://Example.COM/path\n*.bank.example\nexample.com\n");std::string error;
 check(NormalizeVpnRouting(vpn,error)&&vpn->GetString("directDomains")=="example.com\nbank.example","VPN canonical domain deduplication");
 check(VpnBypassList(vpn)=="<-loopback>;example.com;*.example.com;bank.example;*.bank.example","VPN exact and subdomain bypass");
 vpn->SetString("directDomains","file:///C:/private");check(!NormalizeVpnRouting(vpn,error),"VPN non-web address rejected");
 auto connections=CefDictionaryValue::Create();connections->SetString("link","vless://11111111-1111-4111-8111-111111111111@example.com:443?encryption=none");connections->SetString("protocol","vless");connections->SetString("lastProfileId","legacy-id");
 check(NormalizeVpnProfiles(connections,error)&&connections->GetList("profiles")->GetSize()==1&&connections->GetString("defaultProfileId")=="legacy-id","Legacy VPN key migrates without losing its selected ID");
 auto profiles=connections->GetList("profiles");auto second=profiles->GetDictionary(0)->Copy(false);second->SetString("id","second");second->SetString("link","vless://22222222-2222-4222-8222-222222222222@second.example:8443?encryption=none");profiles->SetDictionary(1,second);connections->SetString("defaultProfileId","second");check(NormalizeVpnProfiles(connections,error)&&connections->GetString("link")==second->GetString("link")&&profiles->GetDictionary(0)->GetString("id")=="legacy-id","Selecting a saved VPN key retains other connections");
 auto invalid=connections->Copy(false);invalid->GetList("profiles")->GetDictionary(1)->SetString("id","legacy-id");check(!NormalizeVpnProfiles(invalid,error),"Duplicate VPN profile IDs are rejected");
 auto many=connections->Copy(false);for(int i=0;i<1200;++i){auto row=second->Copy(false);row->SetString("id","fixture-"+std::to_string(i));many->GetList("profiles")->SetDictionary(many->GetList("profiles")->GetSize(),row);}check(NormalizeVpnProfiles(many,error)&&many->GetList("profiles")->GetSize()==1202,"Saved VPN profiles have no small fixed count limit");
 auto legacy=connections->Copy(false);legacy->SetString("link","vless://33333333-3333-4333-8333-333333333333@third.example:443?encryption=none");MergeLegacyVpnSelection(legacy,connections);check(NormalizeVpnProfiles(legacy,error)&&legacy->GetList("profiles")->GetSize()==3&&legacy->GetString("link")!=connections->GetString("link"),"Legacy key updates add a connection without discarding saved keys");
 auto secret=CefDictionaryValue::Create();secret->SetString("token","fixture-only-private-token");
 check(WriteProtectedStore("personal","video",secret),"DPAPI video settings written");
 auto loaded=ReadProtectedStore("personal","video");check(loaded&&loaded->GetString("token")=="fixture-only-private-token","DPAPI video settings restored");
 const auto file=ProfileRoot("personal")/"soulu-private-video.json";std::ifstream in(file,std::ios::binary);const std::string bytes(std::istreambuf_iterator<char>(in),{});in.close();
 check(bytes.find("fixture-only")==std::string::npos,"No plaintext token on disk");
 std::error_code ec;std::filesystem::create_directories(ProfileRoot("work"),ec);std::filesystem::copy_file(file,ProfileRoot("work")/"soulu-private-video.json",std::filesystem::copy_options::overwrite_existing,ec);
 check(!ec&&!ReadProtectedStore("work","video"),"Profile-bound DPAPI entropy");
 check(SaveVideoPreferences("__incognito__",secret)&&VideoPreferences("__incognito__")->GetString("token")=="fixture-only-private-token","Private video settings in memory");
 ForgetPrivateVideoPreferences();check(!VideoPreferences("__incognito__")->HasKey("token"),"Private video settings disposed");
 check(!WriteProtectedStore("../escape","video",secret)&&!WriteProtectedStore("personal","../escape",secret),"Protected path traversal rejected");
 report->SetBool("passed",passed);report->SetList("checks",checks);auto value=CefValue::Create();value->SetDictionary(report);std::ofstream out(output,std::ios::binary);out<<CefWriteJSON(value,JSON_WRITER_PRETTY_PRINT).ToString();return out&&passed?0:2;
}
}
