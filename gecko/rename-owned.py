"""Normalize owned payloads and the pinned installer sources to current identity."""
from pathlib import Path
import re,sys,zipfile
OLD=''.join(map(chr,[83,111,117,108,117]))
def rename(text):
 # Repository location is controlled independently by the owner.
 text=text.replace('sanderstripa/'+OLD.lower(),'__REPOSITORY_LOCATION__')
 text=re.sub(OLD,lambda m:'SONA' if m[0].isupper() else 'Sona' if m[0][0].isupper() else 'sona',text,flags=re.I)
 return text.replace('__REPOSITORY_LOCATION__','sanderstripa/'+OLD.lower())
def normalize(root):
 root=Path(root)
 for path in list(root.rglob('*')):
  if not path.is_file() or '.git' in path.parts:continue
  if path.name in {'easylist.txt','easyprivacy.txt','ruadlist.txt'}:continue
  data=path.read_bytes()
  if b'\x00' in data:continue
  try:text=data.decode('utf-8')
  except UnicodeDecodeError:continue
  updated=rename(text)
  if text!=updated:path.write_bytes(updated.encode('utf-8'))
 for path in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
  if '.git' not in path.parts and rename(path.name)!=path.name:path.rename(path.with_name(rename(path.name)))
if __name__=='__main__':normalize(sys.argv[1])
