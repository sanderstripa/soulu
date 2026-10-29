package main
import("encoding/base64";"encoding/hex";"encoding/json";"errors";"net";"net/url";"strconv";"strings")
func engineConfig(link string,port int)(object,string,error){if len(link)==0||len(link)>16384{return nil,"",errors.New("connection key is missing or too long")};if strings.HasPrefix(link,"sudoku://"){return sudokuConfig(link,port)};return xrayConfig(link,port)}
func xrayConfig(link string,local int)(object,string,error){
 u,e:=url.Parse(link);if e!=nil||u.Scheme!="vless"||u.User==nil||u.User.Username()==""||u.Hostname()==""{return nil,"",errors.New("a vless:// or sudoku:// connection key is required")};port,e:=strconv.Atoi(u.Port());if e!=nil||port<1||port>65535{return nil,"",errors.New("connection port must be 1–65535")}
 q:=u.Query();network:=q.Get("type");if network==""{network="tcp"};if network=="splithttp"{network="xhttp"};security:=q.Get("security");if security==""{security="none"};stream:=object{"network":network,"security":security};sni:=q.Get("sni");if sni==""{sni=u.Hostname()}
 switch security{case "none":case "tls":tls:=object{"serverName":sni,"allowInsecure":false};if fp:=q.Get("fp");fp!=""{tls["fingerprint"]=fp};if alpn:=q.Get("alpn");alpn!=""{tls["alpn"]=strings.Split(alpn,",")};stream["tlsSettings"]=tls
 case "reality":if q.Get("pbk")==""{return nil,"",errors.New("Reality public key is missing")};fp:=q.Get("fp");if fp==""{fp="chrome"};stream["realitySettings"]=object{"serverName":sni,"fingerprint":fp,"publicKey":q.Get("pbk"),"shortId":q.Get("sid"),"spiderX":q.Get("spx")}
 default:return nil,"",errors.New("unsupported VLESS security")}
 switch network{case "tcp","raw":case "xhttp":mode:=q.Get("mode");if mode==""{mode="auto"};settings:=object{"mode":mode,"host":q.Get("host"),"path":q.Get("path")};if raw:=q.Get("extra");raw!=""{var extra object;if json.Unmarshal([]byte(raw),&extra)!=nil{return nil,"",errors.New("invalid XHTTP extra JSON")};settings["extra"]=extra};stream["xhttpSettings"]=settings
 case "ws":stream["wsSettings"]=object{"path":q.Get("path"),"headers":object{"Host":q.Get("host")}}
 case "grpc":stream["grpcSettings"]=object{"serviceName":q.Get("serviceName"),"multiMode":q.Get("mode")=="multi"}
 default:return nil,"",errors.New("unsupported VLESS transport")}
 encryption:=q.Get("encryption");if encryption==""{encryption="none"};user:=object{"id":u.User.Username(),"encryption":encryption};if flow:=q.Get("flow");flow!=""{user["flow"]=flow}
 out:=object{"tag":"proxy","protocol":"vless","settings":object{"vnext":[]any{object{"address":u.Hostname(),"port":port,"users":[]any{user}}}},"streamSettings":stream}
 return object{"log":object{"loglevel":"warning"},"inbounds":[]any{object{"listen":"127.0.0.1","port":local,"protocol":"socks","settings":object{"auth":"noauth","udp":false}}},"outbounds":[]any{out}},"xray",nil
}
func sudokuConfig(link string,port int)(object,string,error){
 encoded:=strings.TrimPrefix(link,"sudoku://");var b []byte;var e error;for _,enc:=range []*base64.Encoding{base64.RawURLEncoding,base64.URLEncoding,base64.RawStdEncoding,base64.StdEncoding}{b,e=enc.DecodeString(encoded);if e==nil{break}};if e!=nil{return nil,"",errors.New("invalid Sudoku Base64 key")}
 var key object;if json.Unmarshal(b,&key)!=nil||str(key,"h")==""||number(key,"p")<1||number(key,"p")>65535||str(key,"k")==""{return nil,"",errors.New("Sudoku key must contain server, port and key")}
 host:=str(key,"h");if strings.ContainsAny(host,"/\\\x00\r\n")||len(host)>253{return nil,"",errors.New("invalid Sudoku host")};if _,e=hex.DecodeString(str(key,"k"));e!=nil{return nil,"",errors.New("invalid Sudoku private key")}
 ascii:=str(key,"a");if ascii==""||ascii=="entropy"{ascii="prefer_entropy"};if ascii=="ascii"{ascii="prefer_ascii"};aead:=str(key,"e");if aead==""{aead="none"}
 tables:=key["ts"];if tables==nil{tables=[]any{}}
 return object{"mode":"client","transport":"tcp","local_port":port,"server_address":net.JoinHostPort(host,strconv.Itoa(number(key,"p"))),"key":str(key,"k"),"aead":aead,"padding_min":5,"padding_max":15,"ascii":ascii,"enable_pure_downlink":!boolean(key,"x"),"custom_table":str(key,"t"),"custom_tables":tables,"proxy_mode":"global","rule_urls":[]string{"global"},"httpmask":object{"disable":boolean(key,"hd"),"mode":str(key,"hm"),"tls":boolean(key,"ht"),"host":str(key,"hh"),"multiplex":str(key,"hx"),"path_root":str(key,"hy")}},"sudoku",nil
}
