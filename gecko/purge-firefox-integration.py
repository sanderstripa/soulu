"""Recursively remove Firefox shell-integration, updater and crash tooling from the runtime."""
import pathlib,sys
root=pathlib.Path(sys.argv[1]).resolve();runtime=root/'runtime'
stale={'default-browser-agent.exe','updater.exe','updater-settings.ini','updater.ini','crashreporter.exe','crashreporter.ini','crashreporter-override.ini','pingsender.exe','maintenanceservice.exe','maintenanceservice_installer.exe','minidump-analyzer.exe'}
removed=[]
for target in list(runtime.rglob('*')):
 if target.is_file() and target.name.lower() in stale:
  target.unlink();removed.append(str(target.relative_to(root)))
print('purged',len(removed),','.join(removed),flush=True)
