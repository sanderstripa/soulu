/* Native WebRender backdrop. No screenshots, capture loop, or duplicate web view. */
(()=>{
 const H='http://www.w3.org/1999/xhtml',root=document.documentElement;
 const glass=document.createElementNS(H,'div');glass.id='soulu-page-glass';glass.setAttribute('aria-hidden','true');root.append(glass);
 const update=()=>{const uri=gBrowser.selectedBrowser.currentURI,home=uri.spec===Soulu.native.homeURL,enabled=!!Soulu.config.settings.mattePanel&&['http','https'].includes(uri.scheme);root.toggleAttribute('soulu-home',home);root.toggleAttribute('soulu-page-glass',enabled);Soulu.native.send('pageGlass',enabled);Soulu.notify();};
 const refresh=Soulu.refresh;Soulu.refresh=()=>{refresh();update();};
 gBrowser.tabContainer.addEventListener('TabSelect',update);gBrowser.addTabsProgressListener({onLocationChange(browser){if(browser===gBrowser.selectedBrowser)update();}});update();
})();
