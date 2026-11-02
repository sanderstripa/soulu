import pathlib,json,urllib.request,hashlib,zipfile,shutil,subprocess,os
root=pathlib.Path(__file__).resolve().parent.parent
pins=json.loads((root/'vpn/components-pin.json').read_text());target=root/'gecko-out/runtime/soulu/vpn';target.mkdir(parents=True,exist_ok=True);stamps={}
for name,pin in pins.items():
 archive=root/'gecko-cache'/pin['archive']
 if not archive.exists():
  print('Download',name,flush=True)
  with urllib.request.urlopen(pin['url'],timeout=180) as response,archive.open('wb') as f:shutil.copyfileobj(response,f)
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=pin['sha256']:raise RuntimeError(name+' integrity mismatch')
 dest=target/name;dest.mkdir(exist_ok=True)
 with zipfile.ZipFile(archive) as z:
  for entry in z.infolist():
   fname=pathlib.PurePosixPath(entry.filename).name
   if fname.lower() in [name+'.exe','geoip.dat','geosite.dat','license','license.txt','readme.md']:(dest/fname).write_bytes(z.read(entry))
 exe=dest/(name+'.exe');assert exe.read_bytes()[:2]==b'MZ'
 stamps[name]={'version':pin['version'],'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
 (dest/'SOURCE.txt').write_text(json.dumps(pin,indent=2))
(target/'components.json').write_text(json.dumps(stamps,indent=2))
for name in ['xray','sudoku']:
 for f in (root/'vpn/native-host'/name).glob('*LICENSE*'):shutil.copy(f,target/name/f.name)
subprocess.run([os.environ.get('GO_BINARY','go'),'build','-trimpath','-ldflags','-s -w','-o',str(target/'SouluVpnHost.exe'),'.'],cwd=root/'vpn/helper',env={**os.environ,'GOOS':'windows','GOARCH':'amd64'},check=True)
