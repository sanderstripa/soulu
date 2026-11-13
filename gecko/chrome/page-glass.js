/* Native WebRender backdrop. No screenshots, capture loop, or duplicate web view. */
(()=>{
 const H='http://www.w3.org/1999/xhtml',root=document.documentElement;
 const glass=document.createElementNS(H,'div');glass.id='sona-page-glass';glass.setAttribute('aria-hidden','true');root.append(glass);
 const update=()=>{const uri=gBrowser.selectedBrowser.currentURI,home=uri.spec===Sona.native.homeURL,enabled=!!Sona.config.settings.mattePanel&&['http','https'].includes(uri.scheme);root.toggleAttribute('sona-home',home);root.toggleAttribute('sona-page-glass',enabled);Sona.native.send('pageGlass',enabled);Sona.notify();};
 const refresh=Sona.refresh;Sona.refresh=()=>{refresh();update();};
 gBrowser.tabContainer.addEventListener('TabSelect',update);gBrowser.addTabsProgressListener({onLocationChange(browser){if(browser===gBrowser.selectedBrowser)update();}});update();
})();
