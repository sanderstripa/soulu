"""Actual offline RU/EN Whisper inference using the same attributed CEF fixtures."""
import importlib.util,pathlib,subprocess,sys,tempfile,json,hashlib,urllib.request,time
import numpy as np,soundfile as sf
root=pathlib.Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('fixtures',root/'scripts/test-cef-home-speech.py');fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
exe=pathlib.Path(sys.argv[1]).resolve();report=pathlib.Path(sys.argv[2]);checks=[]
with tempfile.TemporaryDirectory(prefix='soulu-local-speech-') as tmp:
 for language,url,digest,expected in fixtures.FIXTURES:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SouluRegression/1.0'}),timeout=40) as r:data=r.read(2000000)
  assert hashlib.sha256(data).hexdigest()==digest;source=pathlib.Path(tmp)/('source-'+language);source.write_bytes(data);audio,rate=sf.read(source,dtype='float32',always_2d=True);audio=audio.mean(axis=1)
  if rate!=16000:audio=np.interp(np.arange(round(len(audio)*16000/rate))*rate/16000,np.arange(len(audio)),audio)
  pcm=pathlib.Path(tmp)/(language+'.pcm');pcm.write_bytes((np.clip(np.concatenate([audio,np.zeros(8000)]),-1,1)*32767).astype('<i2').tobytes());start=time.monotonic();p=subprocess.run([str(exe),language,'--pcm-test',str(pcm)],capture_output=True,timeout=100)
  text=p.stdout.decode('utf-8');assert p.returncode==0 and text.startswith('recognized\n') and expected in text.lower(),text;checks.append({'language':language,'text':text,'seconds':round(time.monotonic()-start,2),'fixtureSHA256':digest})
report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps({'passed':True,'checks':checks,'limitations':['Public speech proves real offline inference. Physical microphone capture, Windows microphone access and user acoustic conditions require manual testing.'],'attribution':['RU weather word: The Shtooka Project, Wikimedia Commons Ru-погода.ogg, CC BY 2.0 France','EN: US federal JFK speech, whisper.cpp samples/jfk.wav, public domain']},ensure_ascii=False,indent=2),encoding='utf-8')
print('Native offline RU/EN inference passed')
