/* Native Downloads list: no second download database. */
(()=>{
const {isPrivate,PathUtils}=Soulu.backend;
const {Downloads}=ChromeUtils.importESModule('resource://gre/modules/Downloads.sys.mjs');
const {DownloadIntegration}=ChromeUtils.importESModule('resource://gre/modules/DownloadIntegration.sys.mjs');
ChromeUtils.importESModule('chrome://soulu/content/DownloadPolicy.sys.mjs').install();
const base=Soulu.dispatch,ids=new WeakMap(),byID=new Map();let next=1,list,pending=0;
function id(d){if(!ids.has(d)){ids.set(d,next);byID.set(next++,d);}return ids.get(d);}
async function rows(){return (await list.getAll()).map(d=>({id:id(d),filename:PathUtils.filename(d.target.path),url:d.source.url,receivedBytes:d.currentBytes,totalBytes:d.totalBytes,progress:d.progress,state:d.succeeded?'completed':d.error?'interrupted':d.canceled?'cancelled':'progressing',error:d.error?String(d.error.message||'Загрузка заблокирована или завершилась ошибкой.'):''}));}
function changed(){if(pending)return;pending=requestAnimationFrame(async()=>{pending=0;Soulu.native.send('downloads',await rows());});}
const view={onDownloadAdded:changed,onDownloadChanged:changed,onDownloadRemoved(d){byID.delete(ids.get(d));changed();}};
const ready=Soulu.downloadsReady=(async()=>{list=await Downloads.getList(isPrivate?Downloads.PRIVATE:Downloads.PUBLIC);await list.addView(view);})();
Soulu.dispatch=async(action,payload,source)=>{
 if(action==='browser.downloads.get'){await ready;return rows();}
 if(action==='browser.downloads.action'){
  await ready;const d=byID.get(Number(payload.id));if(!d)throw Error('Загрузка не найдена.');
  switch(payload.operation){case 'cancel':await d.cancel();await d.removePartialData();break;case 'retry':if(d.error?.becauseBlocked)throw Error('Заблокированную загрузку нужно подтвердить заново на сайте.');await d.start();break;case 'open':if(!d.succeeded)throw Error('Файл ещё не загружен.');await d.launch();break;case 'reveal':await DownloadIntegration.showContainingDirectory(d.target.path);break;case 'remove':if(!d.stopped)throw Error('Сначала отмените загрузку.');await list.remove(d);await d.finalize(true);break;default:throw Error('Unknown download action');}changed();return rows();
 }
 if(action==='browser.downloads.chooseFolder'){const path=await base('settings.chooseFolder',null,source);if(path)await base('browser.settings.set',{downloadPath:path},source);return path;}
 if(action==='settings.openFolder'){const path=await DownloadIntegration.getPreferredDownloadsDirectory();const file=Cc['@mozilla.org/file/local;1'].createInstance(Ci.nsIFile);file.initWithPath(path);file.launch();return true;}
 return base(action,payload,source);
};
window.addEventListener('unload',()=>{if(pending)cancelAnimationFrame(pending);ready.then(()=>list.removeView(view));byID.clear();},{once:true});
})();
