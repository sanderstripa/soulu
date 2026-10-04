#pragma once
#include <windows.h>
#include <string>
#include "examples/soulu/typography_metrics.h"

namespace soulu {
HFONT TypographyFont(typography::Metrics role, UINT dpi);
// Same result IDs/default-button semantics as MessageBox, with private Onest.
int TypographyMessageBox(HWND owner, const wchar_t* text, const wchar_t* title, UINT flags,
                         const void* tag=nullptr);
bool TypographyPrompt(HWND owner, const std::wstring& text, const std::wstring& initial,
                      std::wstring& result, const void* tag=nullptr);
void TypographyCancelDialogs(const void* tag);
void TypographyCancelOwnedDialogs(HWND owner);
bool TypographyMenuMessage(UINT message,LPARAM parameter);
}
