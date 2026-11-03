"""Open a second real portable profile through Soulu UI and check native isolation."""
pid=call('browser.profile.create','Independent browser fixture')['id'];directory=profile.parent/pid
with socket.socket() as sock:sock.bind(('127.0.0.1',0));profile_port=sock.getsockname()[1]
(directory/'user.js').write_text('user_pref("remote.prefs.recommended",false);user_pref("marionette.port",'+str(profile_port)+');',encoding='utf-8')
call('browser.profile.switch',pid)
child=None
try:
 def ready_profile():
  try:
   with socket.create_connection(('127.0.0.1',profile_port),timeout=.2):return True
  except OSError:return False
 wait(ready_profile,60);child=Marionette('127.0.0.1',port=profile_port,socket_timeout=40);child.start_session();child.set_context('chrome');child.timeout.script=60
 wait(lambda:child.execute_script('return !!window.Soulu?.ready'))
 def child_call(action,payload=None):
  result=child.execute_async_script('const done=arguments[0];Soulu.dispatch('+json.dumps(action)+','+json.dumps(payload)+').then(done,e=>done({error:String(e)}));')
  if isinstance(result,dict) and 'error' in result:raise AssertionError(result)
  return result
 check('second_profile_uses_own_directory',child.execute_script('return PathUtils.profileDir')==str(directory))
 check('second_profile_places_and_nss_isolated',not any('soulu-fixture' in r['url'] for r in child_call('browser.bookmarks.get')) and child_call('history.query',{'search':'soulu-fixture'})['rows']==[] and child_call('browser.passwords.get')==[])
 child_call('browser.settings.set',{'theme':'light'});check('second_profile_settings_isolated',call('browser.settings.get')['theme']!='light')
 child_call('browser.navigate',url);child.set_context('content');wait(lambda:child.execute_script('return !!document.getElementById("v")'))
 check('second_profile_cookie_storage_isolated',child.execute_script('return !localStorage.getItem("soulu-isolation")&&!document.cookie.includes("soulu_isolation")'))
 child.execute_script('localStorage.setItem("soulu-isolation","other-profile");return true;')
 check('second_profile_does_not_mutate_first',content('return localStorage.getItem("soulu-isolation")==="normal"'))
 try:call('browser.profile.delete',pid);locked=False
 except AssertionError:locked=True
 check('running_profile_cannot_be_deleted',locked and directory.exists())
finally:
 if child:
  try:child.quit()
  except Exception:pass
 def delete_closed_profile():
  try:call('browser.profile.delete',pid);return True
  except Exception:return False
 wait(delete_closed_profile,30)
check('closed_profile_deletes_with_native_lock',not directory.exists())
