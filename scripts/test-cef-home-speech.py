"""Real native Whisper inference on attributed public speech, never user recordings."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import numpy as np
import soundfile as sf

FIXTURES = [
 ('ru','https://upload.wikimedia.org/wikipedia/commons/3/32/Ru-%D0%BF%D0%BE%D0%B3%D0%BE%D0%B4%D0%B0.ogg','1d80d2ade8aaddef0aed7ba9824c7e5476e0c3923a42e79ebffd0364512336fb','погода'),
 ('en','https://raw.githubusercontent.com/ggml-org/whisper.cpp/4979e04f5dcaccb36057e059bbaed8a2f5288315/samples/jfk.wav','59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e','country'),
]

def main():
 exe=Path(sys.argv[1]).resolve();report=Path(sys.argv[2]).resolve();checks=[]
 with tempfile.TemporaryDirectory(prefix='soulu-speech-fixtures-') as root:
  folder=Path(root)
  for language,url,digest,expected in FIXTURES:
   req=urllib.request.Request(url,headers={'User-Agent':'SouluRegression/1.0'})
   local=os.environ.get('SOULU_SPEECH_FIXTURE_DIR')
   raw=(Path(local)/('ru-weather.ogg' if language=='ru' else 'jfk.wav')).read_bytes() if local else urllib.request.urlopen(req,timeout=30).read(2000000)
   assert hashlib.sha256(raw).hexdigest()==digest,'Public speech fixture integrity'
   source=folder/('source-'+language);source.write_bytes(raw)
   audio,rate=sf.read(source,dtype='float32',always_2d=True);audio=audio.mean(axis=1)
   if rate!=16000:audio=np.interp(np.arange(round(len(audio)*16000/rate))*rate/16000,np.arange(len(audio)),audio)
   audio=np.concatenate([audio,np.zeros(8000)])
   assert len(audio)<=320000
   pcm=folder/(language+'.pcm');pcm.write_bytes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes());text=folder/(language+'.txt')
   env=dict(os.environ,SOULU_UI_TEST_PORT='9223',LOCALAPPDATA=root,APPDATA=root)
   result=subprocess.run([str(exe),'--home-speech-test-file='+str(pcm),'--home-speech-test-language='+language,'--home-speech-test-report='+str(text)],env=env,timeout=120)
   assert result.returncode==0,'Native '+language+' inference failed'
   recognized=text.read_text(encoding='utf-8').strip();assert expected in recognized.lower(),language+' speech mismatch: '+recognized
   checks.append({'language':language,'recognized':recognized,'fixtureSHA256':digest});print('PASS: real local '+language+' speech inference',flush=True)
 report.parent.mkdir(parents=True,exist_ok=True)
 report.write_text(json.dumps({'passed':True,'checks':checks,'limitations':['Public audio fixtures prove native inference; they do not prove physical microphone capture.'],'attribution':['Russian weather pronunciation: The Shtooka Project, Wikimedia Commons File:Ru-погода.ogg, CC BY 2.0 France https://creativecommons.org/licenses/by/2.0/fr/deed.en; converted to mono PCM 16 kHz.','English sample: John F. Kennedy inaugural address, official whisper.cpp samples/jfk.wav; US federal speech in public domain.']},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
