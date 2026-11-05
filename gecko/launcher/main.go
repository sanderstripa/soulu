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
func fail(s string){p,_:=syscall.UTF16PtrFromString(s);t,_:=syscall.UTF16PtrFromString("Soul 0.12.0 Preview");syscall.NewLazyDLL("user32.dll").NewProc("MessageBoxW").Call(0,uintptr(unsafe.Pointer(p)),uintptr(unsafe.Pointer(t)),16);os.Exit(1)}
func hidden(cmd *exec.Cmd) *exec.Cmd {cmd.SysProcAttr=&syscall.SysProcAttr{HideWindow:true};return cmd}
func webURL(s string)bool{u,e:=url.Parse(s);return len(s)<=8192&&e==nil&&(u.Scheme=="http"||u.Scheme=="https")&&u.Host!=""&&u.User==nil}
func register(exe,id string)error{
 root:=`HKCU\Software\Clients\StartMenuInternet\Soul`;cap:=root+`\Capabilities`
 command:=`"`+exe+`" --url "%1"`;if id!="default"{command=`"`+exe+`" --profile "`+id+`" --url "%1"`}
 entries:=[][3]string{{root,"","Soul"},{root+`\DefaultIcon`,"",exe+",0"},{root+`\shell\open\command`,"",`"`+exe+`"`},{cap,"ApplicationName","Soul"},{cap,"ApplicationDescription","Soulu browser"},{cap,"ApplicationIcon",exe+",0"},{cap+`\URLAssociations`,"http","Soul.URL"},{cap+`\URLAssociations`,"https","Soul.URL"},{`HKCU\Software\RegisteredApplications`,"Soul",`Software\Clients\StartMenuInternet\Soul\Capabilities`},{`HKCU\Software\Classes\Soul.URL`,"","Soul URL"},{`HKCU\Software\Classes\Soul.URL`,"URL Protocol",""},{`HKCU\Software\Classes\Soul.URL\DefaultIcon`,"",exe+",0"},{`HKCU\Software\Classes\Soul.URL\shell\open\command`,"",command}}
 for _,v:=range entries{args:=[]string{"add",v[0],"/t","REG_SZ","/d",v[2],"/f"};if v[1]==""{args=append(args,"/ve")}else{args=append(args,"/v",v[1])};if e:=hidden(exec.Command("reg.exe",args...)).Run();e!=nil{return e}}
 // Windows retains control of the protected UserChoice associations.
 return hidden(exec.Command("rundll32.exe","url.dll,FileProtocolHandler","ms-settings:defaultapps?registeredAppUser=Soul")).Start()
}
func forward(profile,address string,private bool)bool{
 data,e:=os.ReadFile(filepath.Join(profile,"soulu-remote.json"));if e!=nil||len(data)>1024{return false}
 var info struct{Port int `json:"port"`;Token string `json:"token"`};if json.Unmarshal(data,&info)!=nil||info.Port<1||info.Port>65535||len(info.Token)!=64{return false}
 c,e:=net.DialTimeout("tcp",fmt.Sprintf("127.0.0.1:%d",info.Port),time.Second);if e!=nil{return false};defer c.Close();c.SetDeadline(time.Now().Add(2*time.Second));json.NewEncoder(c).Encode(map[string]any{"token":info.Token,"url":address,"private":private});line,e:=bufio.NewReader(io.LimitReader(c,1024)).ReadString('\n');return e==nil&&strings.TrimSpace(line)=="ok"
}
func main(){exe,e:=os.Executable();if e!=nil{fail(e.Error())};base:=filepath.Dir(exe);args:=os.Args[1:];if len(args)>0&&args[0]=="--register-default"{id:="default";if len(args)==3&&args[1]=="--profile"{id=args[2]}else if len(args)!=1{fail("Invalid registration arguments")};if !regexp.MustCompile(`^[a-zA-Z0-9_-]{1,64}$`).MatchString(id){fail("Invalid profile identifier")};if e=register(exe,id);e!=nil{fail(e.Error())};return}
 id:="default";if len(args)>=2&&args[0]=="--profile"{id=args[1];args=args[2:]}
 if !regexp.MustCompile(`^[a-zA-Z0-9_-]{1,64}$`).MatchString(id){fail("Invalid profile identifier")};root:=os.Getenv("LOCALAPPDATA");if root==""{fail("LOCALAPPDATA is unavailable")};profile:=filepath.Join(root,"Soul","Profiles",id);if e=os.MkdirAll(profile,0700);e!=nil{fail(e.Error())}
 // Invalidate only compiled application resources when this build changes.
 identity,_:=os.ReadFile(filepath.Join(base,"BUILD.json"));signature:=sha256.Sum256(identity);stamp:=hex.EncodeToString(signature[:]);stampFile:=filepath.Join(profile,"soul-build-stamp");previous,_:=os.ReadFile(stampFile);if string(previous)!=stamp{os.RemoveAll(filepath.Join(profile,"startupCache"));os.WriteFile(stampFile,[]byte(stamp),0600)}
 private:=len(args)>0&&args[0]=="--private";address:="";if len(args)>0&&args[0]=="--url"{if len(args)!=2{fail("Invalid external URL arguments")};address=args[1];if !webURL(address){fail("Only HTTP and HTTPS links are supported")};args=[]string{address}}
 if (address!=""||len(args)==0||private)&&forward(profile,address,private){return}
 sum:=sha256.Sum256([]byte(strings.ToLower(profile)));name,_:=syscall.UTF16PtrFromString(`Local\Soul.`+hex.EncodeToString(sum[:16]));h,_,last:=syscall.NewLazyDLL("kernel32.dll").NewProc("CreateMutexW").Call(0,0,uintptr(unsafe.Pointer(name)));if h==0{fail("Cannot create the profile session lock")};defer syscall.CloseHandle(syscall.Handle(h))
 // Native remoting never crosses profile or installed-Firefox boundaries.
 if last==syscall.Errno(183){for i:=0;i<100;i++{if forward(profile,address,private){return};time.Sleep(100*time.Millisecond)};fail("The profile is starting or busy. Try again shortly.")}
 // An explicit initial window prevents the native default-startup handler from
 // opening an additional window while the application home is being restored.
 if len(args)==0{var saved struct{Settings struct{StartupMode string `json:"startupMode"`;StartupURL string `json:"startupUrl"`} `json:"settings"`};if data,err:=os.ReadFile(filepath.Join(profile,"soulu-settings.json"));err==nil{_ = json.Unmarshal(data,&saved)};if saved.Settings.StartupMode!="continue"{home:=(&url.URL{Scheme:"file",Path:"/"+filepath.ToSlash(filepath.Join(base,"engine","soulu","chrome","ui","home.html"))}).String();if saved.Settings.StartupMode=="blank"{home="about:blank"};if saved.Settings.StartupMode=="custom"&&webURL(saved.Settings.StartupURL){home=saved.Settings.StartupURL};args=[]string{"-new-window",home}}}
 if len(args)>0&&args[0]=="--private"{args=append([]string{"-private-window"},args[1:]...)}
 cmd:=exec.Command(filepath.Join(base,"engine","SoulEngine.exe"),append([]string{"-app",filepath.Join(base,"engine","browser","application.ini"),"-no-remote","-profile",profile},args...)...);cmd.Dir=base;if e=cmd.Start();e!=nil{fail(e.Error())};cmd.Wait()
}

