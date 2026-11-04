/* Native WebRender backdrop. No screenshots, capture loop, or duplicate web view. */
(()=>{
 const H='http://www.w3.org/1999/xhtml',root=document.documentElement;
 const glass=document.createElementNS(H,'div');glass.id='soulu-page-glass';glass.setAttribute('aria-hidden','true');root.append(glass);
 const update=()=>{const home=gBrowser.selectedBrowser.currentURI.spec===Soulu.native.homeURL;root.toggleAttribute('soulu-home',home);root.toggleAttribute('soulu-page-glass',!!Soulu.config.settings.mattePanel&&!home);Soulu.native.send('pageGlass',!!Soulu.config.settings.mattePanel&&!home);Soulu.notify();};
 const refresh=Soulu.refresh;Soulu.refresh=()=>{refresh();update();};
 gBrowser.tabContainer.addEventListener('TabSelect',update);gBrowser.addTabsProgressListener({onLocationChange(browser){if(browser===gBrowser.selectedBrowser)update();}});update();
})();
