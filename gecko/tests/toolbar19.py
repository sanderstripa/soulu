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
    check('four_visible_clickable_tabs', wait(lambda: shell("""
        return [...document.querySelectorAll('#tabStrip > [data-tab-id]')].every(tab=>{
          const r=tab.getBoundingClientRect();
          return r.width>0 && r.height>0 && tab.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));
        });
    """)))
    shell("document.querySelector('#tabStrip > [data-tab-id]').click();")
    check('select_first_tab_from_strip', wait(lambda: shell("return document.querySelector('#tabStrip > :first-child').classList.contains('active');")))
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
    shell("document.getElementById('sidebarButton').click();")
