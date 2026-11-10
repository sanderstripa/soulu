"""Acceptance checks in the real installed Gecko process."""
import base64,json

def verify_branding(m,check,wait,out):
    check('chatbot_disabled_on_profile',m.execute_script('return ["browser.ml.chat.enabled","browser.ml.chat.menu","browser.ml.chat.page","browser.ml.chat.shortcuts"].every(p=>Services.prefs.getBoolPref(p)===false&&Services.prefs.prefIsLocked(p));'))
    check('website_ua_compatibility',m.execute_script('const s=Services.prefs.getStringPref("general.useragent.override");return s.includes("Firefox/160.0")&&s.includes("Soulu/1.160.25");'))
    # Verify the packaged illustration bytes, not just a hidden image in one page.
    result=m.execute_async_script('const done=arguments[arguments.length-1];(async()=>{const uri="chrome://global/skin/illustrations/no-connection.svg";const r=await fetch(uri);const text=await r.text();return text.includes("data:image/png;base64,");})().then(done,e=>done({error:String(e)}));')
    check('native_fox_resource_replaced',result is True,result)
    m.execute_script('gBrowser.selectedTab=gBrowser.addTab("http://soulu-brand-check.invalid/",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});return true;')
    m.set_context('content')
    wait(lambda:m.execute_script('return document.documentURI.startsWith("about:neterror")&&!!document.querySelector(".title-text");'))
    check('real_dns_error_retains_retry',wait(lambda:m.execute_script('return !!(document.querySelector("#netErrorButtonContainer button")||document.querySelector("net-error-card")||document.querySelector("#errorTryAgain"));')))
    check('real_error_uses_soulu_accent',m.execute_script('return getComputedStyle(document.documentElement).getPropertyValue("--color-accent-primary").trim()==="#0671ff";'))
    (out/'soulu-network-error.png').write_bytes(base64.b64decode(m.screenshot()))
    m.set_context('chrome')
    m.execute_script('gBrowser.removeTab(gBrowser.selectedTab,{animate:false});return true;')
