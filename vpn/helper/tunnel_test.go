package main
import("bufio";"encoding/base64";"encoding/binary";"encoding/json";"fmt";"io";"net";"net/http";"net/http/httptest";"os";"os/exec";"path/filepath";"strconv";"strings";"testing";"time")
func freePort(t *testing.T)int{l,e:=net.Listen("tcp","127.0.0.1:0");if e!=nil{t.Fatal(e)};port:=l.Addr().(*net.TCPAddr).Port;l.Close();return port}
func TestBundledCoresSOCKSTunnel(t *testing.T){
 base:=os.Getenv("SOULU_VPN_FIXTURE_BIN");if base==""{t.Skip("verified bundled cores supplied by the Windows packaging step")}
 oldBase:=packageBase;packageBase=base;defer func(){packageBase=oldBase}();t.Setenv("LOCALAPPDATA",t.TempDir())
 target:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){fmt.Fprint(w,"soulu-tunnel-fixture")}));defer target.Close();_,rawPort,_:=net.SplitHostPort(strings.TrimPrefix(target.URL,"http://"));destination,_:=strconv.Atoi(rawPort)
 for _,engine:=range []string{"xray","sudoku"}{t.Run(engine,func(t *testing.T){
  defer disconnect();port:=freePort(t);id:="12345678-1234-1234-1234-123456789abc";key:=strings.Repeat("ab",32);var cfg object;var link string
  if engine=="xray"{cfg=object{"log":object{"loglevel":"warning"},"inbounds":[]any{object{"listen":"127.0.0.1","port":port,"protocol":"vless","settings":object{"clients":[]any{object{"id":id}},"decryption":"none"}}},"outbounds":[]any{object{"protocol":"freedom"}}};link=fmt.Sprintf("vless://%s@127.0.0.1:%d?security=none&type=tcp",id,port)
  }else{cfg=object{"mode":"server","transport":"tcp","local_port":port,"key":key,"aead":"none","padding_min":5,"padding_max":15,"ascii":"prefer_entropy","enable_pure_downlink":true,"suspicious_action":"silent","httpmask":object{"disable":true},"rule_urls":[]string{"global"}};raw,_:=json.Marshal(object{"h":"127.0.0.1","p":port,"k":key,"e":"none","hd":true});link="sudoku://"+base64.RawURLEncoding.EncodeToString(raw)}
  dir:=t.TempDir();path:=filepath.Join(dir,"server.json");raw,_:=json.Marshal(cfg);os.WriteFile(path,raw,0600);args:=[]string{"run","-config",path};if engine=="sudoku"{args=[]string{"-c",path}}
  cmd:=exec.Command(filepath.Join(base,engine,engine+".exe"),args...);hideProcess(cmd);logPath:=filepath.Join(dir,"server.log");log,e:=os.Create(logPath);if e!=nil{t.Fatal(e)};cmd.Stdout=log;cmd.Stderr=log;if e=cmd.Start();e!=nil{t.Fatal(e)};defer func(){cmd.Process.Kill();cmd.Wait();log.Close();if t.Failed(){b,_:=os.ReadFile(logPath);t.Log(string(b));b,_=os.ReadFile(filepath.Join(rootDir(),"engine.log"));t.Log(string(b))}}()
  ready:=false;for deadline:=time.Now().Add(8*time.Second);time.Now().Before(deadline);{c,e:=net.DialTimeout("tcp",fmt.Sprintf("127.0.0.1:%d",port),100*time.Millisecond);if e==nil{c.Close();ready=true;break};time.Sleep(100*time.Millisecond)};if !ready{t.Fatal("fixture server did not listen")}
  if _,e=connect(object{"url":link,"profileId":engine});e!=nil{t.Fatal(e)}
  c,e:=net.DialTimeout("tcp","127.0.0.1:17890",time.Second);if e!=nil{t.Fatal(e)};defer c.Close();c.SetDeadline(time.Now().Add(20*time.Second));c.Write([]byte{5,1,0});reply:=make([]byte,2);if _,e=io.ReadFull(c,reply);e!=nil||reply[1]!=0{t.Fatal("SOCKS auth",e)}
  request:=[]byte{5,1,0,1,127,0,0,1,0,0};binary.BigEndian.PutUint16(request[8:],uint16(destination));c.Write(request);head:=make([]byte,4);if _,e=io.ReadFull(c,head);e!=nil||head[1]!=0{t.Fatal("SOCKS connect",head,e)}
  n:=0;switch head[3]{case 1:n=4;case 4:n=16;case 3:b:=make([]byte,1);io.ReadFull(c,b);n=int(b[0]);default:t.Fatal("SOCKS address type")};io.CopyN(io.Discard,c,int64(n+2))
  fmt.Fprintf(c,"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n");response,e:=http.ReadResponse(bufio.NewReader(c),nil);if e!=nil{t.Fatal(e)};body,e:=io.ReadAll(response.Body);response.Body.Close();if e!=nil||string(body)!="soulu-tunnel-fixture"{t.Fatal("real core round-trip failed",e,string(body))}
  t.Log("verified actual",engine,"client/server SOCKS tunnel");disconnect();if connected(){t.Fatal("VPN process retained after disconnect")}
 })}
}
