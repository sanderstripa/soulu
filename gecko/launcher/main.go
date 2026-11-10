// Portable Soulu launcher. Registration is per-user and only on explicit request.
package main
import (
 "bufio"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "io"
 "net"
 "net/url"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "strings"
 "syscall"
 "time"
 "unsafe"
)
func fail(s string){p,_:=syscall.UTF16PtrFromString(s);t,_:=syscall.UTF16PtrFromString("Soulu Preview 1.160.22");syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(0,uintptr(unsafe.Pointer(p)),uintptr(unsafe.Pointer(t)),16);os.Exit(1)}
func hidden(cmd *exec.Cmd) *exec.Cmd {cmd.SysProcAttr=&syscall.SysProcAttr{HideWindow:true};return cmd}
func webURL(s string)bool{u,e:=url.Parse(s);return len(s)<=8192&&e==nil&&(u.Scheme=="http"||u.Scheme=="https")&&u.Host!=""&&u.User==nil}
func register(exe,id string)error{
 root:=`HKCU\Software\Clients\StartMenuInternet\Soulu`;cap:=root+`\Capabilities`
 command:=`"`+exe+`" --url "%1"`;if id!="default"{command=`"`+exe+`" --profile "`+id+`" --url "%1"`}
 entries:=[][3]string{{root,"","Soulu"},{root+`\DefaultIcon`,"",exe+",0"},{root+`\shell\open\command`,"",`"`+exe+`"`},{cap,"ApplicationName","Soulu"},{cap,"ApplicationDescription","Soulu browser"},{cap,"ApplicationIcon",exe+",0"},{cap+`\URLAssociations`,"http","Soulu.URL"},{cap+`\URLAssociations`,"https","Soulu.URL"},{`HKCU\Software\RegisteredApplications`,"Soulu",`Software\Clients\StartMenuInternet\Soulu\Capabilities`},{`HKCU\Software\Classes\Soulu.URL`,"","Soulu URL"},{`HKCU\Software\Classes\Soulu.URL`,"URL Protocol",""},{`HKCU\Software\Classes\Soulu.URL\DefaultIcon`,"",exe+",0"},{`HKCU\Software\Classes\Soulu.URL\shell\open\command`,"",command}}
 for _,v:=range entries{args:=[]string{"add",v[0],"/t","REG_SZ","/d",v[2],"/f"};if v[1]==""{args=append(args,"/ve")}else{args=append(args,"/v",v[1])};if e:=hidden(exec.Command("reg.exe",args...)).Run();e!=nil{return e}}
 // Windows retains control of the protected UserChoice associations.
 return hidden(exec.Command("rundll32.exe","url.dll,FileProtocolHandler","ms-settings:defaultapps?registeredAppUser=Soulu")).Start()
}
func forward(profile,engine,address string,private bool)bool{
 data,e:=os.ReadFile(filepath.Join(profile,"soulu-remote.json"));if e!=nil||len(data)>1024{return false}
 var info struct{PID int `json:"pid"`;Port int `json:"port"`;Token string `json:"token"`};if json.Unmarshal(data,&info)!=nil||info.Port<1||info.Port>65535||len(info.Token)!=64{return false}
 c,e:=net.DialTimeout("tcp",fmt.Sprintf("127.0.0.1:%d",info.Port),250*time.Millisecond);if e!=nil{return false};defer c.Close();if info.PID>0&&sameSessionExecutable(imagePath(info.PID),engine){userSession.NewProc("AllowSetForegroundWindow").Call(uintptr(info.PID))};c.SetDeadline(time.Now().Add(500*time.Millisecond));json.NewEncoder(c).Encode(map[string]any{"token":info.Token,"url":address,"private":private});line,e:=bufio.NewReader(io.LimitReader(c,1024)).ReadString('\n');return e==nil&&strings.TrimSpace(line)=="ok"
}
func main(){exe,e:=os.Executable();if e!=nil{fail(e.Error())};base:=filepath.Dir(exe);args:=os.Args[1:];if len(args)>0&&args[0]=="--register-default"{id:="default";if len(args)==3&&args[1]=="--profile"{id=args[2]}else if len(args)!=1{fail("Invalid registration arguments")};if !regexp.MustCompile(`^[a-zA-Z0-9_-]{1,64}$`).MatchString(id){fail("Invalid profile identifier")};if e=register(exe,id);e!=nil{fail(e.Error())};return}
 id:="default";if len(args)>=2&&args[0]=="--profile"{id=args[1];args=args[2:]}
 if !regexp.MustCompile(`^[a-zA-Z0-9_-]{1,64}$`).MatchString(id){fail("Invalid profile identifier")};root:=os.Getenv("LOCALAPPDATA");if root==""{fail("LOCALAPPDATA is unavailable")};profile:=filepath.Join(root,"Soulu","Profiles",id);if e=os.MkdirAll(profile,0700);e!=nil{fail(e.Error())}

 private:=len(args)>0&&args[0]=="--private";address:="";if len(args)>0&&args[0]=="--url"{if len(args)!=2{fail("Invalid external URL arguments")};address=args[1];if !webURL(address){fail("Only HTTP and HTTPS links are supported")};args=[]string{address}}
 sessionLog(profile,"request")
 tryForward:=func()bool{
  if address==""&&!private&&len(args)==0&&activateSession(profile,exe){sessionLog(profile,"activated-native-window");return true}
  if (address!=""||len(args)==0||private)&&forward(profile,filepath.Join(base,"engine","SouluEngine.exe"),address,private){sessionLog(profile,"forwarded");return true}
  return false
 }
 if tryForward(){return}
 guard,forwarded,lockErr:=acquireSession(profile,tryForward,45*time.Second);if lockErr!=nil{sessionLog(profile,"session-wait-failed");fail(lockErr.Error())};if forwarded{return};defer guard.Close()
 // The preceding launcher may have exited before native remoting stopped.
 if tryForward(){return}
 sessionLog(profile,"acquired")
 // Invalidate only compiled application resources when this build changes.
 identity,_:=os.ReadFile(filepath.Join(base,"BUILD.json"));signature:=sha256.Sum256(identity);stamp:=hex.EncodeToString(signature[:]);stampFile:=filepath.Join(profile,"soulu-build-stamp");previous,_:=os.ReadFile(stampFile);if string(previous)!=stamp{os.RemoveAll(filepath.Join(profile,"startupCache"));os.WriteFile(stampFile,[]byte(stamp),0600)}
 // An explicit initial window prevents the native default-startup handler from
 // opening an additional window while the application home is being restored.
 var saved struct{Settings struct{StartupMode string `json:"startupMode"`;StartupURL string `json:"startupUrl"`} `json:"settings"`};if data,err:=os.ReadFile(filepath.Join(profile,"soulu-settings.json"));err==nil{_ = json.Unmarshal(data,&saved)}
 // Apply startup policy before SessionStore reads the profile, not after XUL loads.
 userFile:=filepath.Join(profile,"user.js");userData,readErr:=os.ReadFile(userFile);if readErr!=nil&&!os.IsNotExist(readErr){fail(readErr.Error())};policy:=regexp.MustCompile(`(?s)\n?// Soulu startup policy begin\n.*?// Soulu startup policy end\n?`);userData=policy.ReplaceAll(userData,nil);page:=1;restore:=false;if saved.Settings.StartupMode=="continue"{page=3;restore=true};block:=fmt.Sprintf("\n// Soulu startup policy begin\nuser_pref(\"browser.startup.page\",%d);\nuser_pref(\"browser.sessionstore.resume_from_crash\",%t);\nuser_pref(\"browser.sessionstore.resume_session_once\",false);\n// Soulu startup policy end\n",page,restore);if e=os.WriteFile(userFile,append(userData,[]byte(block)...),0600);e!=nil{fail(e.Error())}
 if len(args)==0{if saved.Settings.StartupMode!="continue"{home:=(&url.URL{Scheme:"file",Path:"/"+filepath.ToSlash(filepath.Join(base,"engine","soulu","chrome","ui","home.html"))}).String();if saved.Settings.StartupMode=="blank"{home="about:blank"};if saved.Settings.StartupMode=="custom"&&webURL(saved.Settings.StartupURL){home=saved.Settings.StartupURL};args=[]string{"-new-window",home}}}
 if len(args)>0&&args[0]=="--private"{args=append([]string{"-private-window"},args[1:]...)}
 cmd:=exec.Command(filepath.Join(base,"engine","SouluEngine.exe"),append([]string{"-app",filepath.Join(base,"engine","browser","application.ini"),"-no-remote","-profile",profile},args...)...);cmd.Dir=base;cmd.SysProcAttr=&syscall.SysProcAttr{HideWindow:true}
 job,jobErr:=newSessionJob(profile);if jobErr!=nil{fail(jobErr.Error())};defer job.Close()
 if e=cmd.Start();e!=nil{fail(e.Error())}
 userSession.NewProc("AllowSetForegroundWindow").Call(uintptr(cmd.Process.Pid))
 if e=job.Assign(cmd.Process.Pid);e!=nil{_ = cmd.Process.Kill();_ = cmd.Wait();fail(e.Error())}
 if e=writeSessionRecord(profile,job);e!=nil{kernelSession.NewProc("TerminateJobObject").Call(uintptr(job.handle),0);_ = cmd.Wait();fail(e.Error())}
 sessionLog(profile,fmt.Sprintf("engine-start pid=%d",cmd.Process.Pid))
 done:=make(chan struct{});go job.watch(done,8*time.Second,func(stage string){sessionLog(profile,stage)})
 rootDone:=make(chan struct{});go func(){_ = cmd.Wait();close(rootDone)}()
 for{active,queryErr:=job.active();if queryErr!=nil{sessionLog(profile,"job-query-failed");kernelSession.NewProc("TerminateJobObject").Call(uintptr(job.handle),0);break};if active==0{break};time.Sleep(100*time.Millisecond)}
 close(done);<-rootDone;sessionLog(profile,"engine-exit")
}

