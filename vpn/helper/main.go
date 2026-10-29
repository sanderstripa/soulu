package main
import("crypto/sha256";"encoding/binary";"encoding/hex";"encoding/json";"errors";"fmt";"io";"net";"os";"os/exec";"path/filepath";"strings";"time")
type object map[string]any
func str(v object,k string)string{s,_:=v[k].(string);return s}
func boolean(v object,k string)bool{b,_:=v[k].(bool);return b}
func number(v object,k string)int{n,_:=v[k].(float64);return int(n)}
const proxyPort=17890
var running *exec.Cmd
var finished chan struct{}
var activeID,configFile string
var profiles=map[string]string{}
func rootDir()string{return filepath.Join(os.Getenv("LOCALAPPDATA"),"Soulu","VPN")}
var packageBase string
func packageDir()string{if packageBase!=""{return packageBase};exe,_:=os.Executable();return filepath.Dir(exe)}
func readMessage(r io.Reader)(object,error){var n uint32;var v object;if e:=binary.Read(r,binary.LittleEndian,&n);e!=nil{return v,e};if n==0||n>1048576{return v,errors.New("invalid native message length")};b:=make([]byte,n);if _,e:=io.ReadFull(r,b);e!=nil{return v,e};return v,json.Unmarshal(b,&v)}
func writeMessage(w io.Writer,v any)error{b,e:=json.Marshal(v);if e!=nil{return e};if e=binary.Write(w,binary.LittleEndian,uint32(len(b)));e!=nil{return e};_,e=w.Write(b);return e}
func connected()bool{if running==nil{return false};select{case <-finished:return false;default:return true}}
func disconnect(){if running!=nil&&connected(){running.Process.Kill();<-finished};running=nil;activeID="";if configFile!=""{os.Remove(configFile);configFile=""}}
func connect(r object)(object,error){
 link:=str(r,"url");if link==""{link=profiles[str(r,"profileId")]};cfg,engine,e:=engineConfig(link,proxyPort);if e!=nil{return nil,e};exe,e:=resolveEngine(engine);if e!=nil{return nil,e};disconnect()
 if prior,e:=net.DialTimeout("tcp",fmt.Sprintf("127.0.0.1:%d",proxyPort),200*time.Millisecond);e==nil{prior.Close();return nil,errors.New("another proxy already uses the local VPN port; disconnect it first")}
 if e=os.MkdirAll(rootDir(),0700);e!=nil{return nil,e};file,e:=os.CreateTemp(rootDir(),"connection-*.json");if e!=nil{return nil,e};configFile=file.Name();file.Chmod(0600);e=json.NewEncoder(file).Encode(cfg);file.Close();if e!=nil{return nil,e}
 args:=[]string{"run","-config",configFile};if engine=="sudoku"{args=[]string{"-c",configFile}};cmd:=exec.Command(exe,args...);hideProcess(cmd);cmd.Dir=filepath.Dir(exe)
 log,e:=os.OpenFile(filepath.Join(rootDir(),"engine.log"),os.O_CREATE|os.O_WRONLY|os.O_TRUNC,0600);if e!=nil{return nil,e};cmd.Stdout=log;cmd.Stderr=log;if e=cmd.Start();e!=nil{log.Close();return nil,e}
 running=cmd;finished=make(chan struct{});done:=finished;go func(){cmd.Wait();log.Close();close(done)}()
 deadline:=time.Now().Add(12*time.Second);for time.Now().Before(deadline){if !connected(){disconnect();return nil,errors.New("VPN core stopped before its SOCKS listener became ready")};c,err:=net.DialTimeout("tcp",fmt.Sprintf("127.0.0.1:%d",proxyPort),250*time.Millisecond);if err==nil{c.SetDeadline(time.Now().Add(time.Second));c.Write([]byte{5,1,0});b:=make([]byte,2);_,err=io.ReadFull(c,b);c.Close();if err==nil&&b[0]==5&&b[1]==0{activeID=str(r,"profileId");return object{"ok":true,"connected":true,"activeProfileId":activeID,"port":proxyPort},nil}};time.Sleep(100*time.Millisecond)}
 disconnect();return nil,errors.New("VPN SOCKS listener did not start")
}
func handle(r object)(object,error){switch str(r,"action"){
 case "status":return object{"ok":true,"connected":connected(),"activeProfileId":activeID,"port":proxyPort},nil
 case "disconnect":disconnect();return object{"ok":true,"connected":false},nil
 case "save_profile":if _,_,e:=engineConfig(str(r,"url"),proxyPort);e!=nil{return nil,e};id:=str(r,"id");if id==""{sum:=sha256.Sum256([]byte(str(r,"url")));id=hex.EncodeToString(sum[:8])};profiles[id]=str(r,"url");return object{"ok":true,"id":id,"profileId":id},nil
 case "connect":return connect(r)
 case "list_profiles":return object{"ok":true,"profiles":[]any{}},nil
 case "delete_profile":delete(profiles,str(r,"id"));if str(r,"id")==activeID{disconnect()};return object{"ok":true},nil
 case "components":return manageComponent(r)
 default:return nil,errors.New("unsupported VPN operation")
}}
func main(){if os.Getenv("LOCALAPPDATA")==""{fmt.Fprintln(os.Stderr,"LOCALAPPDATA is required");return};defer disconnect();for{r,e:=readMessage(os.Stdin);if e!=nil{return};v,e:=handle(r);if e!=nil{v=object{"ok":false,"error":e.Error()}};if e=writeMessage(os.Stdout,v);e!=nil{return};if len(os.Args)>1&&strings.EqualFold(os.Args[1],"--components"){return}}}
