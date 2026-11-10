"""Requested Preview 14 theme regression, on the real application surfaces."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
source=source.replace("exec(compile(source,", "source=source.replace(\"else:command=[str(binary),*headless\",\"else:command=[str(binary),'-app',str(binary.parent/'browser/application.ini'),*headless\")\nexec(compile(source,")
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
import winreg
report={'passed':False,'checks':{}}
key=winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
try:previous=winreg.QueryValueEx(key,'AppsUseLightTheme')
except FileNotFoundError:previous=None
try:
 start()
 for value in [0,1]:
  winreg.SetValueEx(key,'AppsUseLightTheme',0,winreg.REG_DWORD,value)
  for setting in ['light','dark','system']:
   expected=('light' if value else 'dark') if setting=='system' else setting
   chrome('Soulu.config.settings.theme='+json.dumps(setting)+';Soulu.refresh();Soulu.notify();return true;')
   # Refresh onboarding data through its actual IPC/render path.
   ui('location.reload();return true;','page')
   wait(lambda:ui('return !!document.querySelector("#controls select")','page'))
   check('welcome_'+str(value)+'_'+setting,wait(lambda:ui('return document.body.dataset.theme==='+json.dumps(expected),'page')))
   check('toolbar_'+str(value)+'_'+setting,wait(lambda:ui('return document.body.dataset.theme==='+json.dumps(expected))))
   check('native_'+str(value)+'_'+setting,chrome('return document.documentElement.hasAttribute("soulu-dark")==='+str(expected=='dark').lower()))
   (out/('theme-'+str(value)+'-'+setting+'.png')).write_bytes(base64.b64decode(m.screenshot()))
 report['passed']=True
except Exception as e:
 report['error']=str(e);raise
finally:
 if previous is None:winreg.DeleteValue(key,'AppsUseLightTheme')
 else:winreg.SetValueEx(key,'AppsUseLightTheme',0,previous[1],previous[0])
 key.Close();(out/'preview14.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));stop()
