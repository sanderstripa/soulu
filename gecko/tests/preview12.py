"""Requested Soul regressions against the production application surface."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{}}
try:
 start()
 check('opaque_by_default',chrome('return Soulu.config.settings.mattePanel===false'))
 check('weather_defaults',chrome('return Soulu.config.settings.homeWeatherMode==="automatic"&&Soulu.config.settings.homeWeatherUnits==="celsius"'))
 check('engine_identity_soul',chrome('return Services.appinfo.name==="Soul"'))
 wait(lambda:ui('return !!document.querySelector("#actions .primary")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page')
 wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("2")','page'))
 # Proceed through the existing welcome steps and save a key without leaving it.
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("3")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return document.getElementById("counter").textContent.startsWith("4")','page'))
 ui('document.querySelector("#actions .primary").click();return true;','page');wait(lambda:ui('return !!document.getElementById("welcomeVpnKey")','page'))
 ui('document.getElementById("welcomeVpnName").value="Fixture";document.getElementById("welcomeVpnKey").value="vless://00000000-0000-4000-8000-000000000001@example.org:443?security=tls&type=tcp#Fixture";document.querySelector("#controls button").click();return true;','page')
 check('vpn_key_saved_inside_welcome',wait(lambda:chrome('return Soulu.config.vpn.profiles.some(p=>p.name==="Fixture")&&!Soulu.settingsRequested')))
 check('welcome_remains_visible',ui('return location.pathname.endsWith("/onboarding.html")&&document.getElementById("controls").textContent.includes("OK")','page'))
 call('browser.extensions.manage',{'profile':'default'})
 check('extensions_manager_opens',wait(lambda:chrome('return gBrowser.selectedBrowser.currentURI.spec==="about:addons"')))
 check('no_stock_toolbar',chrome('return getComputedStyle(document.getElementById("navigator-toolbox")).display==="none"'))
 run('Soulu.config.onboarding={done:true,step:6};await Soulu.backend.save();return true;')
 stop();start()
 check('same_profile_reopens',chrome('return Soulu.ready&&Soulu.config.onboarding.done&&Soulu.config.vpn.profiles.some(p=>p.name==="Fixture")'))
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:print(chrome('return Services.console.getMessageArray().map(x=>x.message).slice(-25)'),flush=True)
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'preview12.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');log.close();server.shutdown()
