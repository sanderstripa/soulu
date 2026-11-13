"""Exercise controls inside the installed Gecko shell through its test-only actor."""
import json


def verify_toolbar(m, check, wait):
    def shell(code):
        script = ('const done=arguments[arguments.length-1];'
                  'document.getElementById("sona-shell-frame").browsingContext.currentWindowGlobal'
                  '.getActor("SonaApp").sendQuery("testing",' + json.dumps(code) +
                  ').then(done,error=>done({error:String(error)}));')
        value = m.execute_async_script(script)
        if isinstance(value, dict) and 'error' in value:
            raise AssertionError(value['error'])
        return value

    count = "return document.querySelectorAll('#tabStrip > [data-tab-id]').length;"
    wait(lambda: shell(count) == 1)
    for expected in range(2, 5):
        shell("document.getElementById('newTabButton').click();")
        wait(lambda: shell(count) == expected)
    print('strip layout',shell("""
        await new Promise(r=>setTimeout(r,700));
        const nodes=[...document.querySelectorAll('.tabs-zone,#tabStrip,#tabStrip > [data-tab-id]')];
        return JSON.stringify({size:[innerWidth,innerHeight],expanded:document.body.dataset.adaptiveExpanded,
          nodes:nodes.map(n=>{const r=n.getBoundingClientRect(), s=getComputedStyle(n);
            return [n.className,r.toJSON(),s.visibility,s.opacity,s.pointerEvents,document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.outerHTML.slice(0,200)]})});
    """),flush=True)
    check('four_visible_clickable_tabs', wait(lambda: shell("""
        return [...document.querySelectorAll('#tabStrip > [data-tab-id]')].every(tab=>{
          const r=tab.getBoundingClientRect();
          return r.width>0 && r.height>0 && tab.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));
        });
    """)))
    shell("document.querySelector('#tabStrip > [data-tab-id]').click();")
    check('select_first_tab_from_strip', wait(lambda: shell("return document.querySelector('#tabStrip > :first-child').classList.contains('active');")))
    def centered(selector):
        return shell("""
            const button=document.querySelector(%s), icon=button?.querySelector('svg');
            if(!icon)return false;
            const b=button.getBoundingClientRect(), i=icon.getBoundingClientRect();
            return i.width>0 && Math.abs((b.left+b.right-i.left-i.right)/2)<=0.75
                && Math.abs((b.top+b.bottom-i.top-i.bottom)/2)<=0.75;
        """ % json.dumps(selector))

    check('tab_close_glyph_centered', wait(lambda: centered('#tabStrip .active [data-close-tab]')))
    shell("await window.browserShell.setOverview(true);")
    check('overview_close_glyph_centered', wait(lambda: centered('.overview-caption > button')))
    shell("await window.browserShell.setOverview(false);")
    for expected in [3, 2, 1]:
        shell("document.querySelector('#tabStrip > :last-child [data-close-tab]').click();")
        wait(lambda: shell(count) == expected)
    check('close_tabs_from_strip', m.execute_script('return gBrowser.tabs.length') == 1)
    shell("document.getElementById('sidebarButton').click();")
    check('bookmark_search_inside_panel_without_autofocus',wait(lambda: shell("""
        const panel=document.querySelector('.bookmarks-menu'), search=panel.querySelector('.navigation-search');
        const r=search.getBoundingClientRect(), p=panel.getBoundingClientRect();
        return !panel.hidden && r.width>0 && r.left>=p.left && r.right<=p.right && p.width<=276 && document.activeElement!==search;
    """)))
    geometry = shell("""
        const tree=document.querySelector('.bookmarks-menu .bookmark-tree');
        const thumb=tree.parentElement.querySelector('.bookmark-scroll-thumb');
        const sheet=new document.defaultView.CSSStyleSheet();
        sheet.replaceSync('.bookmarks-menu .bookmark-tree::after{content:"";display:block;height:3000px}');
        document.adoptedStyleSheets.push(sheet);
        try {
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            tree.scrollTop=tree.scrollHeight;
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            return JSON.stringify({size:thumb.offsetHeight,hidden:thumb.hidden,top:tree.scrollTop,
                radius:parseFloat(getComputedStyle(thumb,'::before').borderRadius),
                delta:tree.getBoundingClientRect().bottom-thumb.getBoundingClientRect().bottom});
        } finally { document.adoptedStyleSheets=document.adoptedStyleSheets.filter(s=>s!==sheet);tree.scrollTop=0; }
    """)
    g=json.loads(geometry)
    check('rounded_bookmark_thumb_tracks_scrolling', g['size']>=24 and not g['hidden'] and
          g['top']>0 and g['radius']>0 and abs(g['delta'])<=1, g)
    shell("document.getElementById('sidebarButton').click();")
