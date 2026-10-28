#include "examples/soulu/page_glass.h"
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Graphics.Effects.h>
#include <winrt/Windows.UI.Composition.h>
#include <winrt/Windows.UI.Composition.Desktop.h>
#include <windows.ui.composition.interop.h>
#include <windows.graphics.effects.interop.h>
#include <d2d1effects.h>
#include <map>
namespace soulu {
namespace {
using namespace winrt;
using namespace Windows::UI::Composition;
using namespace Windows::Graphics::Effects;
struct Blur final : implements<Blur,IGraphicsEffect,IGraphicsEffectSource,IGraphicsEffectD2D1Interop> {
  IGraphicsEffectSource source;
  explicit Blur(IGraphicsEffectSource const& value):source(value){}
  hstring Name() const {return L"PageBlur";} void Name(hstring const&) {}
  HRESULT __stdcall GetEffectId(GUID* value) noexcept override {*value=CLSID_D2D1GaussianBlur;return S_OK;}
  HRESULT __stdcall GetNamedPropertyMapping(LPCWSTR,UINT*,GRAPHICS_EFFECT_PROPERTY_MAPPING*) noexcept override {return E_INVALIDARG;}
  HRESULT __stdcall GetPropertyCount(UINT* value) noexcept override {*value=3;return S_OK;}
  HRESULT __stdcall GetProperty(UINT index,ABI::Windows::Foundation::IPropertyValue** value) noexcept override {
    try {Windows::Foundation::IPropertyValue property{nullptr};
      if(index==0)property=box_value(4.f).as<Windows::Foundation::IPropertyValue>();
      else if(index==1)property=box_value(uint32_t(D2D1_GAUSSIANBLUR_OPTIMIZATION_BALANCED)).as<Windows::Foundation::IPropertyValue>();
      else if(index==2)property=box_value(uint32_t(D2D1_BORDER_MODE_HARD)).as<Windows::Foundation::IPropertyValue>();
      else return E_INVALIDARG;
      *value=reinterpret_cast<ABI::Windows::Foundation::IPropertyValue*>(detach_abi(property));return S_OK;
    }catch(...){return to_hresult();}
  }
  HRESULT __stdcall GetSourceCount(UINT* value) noexcept override {*value=1;return S_OK;}
  HRESULT __stdcall GetSource(UINT index,ABI::Windows::Graphics::Effects::IGraphicsEffectSource** value) noexcept override {
    if(index)return E_INVALIDARG;auto copy=source;*value=reinterpret_cast<ABI::Windows::Graphics::Effects::IGraphicsEffectSource*>(detach_abi(copy));return S_OK;
  }
};
struct Glass {HWND hwnd=nullptr;Compositor compositor{nullptr};Desktop::DesktopWindowTarget target{nullptr};ContainerVisual root{nullptr};SpriteVisual blur{nullptr},tint{nullptr};};
std::map<HWND,Glass> glasses;
}
HWND UpdatePageGlass(HWND parent,int width,int height,float scale,bool enabled,bool dark){
  if(!enabled){auto i=glasses.find(parent);if(i!=glasses.end())ShowWindow(i->second.hwnd,SW_HIDE);return nullptr;}
  try {auto& g=glasses[parent];
    if(!g.hwnd){
      g.hwnd=CreateWindowExW(WS_EX_NOREDIRECTIONBITMAP|WS_EX_TRANSPARENT|WS_EX_NOACTIVATE,L"STATIC",L"Soulu page glass",WS_CHILD,0,0,1,1,parent,nullptr,GetModuleHandleW(nullptr),nullptr);
      if(!g.hwnd)throw hresult_error(HRESULT_FROM_WIN32(GetLastError()));
      g.compositor=Compositor();auto interop=g.compositor.as<ABI::Windows::UI::Composition::Desktop::ICompositorDesktopInterop>();
      check_hresult(interop->CreateDesktopWindowTarget(g.hwnd,true,reinterpret_cast<ABI::Windows::UI::Composition::Desktop::IDesktopWindowTarget**>(put_abi(g.target))));
      g.root=g.compositor.CreateContainerVisual();g.target.Root(g.root);
      auto source=CompositionEffectSourceParameter(L"Page");
      auto effect=g.compositor.CreateEffectFactory(make<Blur>(source.as<IGraphicsEffectSource>()));auto brush=effect.CreateBrush();
      brush.SetSourceParameter(L"Page",g.compositor.CreateBackdropBrush());
      g.blur=g.compositor.CreateSpriteVisual();g.blur.Brush(brush);g.root.Children().InsertAtBottom(g.blur);
      g.tint=g.compositor.CreateSpriteVisual();g.root.Children().InsertAtTop(g.tint);
    }
    auto gradient=g.compositor.CreateLinearGradientBrush();gradient.StartPoint({0,0});gradient.EndPoint({0,1});
    const BYTE c=dark?14:250;
    gradient.ColorStops().Append(g.compositor.CreateColorGradientStop(0,{254,c,c,c}));
    gradient.ColorStops().Append(g.compositor.CreateColorGradientStop(.35f,{249,c,c,c}));
    gradient.ColorStops().Append(g.compositor.CreateColorGradientStop(.7f,{232,c,c,c}));
    gradient.ColorStops().Append(g.compositor.CreateColorGradientStop(1,{190,c,c,c}));
    g.tint.Brush(gradient);g.root.Size({float(width),float(height)});g.blur.Size(g.root.Size());g.tint.Size(g.root.Size());
    return g.hwnd;
  }catch(...){auto i=glasses.find(parent);if(i!=glasses.end()&&i->second.hwnd)ShowWindow(i->second.hwnd,SW_HIDE);return nullptr;}
}
void ReleasePageGlass(HWND parent){auto i=glasses.find(parent);if(i!=glasses.end()){if(i->second.hwnd)DestroyWindow(i->second.hwnd);glasses.erase(i);}}
}
