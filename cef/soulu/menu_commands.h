#pragma once
#include "include/internal/cef_types.h"
namespace soulu {
enum MenuCommand {
  kLinkForeground=MENU_ID_USER_FIRST,kLinkBackground,kLinkIncognito,kLinkSave,kLinkCopy,
  kLinkWindow,kImageOpen,kImageSave,kImageCopyAddress,kImageCopy,kSelectionSearch,
  kPageSave,kPageReader,kPageTranslate,kPageQR,kInspect,
  kMediaPlay,kMediaMute,kMediaLoop,kMediaControls,kMediaSave,kMediaCopy,
};
static_assert(kMediaCopy<=MENU_ID_USER_LAST);
}
