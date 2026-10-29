#include "examples/soulu/home_weather_yandex.h"
#include "examples/soulu/vpn_routing.h"
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
 auto raw=CefParseJSON(R"JSON({"data":{"weatherByPoint":{"now":{"temperature":6,"humidity":80,"windSpeed":2.5,"prec":0.2,"icon":"bkn_d"},"forecast":{"days":[{"time":"2026-10-29T00:00:00+05:00","hours":[{"temperature":2,"precProbability":10,"icon":"skc_d"},{"temperature":8,"precProbability":70,"icon":"ra_d"}]}]}}}})JSON",JSON_PARSER_RFC);
 auto c=NormalizeYandexWeather(raw->GetDictionary(),"celsius","City"),fa=NormalizeYandexWeather(raw->GetDictionary(),"fahrenheit","City");
 check(c&&c->GetDictionary("current")->GetDouble("temperature_2m")==6,"Yandex integer temperature");
 check(c&&c->GetDictionary("current")->GetDouble("wind_speed_10m")==9,"Yandex wind m/s to km/h");
 check(c&&c->GetDictionary("daily")->GetList("temperature_2m_min")->GetDouble(0)==2&&c->GetDictionary("daily")->GetList("temperature_2m_max")->GetDouble(0)==8,"Yandex daily range");
 check(c&&c->GetDictionary("daily")->GetList("precipitation_probability_max")->GetDouble(0)==70,"Yandex precipitation probability");
 check(fa&&fa->GetDictionary("current")->GetDouble("temperature_2m")>42.7&&fa->GetDictionary("current")->GetDouble("temperature_2m")<42.9,"Yandex Fahrenheit conversion");
 check(!NormalizeYandexWeather(CefDictionaryValue::Create(),"celsius","City"),"Yandex malformed response rejected");
 auto vpn=CefDictionaryValue::Create();vpn->SetString("directDomains"," https://Example.COM/path\n*.bank.example\nexample.com\n");std::string error;
 check(NormalizeVpnRouting(vpn,error)&&vpn->GetString("directDomains")=="example.com\nbank.example","VPN canonical domain deduplication");
 check(VpnBypassList(vpn)=="<-loopback>;example.com;*.example.com;bank.example;*.bank.example","VPN exact and subdomain bypass");
 vpn->SetString("directDomains","file:///C:/private");check(!NormalizeVpnRouting(vpn,error),"VPN non-web address rejected");
 auto secret=CefDictionaryValue::Create();secret->SetString("token","fixture-only-private-token");secret->SetString("key","fixture-only-weather-key");
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
