"""Preview 9 acceptance: the payload ships exactly one browser and registers nothing Firefox-branded."""
import json,pathlib,sys
build=pathlib.Path(sys.argv[1]).resolve();report={'passed':False,'checks':{}}
def check(name,value,detail=None):
 report['checks'][name]={'passed':bool(value),'detail':detail};print(name,bool(value),detail or '',flush=True)
 if not value:raise AssertionError(name+': '+str(detail))
# The runtime keeps its engine binary, but none of the tools that would register or
# update a separate Mozilla Firefox installation.
forbidden={'default-browser-agent.exe','updater.exe','crashreporter.exe','pingsender.exe','maintenanceservice.exe','maintenanceservice_installer.exe','minidump-analyzer.exe'}
leftovers=[str(p.relative_to(build)) for p in build.rglob('*') if p.name.lower() in forbidden or p.name.lower().startswith(('crashreporter-','maintenanceservice','default-browser-agent','pingsender','updater-'))]
check('payload_has_no_firefox_side_binaries',not leftovers,leftovers)
check('isolated_gecko_runtime_present',(build/'runtime/firefox.exe').is_file() and (build/'runtime/xul.dll').is_file() and (build/'runtime/soulu.cfg').is_file())
provenance=json.loads((build/'BUILD.json').read_text(encoding='utf-8'))
check('manifest_is_soulu_preview9',provenance.get('name')=='Soulu Gecko Preview 9' and provenance.get('channel')=='gecko-preview',provenance)
check('launcher_built',(build/'Soulu.exe').is_file())
if sys.platform=='win32':
 # Nothing inside this build may be registered under a Firefox-named browser entry.
 import winreg
 def firefox_registrations():
  hits=[]
  try:root=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Clients\StartMenuInternet')
  except OSError:return hits
  index=0
  while True:
   try:name=winreg.EnumKey(root,index);index+=1
   except OSError:break
   if not name.lower().startswith('firefox'):continue
   try:
    with winreg.OpenKey(root,name+r'\shell\open\command') as key:command=winreg.QueryValueEx(key,'')[0]
   except OSError:command=''
   if str(build).lower() in command.lower():hits.append(name)
  return hits
 check('no_firefox_registration_points_into_build',not firefox_registrations(),firefox_registrations())
report['passed']=True
reportPath=build.parent/'preview9.json'
reportPath.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('preview9: passed')
