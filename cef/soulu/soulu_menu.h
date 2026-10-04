#pragma once
#include <windows.h>
#include <string>
#include <vector>

namespace soulu {
enum class MenuItemType { Action, Separator, Check, Radio, Submenu };
struct MenuItem {
  int command = 0;
  std::wstring label;
  std::wstring accelerator;
  bool enabled = true;
  bool checked = false;
  MenuItemType type = MenuItemType::Action;
  std::vector<MenuItem> children;
  static MenuItem Separator() { MenuItem item; item.type=MenuItemType::Separator; return item; }
};
using MenuModel = std::vector<MenuItem>;
struct MenuAppearance { bool dark=false; };
// Owns a copied model for the entire popup session. Zero means dismissed.
int ShowSouluMenu(HWND owner, POINT anchor, MenuModel model, MenuAppearance appearance);
void DismissSouluMenus(HWND owner);
std::wstring MenuLabel(const std::wstring& mnemonicLabel);
}
