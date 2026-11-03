/* Local microphone and Whisper inference, isolated helper; no audio upload. */
(()=>{
const {shared,save,PathUtils}=Soulu.backend,{Subprocess}=ChromeUtils.importESModule('resource://gre/modules/Subprocess.sys.mjs');
const base=Soulu.dispatch;
function cancel(){shared.speechJob?.kill();shared.speechJob=null;}
Soulu.dispatch=async(action,payload,source)=>{
 if(action==='home.voice.cancel'){cancel();return {status:'cancelled'};}
 if(action!=='home.voice')return base(action,payload,source);
 if(source?.appURI!==Soulu.native.homeURL||!source.gesture||Date.now()-source.gesture.at>2000)throw Error('Нажмите микрофон на домашней странице.');
 if(Services.appinfo.OS!=='WINNT')return {status:'unavailable'};
 const browser=gBrowser.selectedBrowser,uri=browser.currentURI.spec,generation=browser.browsingContext.currentWindowGlobal?.innerWindowId;
 if(uri!==Soulu.native.homeURL)throw Error('Откройте домашнюю страницу.');
 const rule=shared.config.rules.sites['soulu://home']??={};
 if(rule.microphone===2)return {status:'denied'};
 if(rule.microphone!==0){if(!Services.prompt.confirm(window,'Голосовой ввод Soulu','Разрешить запись микрофона для локального распознавания речи? Аудио обрабатывается Whisper на этом компьютере и никуда не отправляется.'))return {status:'denied'};rule.microphone=0;await save();}
 cancel();const command=PathUtils.join(Services.dirsvc.get('GreD',Ci.nsIFile).path,'soulu','speech','SouluSpeech.exe');
 const job=await Subprocess.call({command,arguments:[shared.config.settings.language==='en'?'en':'ru'],stdout:'pipe',stderr:'pipe'});shared.speechJob=job;
 const phase=(async()=>{while(true){const line=await job.stderr.readString();if(!line)break;try{browser.browsingContext.currentWindowGlobal?.getActor('SouluApp').sendAsyncMessage('emit',{name:'voicePhase',value:line.includes('processing')?'processing':'listening'});}catch{}}})();
 let text='';while(true){const chunk=await job.stdout.readString();if(!chunk)break;text+=chunk;if(text.length>8192){cancel();break;}}
 await job.wait();await phase.catch(()=>{});if(shared.speechJob!==job||gBrowser.selectedBrowser!==browser||browser.browsingContext.currentWindowGlobal?.innerWindowId!==generation)return {status:'cancelled'};
 shared.speechJob=null;const [status,...lines]=text.split('\n');return {status,text:status==='recognized'?lines.join('\n').trim():''};
};
gBrowser.tabContainer.addEventListener('TabSelect',cancel);gBrowser.addTabsProgressListener({onLocationChange(browser){if(browser===gBrowser.selectedBrowser)cancel();}});window.addEventListener('unload',cancel,{once:true});
})();
