"""Targeted Home/state regression checks against the assembled Windows browser."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{},'limitations':[]}
try:
 start();wait(lambda:content('return location.pathname.endsWith("onboarding.html")'));wait(lambda:ui('return !!document.querySelector("#actions button:not(.primary)")','page'));ui('document.querySelector("#actions button:not(.primary)").click();return true;','page');wait(lambda:content('return location.pathname.endsWith("home.html")'));wait(lambda:ui('return document.body.classList.contains("home-ready")','page'));check('home_revealed_after_state_and_font_ready',True)
 call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'));rows=call('browser.bookmarks.add');first=next(r for r in rows if r['url']==url)
 call('browser.navigate',url+'second');wait(lambda:content('return location.pathname==="/second"'));rows=call('browser.bookmarks.add');second=next(r for r in rows if r['url']==url+'second')
 call('browser.navigate','soulu://home');wait(lambda:content('return location.pathname.endsWith("home.html")'));wait(lambda:ui('return document.body.classList.contains("home-ready")','page'))
 identity=chrome('return gBrowser.selectedBrowser.browsingContext.currentWindowGlobal.innerWindowId')
 call('browser.bookmarks.homeFavorite',{'id':first['id'],'selected':True});wait(lambda:ui('return document.querySelectorAll(".favorite").length===1','page'));check('favorite_updates_existing_home_without_reload',identity==chrome('return gBrowser.selectedBrowser.browsingContext.currentWindowGlobal.innerWindowId'))
 call('home.favorite.add',second['id']);wait(lambda:ui('return document.querySelectorAll(".favorite").length===2','page'));call('home.favorite.reorder',[second['id'],first['id']]);wait(lambda:ui('return document.querySelector(".favorite").href.endsWith("/second")','page'));check('favorite_order_and_no_url_caption',ui('return !document.querySelector(".favorite small")','page'))
 call('browser.settings.set',{'homeShowFavorites':False});check('home_toggle_applies_live',wait(lambda:ui('return document.getElementById("favoritesToggle").hidden','page')))
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady']);ui('souluSettings.openSection("about");return true','settings');chrome('Soulu.closeSettings()');time.sleep(.3);call('browser.settings.openWindow');check('settings_reopens_at_12_cards',wait(lambda:ui('return !document.getElementById("homeCards").hidden&&document.querySelectorAll("#homeCards button").length===12','settings')));chrome('Soulu.closeSettings()');time.sleep(.3)
 check('single_extensions_button',ui('return !!document.getElementById("soulu-extensions-menu")&&!document.querySelector("[data-extension-toolbar] [data-extension-id]")'))
 call('browser.settings.set',{'showExtensions':False});check('extensions_toggle_applies',wait(lambda:ui('return document.getElementById("soulu-extensions-menu").hidden')))
 call('browser.openTab',{'url':url+'extra'});select_latest();call('browser.closeOtherTabs',call('browser.state.get')['activeTabId']);time.sleep(.5);check('single_tab_geometry_centered',ui('return document.body.style.getPropertyValue("--adaptive-progress")==="0"'))
 report['passed']=True
finally:
 try:stop()
 finally:(out/'preview6.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
