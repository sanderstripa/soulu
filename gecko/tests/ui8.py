"""Preview 8: reproduce the user's exact editor/sidebar/click and native add-ons paths."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text().split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'checks':{}}
try:
 start();wait(lambda:chrome('return !window.__souluStartupHidden'))
 wait(lambda:content('return location.pathname.endsWith("onboarding.html")'));wait(lambda:ui('return !!document.querySelector("#actions button:not(.primary)")','page'));ui('document.querySelector("#actions button:not(.primary)").click();return true','page');wait(lambda:content('return location.pathname.endsWith("home.html")'))
 call('browser.settings.openWindow','interface');wait(lambda:call('browser.state.get')['settingsOverlayReady']);ui('souluSettings.openSection("interface");return true','settings');wait(lambda:ui('return !!document.getElementById("showExtensions")','settings'))
 for value in [False,True]:
  ui('const n=document.getElementById("showExtensions");if(n.checked!=='+json.dumps(value)+')n.click();await souluSettings.flush();return true','settings');chrome('Soulu.closeSettings()');time.sleep(.3)
  check('extensions_toggle_actual_layout_'+str(value),wait(lambda:ui('const n=document.getElementById("soulu-extensions-menu");return (n.getBoundingClientRect().width>0)==='+json.dumps(value))),call('browser.state.get')['settings'].get('showExtensions'))
  if not value:call('browser.settings.openWindow','interface');time.sleep(.25)
 check('settings_changes_do_not_reset_completed_welcome',chrome('return Soulu.config.onboarding.done'))
 call('browser.navigate',url+'saved');select_latest();wait(lambda:content('return !!document.getElementById("v")'));marks=call('browser.bookmarks.add');mark=next(x for x in marks if x['url']==url+'saved');call('browser.home');wait(lambda:ui('return document.body.classList.contains("home-ready")','page'))
 ui('await souluNavigation.openBookmarks();return true');time.sleep(.2);chrome('Soulu.native.send("editBookmark",'+str(mark['id'])+');return true');wait(lambda:ui('return !!document.getElementById("bookmarkHomeFavorite")'))
 ui('const n=document.getElementById("bookmarkHomeFavorite");if(!n.checked)n.click();document.querySelector(".bookmark-editor").requestSubmit();return true');wait(lambda:ui('return !document.querySelector(".bookmark-editor")'));time.sleep(.3)
 r=ui('const r=document.getElementById("favoritesToggle").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}','page');offset=chrome('const r=gBrowser.selectedBrowser.getBoundingClientRect();return {x:r.x,y:r.y}');x=round(r['x']+offset['x']);y=round(r['y']+offset['y'])
 report['hitTest']=chrome('const n=document.elementFromPoint('+str(x)+','+str(y)+');return {id:n?.id,clip:document.getElementById("soulu-shell-frame").style.clipPath}')
 m.set_context('chrome');m._send_message('WebDriver:PerformActions',{'actions':[{'type':'pointer','id':'home-after-editor','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport','x':x,'y':y,'duration':0},{'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
 check('home_favorites_opens_after_edit_while_sidebar_stays_open',wait(lambda:ui('return !document.getElementById("favoritesPanel").hidden','page')) and call('browser.state.get')['bookmarksSidebarVisible'],report['hitTest'])
 call('browser.bookmarks.sidebar',False);call('browser.newTab');time.sleep(.4);ui('document.getElementById("classicPageMenu").click();return true');wait(lambda:ui('return !document.querySelector(".site-popover").hidden'))
 rect=ui('const a=document.getElementById("classicPageMenu").getBoundingClientRect(),r=document.querySelector(".site-popover").getBoundingClientRect();return {anchorBottom:a.bottom,menuTop:r.top,toolbar:parseFloat(getComputedStyle(document.body).getPropertyValue("--chrome-height"))}')
 check('page_actions_anchors_to_address_row',rect['menuTop']<=rect['anchorBottom']+9 and rect['menuTop']<rect['toolbar'],rect)
 ui('document.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));return true');times=[]
 for _ in range(4):
  began=time.monotonic();call('browser.newTab');select_latest();wait(lambda:ui('return document.body.classList.contains("home-ready")','page'));times.append(round((time.monotonic()-began)*1000))
 check('home_no_unnecessary_select_controls_or_web_loading_indicator',ui('return ![...document.scripts].some(s=>s.src.endsWith("select-control.js"))','page') and not call('browser.state.get')['page']['loading'],{'readyMilliseconds':times})
 native=run('await Soulu.votReady;const {AddonManager}=ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs");const a=await AddonManager.getAddonByID("vot-ext@firefox");return {builtin:a?.isBuiltin,active:a?.isActive};')
 listed=call('browser.extensions.list')['items'];check('vot_is_default_builtin_outside_user_extension_list',native.get('builtin') and native.get('active') and all(i['id']!='vot-ext@firefox' for i in listed),native)
 call('browser.openTab',{'url':'about:addons'});select_latest();wait(lambda:content('return !!document.querySelector("search-addons moz-input-search")?.shadowRoot?.querySelector("input[data-soulu-centered]")'))
 check('native_manager_does_not_list_builtin_vot',content('return ![...document.querySelectorAll("addon-card[addon-id=\\"vot-ext@firefox\\"]")].some(n=>n.getBoundingClientRect().height>0)'))
 branding=run('const a=await(await fetch("chrome://branding/content/about-logo.png")).arrayBuffer(),b=await(await fetch("chrome://soulu/content/ui/branding/soulu-128.png")).arrayBuffer();return a.byteLength===b.byteLength&&new Uint8Array(a).every((x,i)=>x===new Uint8Array(b)[i]);');check('native_addons_logo_is_actual_soulu_asset',branding)
 align=content('const n=document.querySelector("moz-input-search").shadowRoot.querySelector("input"),s=getComputedStyle(n);return {height:n.getBoundingClientRect().height,top:parseFloat(s.paddingTop),bottom:parseFloat(s.paddingBottom)}');check('native_manager_search_has_centered_vertical_padding',align['height']>=32 and abs(align['top']-align['bottom'])<1,align)
 m.set_context('chrome');(out/'addons8.png').write_bytes(base64.b64decode(m.screenshot()));report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:report['console']=chrome('return Services.console.getMessageArray().map(x=>x.message).slice(-18)');(out/'ui8-failure.png').write_bytes(base64.b64decode(m.screenshot()))
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'ui8.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
