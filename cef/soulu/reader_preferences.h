#pragma once
#include <string>
#include "include/cef_values.h"

namespace soulu {
// The appearance palette and Settings transaction validate the same preferences.
inline bool IsReaderThemeSupported(const std::string& theme) {
  return theme=="light"||theme=="sepia"||theme=="gray"||theme=="dark";
}
bool IsReaderFontSupported(const std::string& font);
CefRefPtr<CefListValue> ReaderFontChoices();
}
