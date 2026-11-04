"""Regression checks use the real editor and actual renderer pixels, not backend buttons alone."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{}}
try:
 started=time.monotonic();start();report['startupSeconds']=time.monotonic()-started
 wait(lambda:content('return location.pathname.endsWith("onboarding.html")'));wait(lambda:ui('return !!document.querySelector("#actions button:not(.primary)")','page'));ui('document.querySelector("#actions button:not(.primary)").click();return true','page');wait(lambda:content('return location.pathname.endsWith("home.html")'))
 call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'));rows=call('browser.bookmarks.add');mark=next(r for r in rows if r['url']==url);call('browser.bookmarks.homeFavorite',{'id':mark['id'],'selected':True})
 call('browser.navigate',url+'second');wait(lambda:content('return location.pathname==="/second"'));rows=call('browser.bookmarks.add');second=next(r for r in rows if r['url']==url+'second');call('browser.bookmarks.homeFavorite',{'id':second['id'],'selected':True})
 # A real settings snapshot must not overwrite newer favorites on a theme save.
 config=call('settings.begin');call('browser.bookmarks.homeFavorite',{'id':mark['id'],'selected':False});config['settings']['theme']='light';call('settings.save',config);check('stale_settings_do_not_restore_or_erase_favorites',call('browser.state.get')['settings']['homeFavoriteIds']==[second['id']])
 call('browser.bookmarks.homeFavorite',{'id':mark['id'],'selected':True});wait(lambda:ui('return document.querySelector("#favoritesButton")!==null'))
 ui('document.querySelector("#favoritesButton").click();return true');wait(lambda:ui('return !!document.getElementById("bookmarkHomeFavorite")'));check('actual_editor_reads_saved_favorite',ui('return document.getElementById("bookmarkHomeFavorite").checked'))
 ui('document.querySelector(".bookmark-editor").requestSubmit();return true');wait(lambda:ui('return !document.querySelector(".bookmark-editor")'));check('editor_preserves_other_favorites',set(call('browser.state.get')['settings']['homeFavoriteIds'])=={mark['id'],second['id']})
 call('browser.home');wait(lambda:content('return location.pathname.endsWith("home.html")'));wait(lambda:ui('return document.body.classList.contains("home-ready")','page'));check('home_shows_both_favorites_after_edit',ui('return document.querySelectorAll(".favorite").length===2','page'))
 chrome('window.openPreferences("panePrivacy")');check('native_preferences_entry_routes_to_soulu',wait(lambda:call('browser.state.get')['settingsOverlayOpen']));check('no_native_preferences_tab',all(not t['url'].startswith('about:preferences') for t in call('browser.state.get')['tabs']));chrome('Soulu.closeSettings()');time.sleep(.25)
 check('puzzle_icon_matches_existing_asset',ui('return document.querySelector("#soulu-extensions-menu path").getAttribute("d").startsWith("M4 4h6V2")'))
 fixture={'draft':False,'tag_name':'gecko-preview-7','assets':[{'id':1,'name':'Soulu-Gecko-Preview-7-win64.zip','size':100,'digest':'sha256:'+'a'*64,'browser_download_url':'https://github.com/sanderstripa/soulu/releases/download/gecko-preview-7/Soulu-Gecko-Preview-7-win64.zip'}]};check('updater_never_offers_current_release',chrome('return Soulu.updateCandidate('+json.dumps([fixture])+')===null'))
 call('browser.navigate',url+'glass');wait(lambda:content('return !!document.getElementById("v")'));content('document.body.style.background="#ff0000";document.getElementById("box").style.background="#ff0000";return true')
 call('browser.settings.set',{'mattePanel':True});time.sleep(.6)
 def shot(name):
  m.set_context('chrome');raw=base64.b64decode(m.screenshot());(out/name).write_bytes(raw);return raw
 red=shot('glass-red.png');content('document.body.style.background="#0000ff";document.getElementById("box").style.background="#0000ff";return true');time.sleep(.4);blue=shot('glass-blue.png')
 from PIL import Image
 import io
 a=Image.open(io.BytesIO(red)).convert('RGB');b=Image.open(io.BytesIO(blue)).convert('RGB');points=[(int(a.width*f),10) for f in [.2,.4,.6,.8]];diff=sum(sum(abs(x-y) for x,y in zip(a.getpixel(p),b.getpixel(p))) for p in points);check('actual_toolbar_backdrop_samples_page_pixels',diff>60,{'delta':diff,'points':points})
 call('browser.settings.set',{'mattePanel':False});time.sleep(.3);opaque=shot('glass-disabled.png');c=Image.open(io.BytesIO(opaque)).convert('RGB');diffOff=sum(sum(abs(x-y) for x,y in zip(b.getpixel(p),c.getpixel(p))) for p in points);check('matte_toggle_changes_actual_pixels',diffOff>60,{'delta':diffOff})
 # Inspect the actual native location/permissions, not a filtered Soulu label.
 result=run('return await Soulu.dispatch("browser.vot.install",{consent:true},{gesture:{at:Date.now()}});');check('vot_builtin_install_completes',result['installed'])
 native=run('const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");const a=await AddonManager.getAddonByID("vot-ext@firefox");return {builtin:a.isBuiltin,canUninstall:!!(a.permissions&AddonManager.PERM_CAN_UNINSTALL),active:a.isActive};')
 check('vot_is_native_builtin_and_not_user_removable',native['builtin'] and not native['canUninstall'],native)
 report['passed']=True
except Exception as error:
 report['error']=str(error)
 try:report['console']=chrome('return Services.console.getMessageArray().map(x=>x.message).slice(-20)');(out/'failure.png').write_bytes(base64.b64decode(m.screenshot()))
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'preview7.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
