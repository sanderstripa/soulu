"""Reject previous product identity in paths and owned readable resources."""
from pathlib import Path
import json,re,subprocess,sys,zipfile
old=''.join(map(chr,[115,111,117,108,117]))
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
failures=[];count=0
external={'easylist.txt','easyprivacy.txt','ruadlist.txt'}
def inspect(name,data):
 global count
 count+=1
 if old in name.lower():failures.append(name+': path')
 if Path(name).name in external or b'\0' in data:return
 try:text=data.decode('utf-8')
 except UnicodeDecodeError:return
 # Until the owner renames the GitHub repository its canonical location stays.
 text=text.replace('sanderstripa/'+old,'sanderstripa/REPOSITORY')
 if old in text.lower():failures.append(name+': contents')
if len(sys.argv)>1:
 for p in root.rglob('*'):
  if not p.is_file():continue
  name=p.relative_to(root).as_posix()
  inspect(name,p.read_bytes())
  if p.suffix=='.ja':
   with zipfile.ZipFile(p) as z:
    for entry in z.namelist():inspect(name+'!'+entry,z.read(entry))
else:
 paths=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=root).decode().split('\0')
 for name in set(paths):
  if name and (root/name).is_file():inspect(name,(root/name).read_bytes())
print(json.dumps({'passed':not failures,'files':count,'failures':failures},ensure_ascii=False))
if failures:raise SystemExit(1)
