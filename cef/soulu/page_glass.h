#pragma once
#include <windows.h>
namespace soulu {
HWND UpdatePageGlass(HWND parent,int width,int height,float scale,bool enabled,bool dark);
int PageGlassError(HWND parent);
void ReleasePageGlass(HWND parent);
}
