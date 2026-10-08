"""Run only the import adapters against an empty, isolated AppData fixture."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

exe=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('browser-import-native.json').resolve()
with tempfile.TemporaryDirectory(prefix='soulu-import-fixture-') as temporary:
    root=Path(temporary)
    appdata=root/'empty-appdata'
    appdata.mkdir()
    report=root/'result.json'
    env=dict(os.environ,LOCALAPPDATA=str(appdata),APPDATA=str(appdata),
             SOULU_DATA_SECURITY_TEST_ROOT=str(appdata),SOULU_UI_TEST_PORT='0')
    result=subprocess.run([str(exe),'--browser-import-test-report='+str(report)],env=env,timeout=90)
    if not report.exists():
        raise SystemExit('Import test report missing; use a binary built with Browser Import 2.0 sources')
    data=json.loads(report.read_text(encoding='utf-8'))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('Import native checks:',data.get('checks'),'; passed:',data.get('ok'))
    raise SystemExit(0 if result.returncode==0 and data.get('ok') else 2)
