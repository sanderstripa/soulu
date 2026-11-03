"""Executed inside preview4.py's real Windows browser acceptance scope."""
import base64 as b64,psutil,winreg,hashlib

def system_proxy_digest():
 values=[]
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
  for name in ['ProxyEnable','ProxyServer','AutoConfigURL','ProxyOverride']:
   try:values.append((name,winreg.QueryValueEx(key,name)[0]))
   except FileNotFoundError:values.append((name,None))
 return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()
proxy_before=system_proxy_digest();settings_before=call('settings.begin');rtc_before=chrome('return Services.prefs.getBoolPref("media.peerconnection.enabled")');trr_before=chrome('return Services.prefs.getIntPref("network.trr.mode",0)')
chrome('Services.prefs.setBoolPref("network.proxy.allow_hijacking_localhost",true)')
for engine in ['xray','sudoku']:
 with socket.socket() as listener:listener.bind(('127.0.0.1',0));server_port=listener.getsockname()[1]
 uuid='12345678-1234-1234-1234-123456789abc'
 if engine=='xray':
  cfg={'log':{'loglevel':'warning'},'inbounds':[{'listen':'127.0.0.1','port':server_port,'protocol':'vless','settings':{'clients':[{'id':uuid}],'decryption':'none'}}],'outbounds':[{'protocol':'freedom','settings':{'finalRules':[{'action':'allow','ip':['127.0.0.1/32']}]}}]}
  link=f'vless://{uuid}@127.0.0.1:{server_port}?security=none&type=tcp'
 else:
  key='ab'*32;cfg={'mode':'server','transport':'tcp','local_port':server_port,'key':key,'aead':'none','padding_min':5,'padding_max':15,'ascii':'prefer_entropy','enable_pure_downlink':True,'suspicious_action':'silent','httpmask':{'disable':True},'rule_urls':['global']}
  link='sudoku://'+b64.urlsafe_b64encode(json.dumps({'h':'127.0.0.1','p':server_port,'k':key,'e':'none','hd':True}).encode()).decode().rstrip('=')
 path=root/(engine+'-server.json');path.write_text(json.dumps(cfg),encoding='utf-8');engine_log=open(out/(engine+'-server.log'),'w');exe=binary.parent/'soulu/vpn'/engine/(engine+'.exe');command=[str(exe),*(['run','-config',str(path)] if engine=='xray' else ['-c',str(path)])];core=subprocess.Popen(command,stdout=engine_log,stderr=engine_log)
 try:
  def listening():
   try:
    with socket.create_connection(('127.0.0.1',server_port),timeout=.2):return True
   except OSError:return False
  wait(listening,15)
  config=call('settings.begin');config['vpn']['profiles']=[{'id':engine,'name':'Local real-core fixture','link':link}];config['vpn']['defaultProfileId']=engine;config['vpn']['directDomains']='';assert call('settings.save',config)['ok']
  check(engine+'_connect_from_original_toolbar_bridge',ui('await vpn.send("connect");return (await vpn.send("status")).connected'))
  port=chrome('return Soulu.backend.shared.socksPort')
  check(engine+'_remote_dns_fail_closed_webrtc',chrome('return Services.prefs.getBoolPref("network.proxy.socks_remote_dns")&&!Services.prefs.getBoolPref("network.proxy.failover_direct")&&Services.prefs.getIntPref("network.proxy.type")===1&&!Services.prefs.getBoolPref("media.peerconnection.enabled")'))
  target=f'http://127.0.0.1:{server.server_port}/download-vpn-{engine}'
  info=run('let proxy=null;const observer={observe(channel){try{if(channel.QueryInterface(Ci.nsIHttpChannel).URI.spec==='+json.dumps(target)+'){const p=channel.QueryInterface(Ci.nsIProxiedChannel).proxyInfo;proxy=p?{type:p.type,host:p.host,port:p.port}:null;}}catch(e){proxy={error:String(e)};}};Services.obs.addObserver(observer,"http-on-examine-response");try{const response=await fetch('+json.dumps(target)+',{cache:"no-store",signal:AbortSignal.timeout(15000)});return {text:await response.text(),proxy};}finally{Services.obs.removeObserver(observer,"http-on-examine-response");}')
  check(engine+'_actual_gecko_socks_round_trip',info['text']=='soulu-download-fixture' and info['proxy'] and info['proxy'].get('port')==port,info)
  helper_pid=chrome('return Soulu.backend.shared.helper.pid');clients=[p for p in psutil.Process(helper_pid).children(recursive=True) if p.name().lower()==engine+'.exe'];assert len(clients)==1;clients[0].kill();clients[0].wait(10)
  status=call('vpn.send',{'action':'status'});check(engine+'_core_failure_reported',status['state']=='error' and not status['connected'])
  blocked=run('try{await fetch('+json.dumps(target+'-after-failure')+',{cache:"no-store",signal:AbortSignal.timeout(5000)});return false;}catch(e){return true;}')
  check(engine+'_no_silent_direct_fallback',blocked and chrome('return Services.prefs.getIntPref("network.proxy.type")===1'))
  call('vpn.send',{'action':'disconnect'})
  check(engine+'_disconnect_restores_network_preferences',chrome('return Services.prefs.getIntPref("network.proxy.type")===0&&Services.prefs.getBoolPref("media.peerconnection.enabled")==='+json.dumps(rtc_before)+'&&Services.prefs.getIntPref("network.trr.mode",0)==='+str(trr_before)))
 finally:
  try:call('vpn.send',{'action':'disconnect'})
  except Exception:pass
  core.terminate()
  try:core.wait(timeout=10)
  except subprocess.TimeoutExpired:core.kill();core.wait()
  engine_log.close()
call('settings.save',settings_before);chrome('Services.prefs.clearUserPref("network.proxy.allow_hijacking_localhost")')
check('windows_system_proxy_unchanged',system_proxy_digest()==proxy_before)
