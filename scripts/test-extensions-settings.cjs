// UI contract only. Native CEF installation still requires the Windows suite.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1020,height:800},reducedMotion:'reduce'});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
   window.extensionRequests=[];
   const snapshot={profile:'personal',settings:{language:'ru',theme:'light',performanceMode:'balanced'},rules:{defaults:{},sites:{},blocking:{enabled:true,sites:{}}},reader:{},vpn:{}};
   window.cefQuery=({request,onSuccess})=>{const data=JSON.parse(request);if(data.action==='settings.extensions')window.extensionRequests.push(data.payload);
    onSuccess(JSON.stringify(data.action==='settings.begin'?snapshot:data.action==='browser.state.get'?{activeProfileId:'personal'}:{}));};
  });
  await page.goto('file://'+path.resolve(__dirname,'../ui/settings.html'));
  await page.waitForSelector('body.ready');
  await page.evaluate(()=>souluSettings.openSection('extensions'));
  await page.waitForFunction(()=>extensionRequests.some(r=>r.visible));
  assert.equal(await page.getByRole('button',{name:'Chrome Web Store',exact:true}).count(),1);
  await page.getByRole('button',{name:'Chrome Web Store',exact:true}).click();
  await page.waitForFunction(()=>extensionRequests.some(r=>r.page==='store'));
  await page.getByRole('button',{name:'Установленные',exact:true}).click();
  await page.waitForFunction(()=>extensionRequests.some(r=>r.page==='installed'));
  await page.locator('#settingsSearch').fill('камера');
  await page.waitForFunction(()=>extensionRequests.at(-1)?.visible===false);
  await page.locator('#settingsSearch').fill('');
  await page.waitForFunction(()=>extensionRequests.at(-1)?.visible===true);
  await page.evaluate(()=>souluSettings.dialog('test',()=>{}));
  await page.waitForFunction(()=>extensionRequests.at(-1)?.visible===false);
  await page.locator('#closeAction').click();
  await page.waitForFunction(()=>extensionRequests.at(-1)?.visible===true);
  await page.evaluate(()=>souluSettings.openSection('general'));
  await page.waitForFunction(()=>extensionRequests.at(-1)?.visible===false);
  assert.deepEqual(errors,[]);
  console.log('PASS: extension navigation, embedded bounds, search, dialogs and section switching');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
