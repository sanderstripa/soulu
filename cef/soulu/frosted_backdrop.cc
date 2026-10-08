#include "examples/soulu/frosted_backdrop.h"
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.System.h>
#include <winrt/Windows.UI.ViewManagement.h>
#include <winrt/Windows.UI.Composition.Desktop.h>
#include <windows.ui.composition.interop.h>
#include <DispatcherQueue.h>
#include <dwmapi.h>
#include <map>
#include <algorithm>
namespace soulu {
namespace {
using namespace winrt;
using namespace Windows::UI::Composition;
struct Backdrop {
  Windows::System::DispatcherQueueController queue{nullptr};
  Compositor compositor{nullptr};
  Desktop::DesktopWindowTarget target{nullptr};
  SpriteVisual visual{nullptr};
  ContainerVisual settings_root{nullptr};
  SpriteVisual settings_shadow{nullptr};
};
std::map<HWND,Backdrop> backdrops;
}
int BackdropCapabilities(){
  BOOL composition=FALSE;DwmIsCompositionEnabled(&composition);
  int flags=composition?1:0;
  try{if(winrt::Windows::UI::ViewManagement::UISettings().AdvancedEffectsEnabled())flags|=2;}catch(...){}
  if(GetSystemMetrics(SM_REMOTESESSION))flags|=4;
  HIGHCONTRASTW contrast={sizeof(contrast)};
  if(SystemParametersInfoW(SPI_GETHIGHCONTRAST,sizeof(contrast),&contrast,0) && (contrast.dwFlags&HCF_HIGHCONTRASTON))flags|=8;
  return flags;
}
bool ConfigureFrostedBackdrop(HWND window,bool enabled){
  try {
    auto& state=backdrops[window];
    if(!state.compositor){
      if(!Windows::System::DispatcherQueue::GetForCurrentThread()){
        DispatcherQueueOptions options={sizeof(options),DQTYPE_THREAD_CURRENT,DQTAT_COM_NONE};
        check_hresult(CreateDispatcherQueueController(options,reinterpret_cast<ABI::Windows::System::IDispatcherQueueController**>(put_abi(state.queue))));
      }
      state.compositor=Compositor();
      auto interop=state.compositor.as<ABI::Windows::UI::Composition::Desktop::ICompositorDesktopInterop>();
      check_hresult(interop->CreateDesktopWindowTarget(window,false,reinterpret_cast<ABI::Windows::UI::Composition::Desktop::IDesktopWindowTarget**>(put_abi(state.target))));
      state.visual=state.compositor.CreateSpriteVisual();
      state.visual.Brush(state.compositor.CreateHostBackdropBrush());
      state.target.Root(state.visual);
    }
    BOOL host=enabled?TRUE:FALSE;
    check_hresult(DwmSetWindowAttribute(window,17,&host,sizeof(host)));
    state.visual.IsVisible(enabled);
    return enabled;
  }catch(const hresult_error& error){
    wchar_t text[96]={};swprintf_s(text,L"Soulu backdrop error: 0x%08X\n",static_cast<unsigned>(error.code().value));
    OutputDebugStringW(text);
    return false;
  }
}
void ResizeFrostedBackdrop(HWND window,int width,int height){
  const auto found=backdrops.find(window);
  if(found!=backdrops.end()&&found->second.visual)
    found->second.visual.Size({static_cast<float>(width),static_cast<float>(height)});
}
void SetFrostedBackdropOpacity(HWND window,float opacity){
  const auto found=backdrops.find(window);
  if(found!=backdrops.end()&&found->second.visual)found->second.visual.Opacity(opacity);
  if(found!=backdrops.end()&&found->second.settings_shadow)found->second.settings_shadow.Opacity(opacity);
}
void SetSettingsBackdropPanel(HWND window,float x,float y,float width,float height,float scale){
  const auto found=backdrops.find(window);if(found==backdrops.end())return;
  try{
    auto& state=found->second;
    if(!state.settings_root){
      state.settings_root=state.compositor.CreateContainerVisual();
      state.target.Root(nullptr);
      state.settings_root.Children().InsertAtBottom(state.visual);
      state.settings_shadow=state.compositor.CreateSpriteVisual();
      state.settings_shadow.Opacity(state.visual.Opacity());
      state.settings_shadow.Brush(state.compositor.CreateColorBrush(Windows::UI::Color{255,32,33,36}));
      const auto shadow=state.compositor.CreateDropShadow();
      shadow.Color(Windows::UI::Color{255,0,0,0});shadow.Opacity(.34f);
      shadow.BlurRadius(20*scale);shadow.Offset({0,8*scale,0});
      state.settings_shadow.Shadow(shadow);
      state.settings_root.Children().InsertAtTop(state.settings_shadow);
      state.target.Root(state.settings_root);
    }
    state.settings_shadow.Opacity(y+height>0 ? state.visual.Opacity() : 0);
    state.settings_shadow.Offset({x+2*scale,y,0});
    state.settings_shadow.Size({std::max(1.f,width-4*scale),std::max(1.f,height-3*scale)});
  }catch(const hresult_error&){/* The Settings edge remains visible without shadows. */}
}
void ReleaseFrostedBackdrop(HWND window){backdrops.erase(window);}
}
