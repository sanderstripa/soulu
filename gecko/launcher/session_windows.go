//go:build windows

package main

import (
 "crypto/rand"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "runtime"
 "strings"
 "syscall"
 "sync"
 "time"
 "unsafe"
)

var kernelSession=syscall.NewLazyDLL("kernel32.dll")
var userSession=syscall.NewLazyDLL("user32.dll")
func profileKey(profile string) string {sum:=sha256.Sum256([]byte(strings.ToLower(filepath.Clean(profile))));return hex.EncodeToString(sum[:16])}
func sessionMutexName(profile string)string{return `Local\Soulu.`+profileKey(profile)}
type sessionGuard struct{handle syscall.Handle}
func(g *sessionGuard)Close(){kernelSession.NewProc("ReleaseMutex").Call(uintptr(g.handle));syscall.CloseHandle(g.handle);runtime.UnlockOSThread()}
// A mutex handle is not ownership. Waiters must acquire it after the preceding
// owner exits, even when other waiters keep the named object alive.
func acquireSession(profile string,forward func()bool,budget time.Duration)(*sessionGuard,bool,error){
 runtime.LockOSThread()
 name,_:=syscall.UTF16PtrFromString(sessionMutexName(profile));h,_,e:=kernelSession.NewProc("CreateMutexW").Call(0,0,uintptr(unsafe.Pointer(name)))
 if h==0{runtime.UnlockOSThread();return nil,false,e}
 deadline:=time.Now().Add(budget)
 for{
  status,_,waitErr:=kernelSession.NewProc("WaitForSingleObject").Call(h,0)
  if status==0||status==0x80{return &sessionGuard{syscall.Handle(h)},false,nil}
  if status!=0x102{syscall.CloseHandle(syscall.Handle(h));runtime.UnlockOSThread();return nil,false,waitErr}
  if forward(){syscall.CloseHandle(syscall.Handle(h));runtime.UnlockOSThread();return nil,true,nil}
  if time.Now().After(deadline){syscall.CloseHandle(syscall.Handle(h));runtime.UnlockOSThread();return nil,false,fmt.Errorf("не удалось дождаться завершения предыдущего сеанса")}
  time.Sleep(50*time.Millisecond)
 }
}
func sessionLog(profile,stage string){
 file:=filepath.Join(profile,"soulu-launcher.log")
 f,e:=os.OpenFile(file,os.O_CREATE|os.O_WRONLY|os.O_APPEND,0600);if e!=nil{return};defer f.Close()
 fmt.Fprintf(f,"%s pid=%d %s\n",time.Now().UTC().Format(time.RFC3339Nano),os.Getpid(),stage)
}
type jobBasicLimits struct{ProcessTime,JobTime int64;Flags uint32;MinWorking,MaxWorking uintptr;Active uint32;Affinity uintptr;Priority,Scheduling uint32}
type jobLimits struct{Basic jobBasicLimits;IO [6]uint64;ProcessMemory,JobMemory,PeakProcessMemory,PeakJobMemory uintptr}
type sessionJob struct{handle syscall.Handle;name string;callback uintptr;found []uintptr;mu sync.Mutex}
type sessionRecord struct{Leader int `json:"leader"`;Job string `json:"job"`}
func newSessionJob(profile string)(*sessionJob,error){
 nonce:=make([]byte,16);if _,e:=rand.Read(nonce);e!=nil{return nil,e}
 name:=`Local\Soulu.Session.`+profileKey(profile)+"."+hex.EncodeToString(nonce);wide,_:=syscall.UTF16PtrFromString(name)
 h,_,e:=kernelSession.NewProc("CreateJobObjectW").Call(0,uintptr(unsafe.Pointer(wide)));if h==0{return nil,e}
 j:=&sessionJob{handle:syscall.Handle(h),name:name};limits:=jobLimits{};limits.Basic.Flags=0x2000 // KILL_ON_JOB_CLOSE, no sandbox/resource restrictions.
 ok,_,e:=kernelSession.NewProc("SetInformationJobObject").Call(h,9,uintptr(unsafe.Pointer(&limits)),unsafe.Sizeof(limits));if ok==0{j.Close();return nil,e}
 return j,nil
}
func(j *sessionJob)Close(){syscall.CloseHandle(j.handle)}
func(j *sessionJob)Assign(pid int)error{
 p,e:=syscall.OpenProcess(0x0100|0x0001,false,uint32(pid));if e!=nil{return e};defer syscall.CloseHandle(p)
 ok,_,e:=kernelSession.NewProc("AssignProcessToJobObject").Call(uintptr(j.handle),uintptr(p));if ok==0{return e};return nil
}
func(j *sessionJob)windows()[]uintptr{
 j.mu.Lock();defer j.mu.Unlock();j.found=nil
 if j.callback==0{j.callback=syscall.NewCallback(func(hwnd,unused uintptr)uintptr{
  visible,_,_:=userSession.NewProc("IsWindowVisible").Call(hwnd);if visible==0{return 1}
  var pid uint32;userSession.NewProc("GetWindowThreadProcessId").Call(hwnd,uintptr(unsafe.Pointer(&pid)))
  process,e:=syscall.OpenProcess(0x1000,false,pid);if e!=nil{return 1}
  var member int32;kernelSession.NewProc("IsProcessInJob").Call(uintptr(process),uintptr(j.handle),uintptr(unsafe.Pointer(&member)));syscall.CloseHandle(process)
  if member!=0{j.found=append(j.found,hwnd)};return 1
 })}
 userSession.NewProc("EnumWindows").Call(j.callback,0);return append([]uintptr(nil),j.found...)
}
func(j *sessionJob)watch(done <-chan struct{},grace time.Duration,record func(string)){
 seen:=false;last:=time.Now();tick:=time.NewTicker(200*time.Millisecond);defer tick.Stop()
 for{select{case <-done:return;case <-tick.C:
  wins:=j.windows()
  if len(wins)>0{
   if !seen{for _,hwnd:=range wins{if sessionWindowReady(hwnd){record("visible");seen=true;break}}}
   last=time.Now();continue
  }
  // Never interrupt initial startup, a minimized window, or any visible dialog.
  // Only this launcher-owned process group is eligible after its UI was closed.
  if seen&&time.Since(last)>grace{record("recover-closed-session");kernelSession.NewProc("TerminateJobObject").Call(uintptr(j.handle),0);return}
 }}
}
func writeSessionRecord(profile string,j *sessionJob)error{data,e:=json.Marshal(sessionRecord{os.Getpid(),j.name});if e!=nil{return e};return os.WriteFile(filepath.Join(profile,"soulu-session.json"),data,0600)}
func imagePath(pid int)string{
 p,e:=syscall.OpenProcess(0x1000,false,uint32(pid));if e!=nil{return ""};defer syscall.CloseHandle(p)
 buffer:=make([]uint16,32768);length:=uint32(len(buffer));ok,_,_:=kernelSession.NewProc("QueryFullProcessImageNameW").Call(uintptr(p),0,uintptr(unsafe.Pointer(&buffer[0])),uintptr(unsafe.Pointer(&length)));if ok==0{return ""};return syscall.UTF16ToString(buffer[:length])
}
// A loopback firewall must not prevent an ordinary shortcut from activating an
// already visible window. Verify both the owning launcher and profile-scoped job.
func activateSession(profile,exe string)bool{
 data,e:=os.ReadFile(filepath.Join(profile,"soulu-session.json"));if e!=nil||len(data)>2048{return false}
 var info sessionRecord;if json.Unmarshal(data,&info)!=nil||info.Leader<1||!strings.HasPrefix(info.Job,`Local\Soulu.Session.`+profileKey(profile)+"."){return false}
 if !sameSessionExecutable(imagePath(info.Leader),exe){return false}
 wide,_:=syscall.UTF16PtrFromString(info.Job);h,_,_:=kernelSession.NewProc("OpenJobObjectW").Call(4,0,uintptr(unsafe.Pointer(wide)));if h==0{return false};j:=&sessionJob{handle:syscall.Handle(h),name:info.Job};defer j.Close()
 wins:=j.windows();if len(wins)==0{return false};hwnd:=wins[0]
 userSession.NewProc("ShowWindowAsync").Call(hwnd,9);userSession.NewProc("SetForegroundWindow").Call(hwnd);return true
}

func(j *sessionJob)active()(uint32,error){
 var accounting struct{Times [4]int64;Faults,Total,Active,Terminated uint32}
 ok,_,e:=kernelSession.NewProc("QueryInformationJobObject").Call(uintptr(j.handle),1,uintptr(unsafe.Pointer(&accounting)),unsafe.Sizeof(accounting),0)
 if ok==0{return 0,e};return accounting.Active,nil
}

func sessionWindowReady(hwnd uintptr)bool{
 style,_,_:=userSession.NewProc("GetWindowLongW").Call(hwnd,uintptr(^uint32(19)))
 if uint32(style)&0x80!=0{return false}
 title:=make([]uint16,1024);userSession.NewProc("GetWindowTextW").Call(hwnd,uintptr(unsafe.Pointer(&title[0])),uintptr(len(title)))
 return strings.Contains(syscall.UTF16ToString(title),"Soulu")
}

func sameSessionExecutable(a,b string)bool{
 if strings.EqualFold(filepath.Clean(a),filepath.Clean(b)){return true}
 left,e:=os.Stat(a);if e!=nil{return false};right,e:=os.Stat(b);return e==nil&&os.SameFile(left,right)
}
