#pragma once
#include "include/cef_values.h"
#include <string>
namespace soulu {
CefRefPtr<CefDictionaryValue> NormalizeYandexWeather(CefRefPtr<CefDictionaryValue>,const std::string&,const std::string&);
std::string YandexWeatherQuery(double,double);
}
