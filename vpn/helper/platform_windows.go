package main
import("os/exec";"syscall";"unsafe")
func hideProcess(cmd *exec.Cmd){cmd.SysProcAttr=&syscall.SysProcAttr{HideWindow:true,CreationFlags:0x08000000}}
func replaceFile(from,to string)error{a,e:=syscall.UTF16PtrFromString(from);if e!=nil{return e};b,e:=syscall.UTF16PtrFromString(to);if e!=nil{return e};v,_,err:=syscall.NewLazyDLL("kernel32.dll").NewProc("MoveFileExW").Call(uintptr(unsafe.Pointer(a)),uintptr(unsafe.Pointer(b)),9);if v==0{return err};return nil}
func updateLock()(func(),error){name,_:=syscall.UTF16PtrFromString("Local\\SouluVpnComponentUpdate");kernel:=syscall.NewLazyDLL("kernel32.dll");h,_,e:=kernel.NewProc("CreateMutexW").Call(0,0,uintptr(unsafe.Pointer(name)));if h==0{return nil,e};v,_,e:=kernel.NewProc("WaitForSingleObject").Call(h,10000);if v!=0&&v!=0x80{kernel.NewProc("CloseHandle").Call(h);return nil,e};return func(){kernel.NewProc("ReleaseMutex").Call(h);kernel.NewProc("CloseHandle").Call(h)},nil}
