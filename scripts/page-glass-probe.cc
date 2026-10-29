#include <unknwn.h>
#include <windows.h>
#include <DispatcherQueue.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.System.h>
#include <iostream>
#include "examples/soulu/page_glass.h"
namespace {
COLORREF fill=RGB(25,160,70);
LRESULT CALLBACK Proc(HWND window,UINT message,WPARAM wp,LPARAM lp){
 if(message==WM_PAINT){PAINTSTRUCT ps;auto dc=BeginPaint(window,&ps);RECT r;GetClientRect(window,&r);auto brush=CreateSolidBrush(GetWindowLongPtrW(window,GWLP_USERDATA)?fill:RGB(250,250,250));FillRect(dc,&r,brush);DeleteObject(brush);EndPaint(window,&ps);return 0;}
 return DefWindowProcW(window,message,wp,lp);
}
void pump(DWORD duration){const auto end=GetTickCount64()+duration;MSG m;while(GetTickCount64()<end){while(PeekMessageW(&m,nullptr,0,0,PM_REMOVE)){TranslateMessage(&m);DispatchMessageW(&m);}Sleep(10);}}
}
int main(){
 winrt::init_apartment(winrt::apartment_type::single_threaded);
 winrt::Windows::System::DispatcherQueueController queue{nullptr};
 DispatcherQueueOptions options={sizeof(options),DQTYPE_THREAD_CURRENT,DQTAT_COM_STA};
 winrt::check_hresult(CreateDispatcherQueueController(options,reinterpret_cast<ABI::Windows::System::IDispatcherQueueController**>(winrt::put_abi(queue))));
 WNDCLASSW wc={};wc.lpfnWndProc=Proc;wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=L"SouluGlassProbe";RegisterClassW(&wc);
 HWND root=CreateWindowExW(0,wc.lpszClassName,L"Soulu glass compositor probe",WS_OVERLAPPEDWINDOW|WS_CLIPCHILDREN,80,80,700,400,nullptr,nullptr,wc.hInstance,nullptr);
 HWND source=CreateWindowExW(0,wc.lpszClassName,L"Live page source",WS_CHILD|WS_VISIBLE,0,0,700,400,root,nullptr,wc.hInstance,nullptr);SetWindowLongPtrW(source,GWLP_USERDATA,1);
 ShowWindow(root,SW_SHOW);SetWindowPos(root,HWND_TOPMOST,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_SHOWWINDOW);SetForegroundWindow(root);UpdateWindow(root);UpdateWindow(source);pump(250);
 HWND glass=soulu::UpdatePageGlass(root,680,80,1,true,false);
 std::cout<<"ready="<<(glass!=nullptr)<<" HRESULT="<<std::hex<<static_cast<unsigned>(soulu::PageGlassError(root))<<std::dec<<std::endl;
 if(!glass){DestroyWindow(root);return 2;}
 SetWindowPos(glass,HWND_TOP,0,0,680,80,SWP_SHOWWINDOW|SWP_NOACTIVATE);pump(500);
 POINT point={300,64};ClientToScreen(root,&point);auto screen=GetDC(nullptr);auto a=GetPixel(screen,point.x,point.y);ReleaseDC(nullptr,screen);
 fill=RGB(195,40,35);InvalidateRect(source,nullptr,TRUE);UpdateWindow(source);pump(500);screen=GetDC(nullptr);auto b=GetPixel(screen,point.x,point.y);ReleaseDC(nullptr,screen);
 std::cout<<"green="<<int(GetRValue(a))<<","<<int(GetGValue(a))<<","<<int(GetBValue(a))<<" red="<<int(GetRValue(b))<<","<<int(GetGValue(b))<<","<<int(GetBValue(b))<<std::endl;
 const bool live=GetGValue(a)>GetRValue(a)+8&&GetRValue(b)>GetGValue(b)+8;
 soulu::ReleasePageGlass(root);DestroyWindow(root);return live?0:3;
}
