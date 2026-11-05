//go:build windows
package main
import("os";"os/exec";"path/filepath";"syscall";"testing";"time";"unsafe")
func TestExistingUnownedMutexDoesNotBlockRestart(t *testing.T){
 profile:=t.TempDir();name,_:=syscall.UTF16PtrFromString(sessionMutexName(profile));h,_,e:=kernelSession.NewProc("CreateMutexW").Call(0,0,uintptr(unsafe.Pointer(name)));if h==0{t.Fatal(e)};defer syscall.CloseHandle(syscall.Handle(h))
 guard,forwarded,e:=acquireSession(profile,func()bool{return false},time.Second);if e!=nil||forwarded{t.Fatal(e,forwarded)};guard.Close()
}
func TestWaiterAcquiresOwnershipWhileObjectRemainsAlive(t *testing.T){
 profile:=t.TempDir();owner,_,e:=acquireSession(profile,func()bool{return false},time.Second);if e!=nil{t.Fatal(e)}
 acquired:=make(chan error,1);go func(){g,f,e:=acquireSession(profile,func()bool{return false},3*time.Second);if e==nil&&!f{g.Close()};acquired<-e}()
 time.Sleep(150*time.Millisecond);select{case <-acquired:t.Fatal("waiter bypassed owner");default:}
 owner.Close();if e=<-acquired;e!=nil{t.Fatal(e)}
}
func TestProfilesHaveIndependentSessionLocks(t *testing.T){
 a,_,e:=acquireSession(filepath.Join(t.TempDir(),"a"),func()bool{return false},time.Second);if e!=nil{t.Fatal(e)};defer a.Close()
 b,_,e:=acquireSession(filepath.Join(t.TempDir(),"b"),func()bool{return false},time.Second);if e!=nil{t.Fatal(e)};b.Close()
}
func TestClosedHungSessionIsRecoveredWithoutKillingVisibleWindows(t *testing.T){
 profile:=t.TempDir();job,e:=newSessionJob(profile);if e!=nil{t.Fatal(e)};defer job.Close()
 command:=`Add-Type -AssemblyName System.Windows.Forms;$f=New-Object System.Windows.Forms.Form;$f.Text='Soulu session test';[void]$f.ShowDialog();Start-Sleep -Seconds 300`
 cmd:=exec.Command("powershell.exe","-NoProfile","-Command",command);cmd.SysProcAttr=&syscall.SysProcAttr{CreationFlags:0x08000000};if e=cmd.Start();e!=nil{t.Fatal(e)}
 if e=job.Assign(cmd.Process.Pid);e!=nil{cmd.Process.Kill();cmd.Wait();t.Fatal(e)}
 done:=make(chan struct{});go func(){cmd.Wait();close(done)}()
 events:=make(chan string,10);go job.watch(done,400*time.Millisecond,func(s string){events<-s})
 select{case stage:=<-events:if stage!="visible"{t.Fatal(stage)};case <-time.After(20*time.Second):active,err:=job.active();t.Fatalf("test window was not visible: active=%d err=%v windows=%v",active,err,job.windows())}
 time.Sleep(900*time.Millisecond);select{case <-done:t.Fatal("visible window was terminated");default:}
 if e=writeSessionRecord(profile,job);e!=nil{t.Fatal(e)};exe,_:=os.Executable();if !activateSession(profile,exe){t.Fatal("native focus fallback failed")}
 other:=t.TempDir();data,_:=os.ReadFile(filepath.Join(profile,"soulu-session.json"));os.WriteFile(filepath.Join(other,"soulu-session.json"),data,0600);if activateSession(other,exe){t.Fatal("another profile was activated")}
 for _,hwnd:=range job.windows(){userSession.NewProc("PostMessageW").Call(hwnd,0x10,0,0)}
 select{case <-done:case <-time.After(10*time.Second):t.Fatal("closed hung session was not recovered")}
 select{case stage:=<-events:if stage!="recover-closed-session"{t.Fatal(stage)};case <-time.After(time.Second):t.Fatal("recovery not recorded")}
}
