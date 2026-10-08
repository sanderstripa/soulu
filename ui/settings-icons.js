(() => {
  'use strict';
  // 24-unit grid; 1.5-unit rounded stroke; monochrome currentColor.
  const paths={
    all:'<path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/>',
    general:'<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="2.5"/><circle cx="15" cy="17" r="2.5"/>',
    interface:'<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9h17M9 9v10.5"/>',
    startup:'<path d="m3.5 11 8.5-7 8.5 7M6 9v11h12V9M10 20v-6h4v6"/>',
    search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 4.5 4.5"/>',
    privacy:'<path d="m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6z"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    vpn:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
    reading:'<path d="M12 6c-3-2-6-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1zm0 0v14M6 9h3M6 12h3M15 9h3M15 12h3"/>',
    profiles:'<circle cx="10" cy="7.5" r="3.5"/><path d="M3.5 20v-2a6.5 6.5 0 0 1 13 0v2M17 4a3.5 3.5 0 0 1 0 7M19 14a5 5 0 0 1 2 4v2"/>',
    about:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    close:'<path d="m6.5 6.5 11 11m0-11-11 11"/>',
    chevron:'<path d="m9 6 6 6-6 6"/>',
    open:'<path d="M14 4h6v6m0-6-9 9M10 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/>',
    remove:'<path d="M5 7h14M9 7V4h6v3M7 7l1 13h8l1-13M10 10v7M14 10v7"/>',
    add:'<path d="M12 5v14M5 12h14"/>',
    up:'<path d="m6 13 6-6 6 6M12 7v12"/>',
    edit:'<path d="m4 16 12-12 4 4L8 20H4zm10-10 4 4"/>'
  };
  window.souluSettingsIcons={create(id){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');svg.dataset.settingsIcon=id;svg.innerHTML=paths[id]||paths.open;return svg;}};
})();
