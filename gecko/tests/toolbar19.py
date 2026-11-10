"""Exercise controls inside the installed Gecko shell through its test-only actor."""
import json


def verify_toolbar(m, check, wait):
    def shell(code):
        script = ('const done=arguments[arguments.length-1];'
                  'document.getElementById("soulu-shell-frame").browsingContext.currentWindowGlobal'
                  '.getActor("SouluApp").sendQuery("testing",' + json.dumps(code) +
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
    check('rounded_bookmark_thumb_tracks_scrolling', shell("""
        const tree=document.querySelector('.bookmarks-menu .bookmark-tree');
        const thumb=tree.parentElement.querySelector('.bookmark-scroll-thumb');
        const filler=document.createElement('div');
        filler.style.height='3000px';
        tree.append(filler);
        try {
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            tree.scrollTop=tree.scrollHeight;
            await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
            return thumb.offsetHeight>=24 && !thumb.hidden && tree.scrollTop>0 &&
                parseFloat(getComputedStyle(thumb,'::before').borderRadius)>0 &&
                Math.abs(tree.getBoundingClientRect().bottom-thumb.getBoundingClientRect().bottom)<1;
        } finally { filler.remove(); tree.scrollTop=0; }
    """))
    shell("document.getElementById('sidebarButton').click();")
