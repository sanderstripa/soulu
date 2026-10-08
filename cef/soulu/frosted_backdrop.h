#pragma once
#include <windows.h>
namespace soulu {
int BackdropCapabilities();
bool ConfigureFrostedBackdrop(HWND window, bool enabled);
void ResizeFrostedBackdrop(HWND window, int width, int height);
void SetFrostedBackdropOpacity(HWND window, float opacity);
void SetSettingsBackdropPanel(HWND window, float x, float y, float width, float height, float scale);
void ReleaseFrostedBackdrop(HWND window);
}
