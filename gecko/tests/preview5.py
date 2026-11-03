"""Targeted Preview 5 checks: Places operations, real pixels and UI geometry."""
from pathlib import Path
source=Path(__file__).with_name('preview4.py').read_text(encoding='utf-8').split('\ntry:\n start()',1)[0]
exec(compile(source,str(Path(__file__).with_name('preview4.py')),'exec'),globals())
report={'passed':False,'scope':'Preview 5 corrected components','checks':{},'limitations':[]}
try:
 start();call('browser.navigate',url);wait(lambda:content('return !!document.getElementById("v")'))
 rows=call('browser.bookmarks.add');mark=next(r for r in rows if r['url']==url);mark.update(title='Renamed bookmark',url=url+'renamed')
 saved=call('browser.bookmarks.replace',rows);check('places_edit_title_and_url',any(r['title']=='Renamed bookmark' and r['url']==url+'renamed' for r in saved))
 folder=max(r['id'] for r in saved)+1;saved.append({'id':folder,'type':'folder','title':'Folder','parentId':0,'order':0});mark=next(r for r in saved if r['id']==mark['id']);mark['parentId']=folder
 moved=call('browser.bookmarks.replace',saved);check('places_move_to_new_folder',next(r for r in moved if r['id']==mark['id'])['parentId']==folder)
 call('browser.bookmarks.homeFavorite',{'id':mark['id'],'selected':True})
 call('browser.openTab',{'url':url+'second'});select_latest();second=call('browser.state.get')['activeTabId'];wait(lambda:content('return location.pathname==="/second"'))
 thumb=call('browser.tab.thumbnail',{'id':second});check('native_thumbnail_has_actual_pixels',bool(thumb['thumbnail']) and len(base64.b64decode(thumb['thumbnail'].split(',')[1]))>1500)
 from PIL import Image
 import io
 im=Image.open(io.BytesIO(base64.b64decode(thumb['thumbnail'].split(',')[1])));check('thumbnail_is_nonblank',len(im.convert('RGB').getcolors(im.width*im.height))>20)
 call('browser.overview',True);check('overview_renders_native_images',wait(lambda:ui('return [...document.querySelectorAll(".overview-preview img")].some(i=>i.complete&&i.naturalWidth>0)')));call('browser.overview',False)
 ui('drawSuggestions(document.querySelector("#classicSuggestions"),[{title:"A sufficiently long readable history title",url:"https://history.example.org/long/path",source:"history"}],"history");return true;')
 rect=ui('const n=document.querySelector("#classicSuggestions .suggestion-row span");return {width:n.getBoundingClientRect().width,column:getComputedStyle(n).gridColumnStart};');check('faviconless_history_text_uses_flexible_column',rect['width']>180 and rect['column']=='2',rect)
 ui('document.querySelector("#classicSuggestions").classList.remove("visible");return true;');call('browser.setSuggestionsHeight',0)
 call('browser.settings.openWindow');wait(lambda:call('browser.state.get')['settingsOverlayReady']);check('settings_preserves_12_sections',ui('return document.querySelectorAll("#homeCards button").length===12','settings'))
 ui('souluSettings.openSection("about");return true;','settings');check('preview5_version',ui('return document.querySelector("#sectionContent").textContent.includes("Gecko Preview 5")','settings'))
 chrome('Soulu.closeSettings()');time.sleep(.3)
 bounds=chrome('const a=document.getElementById("browser").getBoundingClientRect(),b=gBrowser.selectedBrowser.getBoundingClientRect();return {left:b.left-a.left,right:a.right-b.right,bottom:a.bottom-b.bottom};');check('native_content_fills_browser_bounds',all(abs(v)<=1 for v in bounds.values()),bounds)
 call('browser.settings.set',{'startupMode':'continue'});stop();start();rows=call('browser.bookmarks.get');check('places_edit_survives_restart',any(r['id']==mark['id'] and r['title']=='Renamed bookmark' and r['parentId']==folder for r in rows));check('home_favorite_survives_restart',mark['id'] in call('browser.state.get')['settings']['homeFavoriteIds'])
 report['passed']=True
except Exception as e:
 report['error']=str(e)
 try:
  report['diagnostic']=chrome('return Services.console.getMessageArray().map(m=>m.message).slice(-20)');(out/'failure.png').write_bytes(base64.b64decode(m.screenshot()))
 except Exception:pass
 raise
finally:
 try:stop()
 finally:(out/'preview5.json').write_text(json.dumps(report,indent=2),encoding='utf-8');log.close();server.shutdown()
