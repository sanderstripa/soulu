"""Exercise real CEF settings-page events and inspect the separate shell browser."""
import json
import os
import time
import urllib.request
import websocket

PORT = int(os.environ.get("SOULU_UI_TEST_PORT", "9223"))
BASE = f"http://127.0.0.1:{PORT}"
seq = 0

def targets():
    with urllib.request.urlopen(BASE + "/json/list", timeout=3) as response:
        return json.load(response)

def find_target(fragment, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            for target in targets():
                if fragment in target.get("url", "") and target.get("type") == "page":
                    return websocket.create_connection(
                        target["webSocketDebuggerUrl"], timeout=8,
                        origin=f"http://127.0.0.1:{PORT}")
        except (OSError, KeyError):
            pass
        time.sleep(.25)
    raise AssertionError(f"CEF target {fragment!r} did not appear")

def evaluate(ws, expression):
    global seq
    seq += 1
    ident = seq
    ws.send(json.dumps({"id": ident, "method": "Runtime.evaluate",
                        "params": {"expression": expression,
                                   "returnByValue": True, "awaitPromise": True}}))
    while True:
        response = json.loads(ws.recv())
        if response.get("id") != ident:
            continue
        if "error" in response:
            raise AssertionError(response["error"])
        result = response["result"]
        if "exceptionDetails" in result:
            raise AssertionError(result["exceptionDetails"])
        return result["result"].get("value")

def wait_for(predicate, label, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (OSError, KeyError):
            pass
        time.sleep(.25)
    raise AssertionError(f"UI state not reached: {label}")

shell = find_target("/ui/index.html")
settings = None
try:
    assert wait_for(lambda: evaluate(shell, "Boolean(window.browserShell && document.querySelector('.browser-toolbar'))"), "shell ready")
    if os.environ.get('SOULU_REGRESSION_SKIP_FIRST_RUN')=='1':
        onboarding=next((r for r in targets() if '/ui/onboarding.html' in r.get('url','')),None)
        if onboarding:
            setup=find_target('/ui/onboarding.html')
            try:
                wait_for(lambda:evaluate(setup,"typeof window.cefQuery==='function'"),'onboarding bridge')
                evaluate(setup,"new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'onboarding.finish',payload:{skip:true}}),onSuccess:resolve,onFailure:(_,message)=>reject(Error(message))}))")
            finally:setup.close()
    evaluate(shell, "window.browserShell.openSettingsWindow()")
    settings = find_target("/ui/settings.html")
    assert wait_for(lambda: evaluate(settings, "Boolean(document.body?.classList.contains('ready'))"), "settings ready")
    # This visual fixture explicitly selects Blank rather than assuming the
    # product's Soulu Home default is an old blank New Tab page.
    evaluate(settings,"souluSettings.openSection('startup');const n=document.querySelector('#newTabMode');n.value='blank';n.dispatchEvent(new Event('change',{bubbles:true}))")
    evaluate(settings,'souluSettings.flush()')
    evaluate(settings, "window.souluSettings.openSection('interface')")
    evaluate(settings, 'document.querySelector(\'[name="settings-layout"][value="compact"]\').click()')
    wait_for(lambda: evaluate(shell, "document.body.dataset.layout === \'compact\'"), "compact toolbar fixture")
    # These are real change/click handlers from the settings page, not a
    # direct write to settings.json or a synthetic state injected into shell.
    evaluate(settings, """(() => {
      document.querySelector('[name="settings-theme"][value="dark"]').click();
      return true;
    })()""")
    wait_for(lambda: evaluate(shell, "document.body.dataset.theme === 'dark'"), "dark shell theme")
    evaluate(settings, """(() => {
      const checkbox = document.querySelector('#mattePanel');
      if (!checkbox.checked) checkbox.click();
      return true;
    })()""")
    wait_for(lambda: evaluate(shell, "document.body.dataset.matte === 'true'"), "matte shell")
    for key in ("vpnToolbarVisible", "showSidebar", "showBack",
                "showFavorites", "showNewTab", "showDownloads"):
        evaluate(settings, f"""(() => {{
          const control = document.querySelector('[data-setting="{key}"]');
          if (!control) throw new Error('Missing setting {key}');
          if (control.checked) control.click();
          return true;
        }})()""")
        wait_for(lambda key=key: evaluate(shell, f"document.body.dataset.{ 'showVpn' if key == 'vpnToolbarVisible' else key } === 'false'"), f"{key} hidden")
    styles = evaluate(shell, """(() => {
      const pick = selector => {
        const element = document.querySelector(selector);
        return element ? getComputedStyle(element).display : 'absent';
      };
      return {
        theme: document.body.dataset.theme,
        matte: document.body.dataset.matte,
        background: getComputedStyle(document.querySelector('.compact-toolbar')).backgroundColor,
        vpn: pick('#compactVpnButton'), sidebar: pick('#compactSidebarButton'),
        back: pick('#compactBackButton'), favorite: pick('.compact-active-tab [data-favorites]'),
        newTab: pick('#compactNewTabButton'), downloads: pick('#compactDownloadsButton')
      };
    })()""")
    print("CEF shell after settings-page interaction:", json.dumps(styles, ensure_ascii=False))
    assert styles["theme"] == "dark" and styles["matte"] == "true"
    assert styles["background"].startswith("rgba"), styles["background"]
    for key in ("vpn", "sidebar", "back", "favorite", "newTab", "downloads"):
        assert styles[key] == "none", f"{key} did not hide: {styles[key]}"
    # Check the reverse direction too: controls must reappear, not merely hide.
    for key, selector in (("vpnToolbarVisible", "#compactVpnButton"),
                          ("showSidebar", "#compactSidebarButton"),
                          ("showBack", "#compactBackButton"),
                          ("showNewTab", "#compactNewTabButton")):
        evaluate(settings, f"""(() => {{
          const control = document.querySelector('[data-setting="{key}"]');
          if (!control.checked) control.click();
          return true;
        }})()""")
        wait_for(lambda selector=selector: evaluate(shell, f"getComputedStyle(document.querySelector('{selector}')).display !== 'none'"), f"{key} restored")
    # Matte mode is painted by the native page-glass compositor; its CSS shell
    # deliberately has the same tiny alpha in both themes. Verify opaque CSS
    # colors here; test-cef-page-glass.py checks rendered matte theme pixels.
    evaluate(settings, "if(document.querySelector('#mattePanel').checked)document.querySelector('#mattePanel').click()")
    wait_for(lambda: evaluate(shell, "document.body.dataset.matte === 'false'"), "opaque toolbar")
    dark_opaque = evaluate(shell, "getComputedStyle(document.querySelector('.compact-toolbar')).backgroundColor")
    evaluate(settings, """(() => {
      document.querySelector('[name="settings-theme"][value="light"]').click();
      return true;
    })()""")
    wait_for(lambda: evaluate(shell, "document.body.dataset.theme === 'light'"), "light shell theme")
    light = evaluate(shell, "getComputedStyle(document.querySelector('.compact-toolbar')).backgroundColor")
    assert light != dark_opaque, "Opaque toolbar did not change with theme"
    evaluate(settings, """(() => {
      document.querySelector('[name="settings-theme"][value="dark"]').click();
      return true;
    })()""")
    wait_for(lambda: evaluate(shell, "document.body.dataset.theme === 'dark'"), "dark restored")
    evaluate(settings, "if(!document.querySelector('#mattePanel').checked)document.querySelector('#mattePanel').click()")
    wait_for(lambda: evaluate(shell, "document.body.dataset.matte === 'true'"), "matte restored")
    evaluate(settings, "window.souluSettings.flush()")
    persisted = evaluate(shell, """(async () => await window.browserShell.getSettings())()""")
    assert persisted["theme"] == "dark" and persisted["mattePanel"] is True
    assert persisted["vpnToolbarVisible"] is True
    evaluate(settings, "souluSettingsRequestClose()")
    wait_for(lambda:not evaluate(shell,"browserShell.getState().then(s=>s.settingsOverlayOpen)"), "Settings close before background input checks")
    # The native OSR buffer must contain actual non-opaque toolbar pixels.
    surface = evaluate(shell, "new Promise((resolve,reject)=>cefQuery({request:JSON.stringify({action:'browser.surfaceDiagnostics'}),onSuccess:s=>resolve(JSON.parse(s)),onFailure:reject}))")
    print("Native toolbar alpha:", surface)
    assert surface["windowless"] and surface["paintCount"] > 0
    assert 0 < surface["toolbarAlpha"] < 200, surface

    # Preserve the exact input node and text through native state updates.
    evaluate(shell, "(() => {const x=document.querySelector('#compactAddress');x.focus();x.value='example.org/new-address';window.testAddressNode=x;return true})()")
    evaluate(shell, "window.browserShell.setSettings({showBack:false})")
    evaluate(shell, "window.browserShell.setSettings({showBack:true})")
    time.sleep(2)
    assert evaluate(shell, "document.activeElement===window.testAddressNode && window.testAddressNode.isConnected && window.testAddressNode.value==='example.org/new-address'"), "Address focus or draft lost during state updates"
    # A domain completion must remain usable without relying on a public server.
    local = evaluate(shell, "Promise.race([window.browserShell.suggestions('example.org'),new Promise((_,reject)=>setTimeout(()=>reject(Error('suggestion timeout')),12000))])")
    assert any(row.get('url') == 'https://example.org' for row in local), local
    # Exercise OSR mouse hit testing and native key forwarding, not only DOM focus.
    import ctypes
    from ctypes import wintypes
    user=ctypes.windll.user32
    user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];user.FindWindowW.restype=wintypes.HWND
    user.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)]
    user.SetForegroundWindow.argtypes=[wintypes.HWND]
    user.GetDpiForWindow.argtypes=[wintypes.HWND]
    wanted_pid=int(os.environ.get('SOULU_TEST_PROCESS_ID','0'))
    handles=[]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowThreadProcessId.restype=wintypes.DWORD
    @callback_type
    def visit(window,unused):
        pid=wintypes.DWORD();user.GetWindowThreadProcessId(window,ctypes.byref(pid))
        name=ctypes.create_unicode_buffer(128);user.GetClassNameW(window,name,128)
        if name.value=='SouluBrowserWindow' and (not wanted_pid or pid.value==wanted_pid):handles.append(window)
        return True
    user.EnumWindows(visit,0)
    assert handles, ('Browser HWND missing for process',wanted_pid)
    hwnd=handles[0]
    user.GetForegroundWindow.restype=wintypes.HWND
    user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];user.GetAncestor.restype=wintypes.HWND
    user.WindowFromPoint.argtypes=[wintypes.POINT];user.WindowFromPoint.restype=wintypes.HWND
    user.AttachThreadInput.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.BOOL]
    current_thread=ctypes.windll.kernel32.GetCurrentThreadId()
    foreground=user.GetForegroundWindow()
    foreground_thread=user.GetWindowThreadProcessId(foreground,None) if foreground else 0
    target_thread=user.GetWindowThreadProcessId(hwnd,None)
    attached=[]
    try:
        for thread in {foreground_thread,target_thread}:
            if thread and thread!=current_thread and user.AttachThreadInput(current_thread,thread,True):attached.append(thread)
        user.ShowWindow(hwnd,9)
        user.BringWindowToTop(hwnd)
        user.SetForegroundWindow(hwnd)
    finally:
        for thread in attached:user.AttachThreadInput(current_thread,thread,False)
    time.sleep(.2)
    rect=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(rect))
    desktop_ready=user.GetForegroundWindow()==hwnd
    print('Physical desktop focus:',{'pid':wanted_pid,'hwnd':int(hwnd),'foreground':int(user.GetForegroundWindow() or 0),'ready':desktop_ready})

    pos=evaluate(shell,"(() => {const r=document.querySelector('#compactAddress').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
    scale=user.GetDpiForWindow(hwnd)/96
    point=wintypes.POINT(round(pos['x']*scale),round(pos['y']*scale))
    user.ClientToScreen(hwnd,ctypes.byref(point))
    hit=user.WindowFromPoint(point)
    desktop_ready=desktop_ready and user.GetAncestor(hit,2)==hwnd
    physical_input=False
    class GUIINFO(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('flags',wintypes.DWORD),('active',wintypes.HWND),('focus',wintypes.HWND),('capture',wintypes.HWND),('menu',wintypes.HWND),('move',wintypes.HWND),('caret',wintypes.HWND),('rect',wintypes.RECT)]
    user.GetGUIThreadInfo.argtypes=[wintypes.DWORD,ctypes.POINTER(GUIINFO)]
    user.SendMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    user.SendMessageW.restype=wintypes.LPARAM
    def native_input_state():
        gui=GUIINFO();gui.size=ctypes.sizeof(gui);user.GetGUIThreadInfo(target_thread,ctypes.byref(gui))
        def name(window):
            value=ctypes.create_unicode_buffer(128);user.GetClassNameW(window,value,128);return value.value
        return {'focus':int(gui.focus or 0),'focusClass':name(gui.focus),'hitClass':name(user.WindowFromPoint(point)),'rootHitTest':user.SendMessageW(hwnd,0x84,0,(point.y<<16)|(point.x&65535)),'dom':evaluate(shell,"({active:document.activeElement?.id,dpr:devicePixelRatio,hit:document.elementFromPoint("+str(pos['x'])+","+str(pos['y'])+")?.id})")}
    if desktop_ready:
        user.SetCursorPos(point.x,point.y)
        user.mouse_event(2,0,0,0,0);user.mouse_event(4,0,0,0,0);time.sleep(.2)
        print('Native input after click:',json.dumps(native_input_state()),flush=True)
        assert user.GetForegroundWindow()==hwnd, 'Browser lost physical desktop focus before input'
        class KEYBD(ctypes.Structure):
            _fields_=[('vk',wintypes.WORD),('scan',wintypes.WORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        class MOUSE(ctypes.Structure):
            _fields_=[('x',wintypes.LONG),('y',wintypes.LONG),('data',wintypes.DWORD),('flags',wintypes.DWORD),('time',wintypes.DWORD),('extra',ctypes.c_size_t)]
        class PAYLOAD(ctypes.Union):
            _fields_=[('keyboard',KEYBD),('mouse',MOUSE)]
        class INPUT(ctypes.Structure):
            _fields_=[('type',wintypes.DWORD),('payload',PAYLOAD)]
        user.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(INPUT),ctypes.c_int]
        def send_key(vk,flags=0,scan=0):
            value=INPUT();value.type=1;value.payload.keyboard=KEYBD(vk,scan or user.MapVirtualKeyW(vk,0),flags,0,0)
            assert user.SendInput(1,ctypes.byref(value),ctypes.sizeof(value))==1, 'Windows rejected keyboard injection'
        send_key(0x11);send_key(0x41);send_key(0x41,2);send_key(0x11,2)
        time.sleep(.05)
        for character in 'soulu test':
            send_key(0,4,ord(character));send_key(0,6,ord(character))
        time.sleep(.5)
        typed=evaluate(shell,"document.querySelector('#compactAddress').value")
        print('Native input after keys:',json.dumps(native_input_state()),flush=True)
        assert typed.lower()=='soulu test', ('Physical address input failed with confirmed foreground',typed)
        physical_input=True
    else:
        print('PHYSICAL_INPUT_UNVERIFIED: runner desktop did not foreground or hit-test the selected browser window')
    # Always test the actual CEF input surface independently of desktop policy.
    def dispatch(method,params):
        global seq
        seq+=1;ident=seq
        shell.send(json.dumps({'id':ident,'method':method,'params':params}))
        while True:
            response=json.loads(shell.recv())
            if response.get('id')!=ident:continue
            if 'error' in response:raise AssertionError(response['error'])
            return response.get('result')
    dispatch('Input.dispatchMouseEvent',dict(pos,type='mousePressed',button='left',clickCount=1))
    dispatch('Input.dispatchMouseEvent',dict(pos,type='mouseReleased',button='left',clickCount=1))
    dispatch('Input.dispatchKeyEvent',{'type':'rawKeyDown','key':'a','code':'KeyA','windowsVirtualKeyCode':65,'modifiers':2})
    dispatch('Input.dispatchKeyEvent',{'type':'keyUp','key':'a','code':'KeyA','windowsVirtualKeyCode':65,'modifiers':2})
    dispatch('Input.insertText',{'text':'soulu test'})
    wait_for(lambda:evaluate(shell,"document.querySelector('#compactAddress').value.toLowerCase()==='soulu test'"),'CEF address input')
    wait_for(lambda:evaluate(shell,"(() => {const row=document.querySelector('#compactSuggestions.visible .suggestion-row');if(!row)return false;const r=row.getBoundingClientRect();return !!document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('.suggestion-row')})()"),'Suggestions remain clickable inside CEF')
    prior=evaluate(shell,"window.browserShell.getState()")
    dispatch('Input.dispatchKeyEvent',{'type':'rawKeyDown','key':'Enter','code':'Enter','windowsVirtualKeyCode':13})
    dispatch('Input.dispatchKeyEvent',{'type':'keyUp','key':'Enter','code':'Enter','windowsVirtualKeyCode':13})
    wait_for(lambda: evaluate(shell,"window.browserShell.getState().then(s=>s.page.url.includes('soulu') && !s.page.url.includes('settings.html'))"),'typed search navigation')
    after_navigation=evaluate(shell,"window.browserShell.getState()")
    assert len(prior['tabs'])==len(after_navigation['tabs']), 'Address navigation created another tab'
    print('CEF address click, keyboard input and same-tab navigation passed; physical input verified:',physical_input)
    evaluate(shell, "window.browserShell.newTab()")
    blank = find_target('/ui/start.html')
    wait_for(lambda: evaluate(blank, "Boolean(document.body) && getComputedStyle(document.body).backgroundColor === 'rgb(8, 9, 11)'"), 'black blank tab')
    blank.close()

    # Physical pointer resize is only meaningful on an acquired desktop.
    # Deterministic native work-area/resize checks are mandatory elsewhere.
    if desktop_ready and user.GetForegroundWindow()==hwnd:
        before=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(before))
        user.SetCursorPos(before.right-2,(before.top+before.bottom)//2)
        user.mouse_event(2,0,0,0,0);time.sleep(.2)
        user.SetCursorPos(before.right-142,(before.top+before.bottom)//2);time.sleep(.5)
        user.mouse_event(4,0,0,0,0);time.sleep(.4)
        after=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(after))
        print('Mouse resize:',before.right-before.left,'->',after.right-after.left)
        assert (before.right-before.left)-(after.right-after.left)>80, 'Browser frame cannot resize by mouse'
    else:
        print('PHYSICAL_RESIZE_UNVERIFIED: selected browser does not own the runner desktop foreground')
    # Desktop-wallpaper blur was removed from the product. Its old positive
    # backdrop-response probe is intentionally replaced by mandatory
    # test-cef-page-glass.py: actual page pixels, opaque themes and desktop
    # independence. Native resize/work-area tests run separately as well.
    print("CEF settings, native alpha, input, completions and blank tab passed; physical desktop evidence is reported separately.")

finally:
    if settings: settings.close()
    shell.close()

