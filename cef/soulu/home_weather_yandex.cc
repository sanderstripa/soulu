#include "examples/soulu/home_weather_yandex.h"
#include "include/cef_parser.h"
#include <algorithm>
#include <cmath>
namespace soulu {
namespace {
int IconCode(const std::string& icon){
 if(icon.find("ts")!=std::string::npos)return 95;
 if(icon.find("sn")!=std::string::npos)return 71;
 if(icon.find("ra")!=std::string::npos)return 61;
 if(icon.find("fg")!=std::string::npos)return 45;
 if(icon.find("ovc")!=std::string::npos)return 3;
 if(icon.find("bkn")!=std::string::npos)return 2;
 if(icon.find("few")!=std::string::npos)return 1;
 return icon.find("skc")!=std::string::npos?0:-1;
}
bool Numeric(CefRefPtr<CefDictionaryValue> value,const char* key){return value&&(value->GetType(key)==VTYPE_INT||value->GetType(key)==VTYPE_DOUBLE)&&std::isfinite(value->GetDouble(key));}
double Number(CefRefPtr<CefDictionaryValue> value,const char* key){return value->GetType(key)==VTYPE_INT?value->GetInt(key):value->GetDouble(key);}
}
std::string YandexWeatherQuery(double lat,double lon){
 const std::string query="{weatherByPoint(request:{lat:"+std::to_string(lat)+",lon:"+std::to_string(lon)+"}){now{temperature(unit:CELSIUS) humidity windSpeed prec icon(format:CODE)} forecast{days(limit:6){time hours{temperature(unit:CELSIUS) precProbability icon(format:CODE)}}}}}";
 auto data=CefDictionaryValue::Create();data->SetString("query",query);auto value=CefValue::Create();value->SetDictionary(data);return CefWriteJSON(value,JSON_WRITER_DEFAULT);
}
CefRefPtr<CefDictionaryValue> NormalizeYandexWeather(CefRefPtr<CefDictionaryValue> raw,const std::string& units,const std::string& city){
 auto data=raw?raw->GetDictionary("data"):nullptr;auto point=data?data->GetDictionary("weatherByPoint"):nullptr;auto now=point?point->GetDictionary("now"):nullptr;
 if(!Numeric(now,"temperature"))return nullptr;
 const auto temperature=[units](double value){return units=="fahrenheit"?value*1.8+32:value;};
 auto result=CefDictionaryValue::Create(),current=CefDictionaryValue::Create(),daily=CefDictionaryValue::Create();
 result->SetString("provider","yandex");result->SetString("source","Яндекс Погода");result->SetString("sourceUrl","https://yandex.ru/pogoda/");result->SetString("city",city);
 current->SetDouble("temperature_2m",temperature(Number(now,"temperature")));current->SetInt("weather_code",IconCode(now->GetString("icon")));
 if(Numeric(now,"humidity"))current->SetDouble("relative_humidity_2m",Number(now,"humidity"));
 if(Numeric(now,"windSpeed"))current->SetDouble("wind_speed_10m",Number(now,"windSpeed")*3.6);
 if(Numeric(now,"prec"))current->SetDouble("precipitation",Number(now,"prec"));
 auto times=CefListValue::Create(),codes=CefListValue::Create(),highs=CefListValue::Create(),lows=CefListValue::Create(),rain=CefListValue::Create();
 auto forecast=point->GetDictionary("forecast");auto days=forecast?forecast->GetList("days"):nullptr;
 if(!days)return nullptr;
 for(size_t i=0;i<std::min<size_t>(7,days->GetSize());++i){
  auto day=days->GetDictionary(i);if(!day)continue;const std::string date=day->GetString("time");auto hours=day->GetList("hours");if(date.size()<10||!hours||!hours->GetSize())continue;
  double low=1000,high=-1000,probability=-1;int code=-1;size_t count=0;
  for(size_t h=0;h<hours->GetSize();++h){auto hour=hours->GetDictionary(h);if(!Numeric(hour,"temperature"))continue;const double value=temperature(Number(hour,"temperature"));low=std::min(low,value);high=std::max(high,value);++count;if(h==hours->GetSize()/2||code<0)code=IconCode(hour->GetString("icon"));if(Numeric(hour,"precProbability"))probability=std::max(probability,Number(hour,"precProbability"));}
  if(!count)continue;const auto n=times->GetSize();times->SetString(n,date.substr(0,10));codes->SetInt(n,code);highs->SetDouble(n,high);lows->SetDouble(n,low);rain->SetDouble(n,probability);
 }
 if(!times->GetSize())return nullptr;
 daily->SetList("time",times);daily->SetList("weather_code",codes);daily->SetList("temperature_2m_max",highs);daily->SetList("temperature_2m_min",lows);daily->SetList("precipitation_probability_max",rain);
 result->SetDictionary("current",current);result->SetDictionary("daily",daily);return result;
}
}
