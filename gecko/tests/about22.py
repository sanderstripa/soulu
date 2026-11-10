"""Verify the About view and real filter installation in the running engine."""
import json
def verify_about(m,check,wait):
    m.execute_script('Soulu.dispatch("browser.settings.openWindow");return true;')
    wait(lambda:m.execute_script('return !!document.getElementById("soulu-settings-frame")?.browsingContext.currentWindowGlobal'))
    def settings(code):
        return m.execute_async_script('const done=arguments[arguments.length-1];document.getElementById("soulu-settings-frame").browsingContext.currentWindowGlobal.getActor("SouluApp").sendQuery("testing",'+json.dumps(code)+').then(done,e=>done({error:String(e)}));')
    import time
    time.sleep(3)
    print('settings diagnostic',settings('return JSON.stringify({ready:document.body.className,loaded:!!window.souluSettings?.loaded,message:document.getElementById("dataMessage")?.textContent,text:document.body.innerText.slice(-1500)});'),flush=True)
    print('settings requests',settings('const out={};for(const action of ["begin","capabilities"]){try{out[action]=await window.souluSettings.invoke(action);}catch(e){out[action]=String(e);}}return JSON.stringify(out);'),flush=True)
    wait(lambda:settings('return !!window.souluSettings?.loaded && document.body.classList.contains("ready");') is True)
    print("about section",settings("await window.souluSettings.openSection('about');return document.getElementById('sectionContent').innerText;"),flush=True)
    check('about_three_blocks_and_gecko',wait(lambda:settings("return document.querySelectorAll('.version-grid > div').length===2 && document.querySelector('.version-grid').textContent.includes('Gecko') && !!document.querySelector('[data-adblock-manager] button') && !!document.querySelector('.component-manager');") is True))
    result=m.execute_async_script('const done=arguments[arguments.length-1];Soulu.adblock.update().then(done,e=>done({error:String(e)}));')
    check('downloaded_filters_installed_in_real_adblock',isinstance(result,dict) and not result.get('error') and result.get('networkRules',0)>0 and result.get('lastSuccessfulUpdate',0)>0,result)
    settings("document.getElementById('closeSettings').click();")
