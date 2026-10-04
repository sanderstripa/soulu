const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),{webcrypto}=require('node:crypto');
const context=vm.createContext({window:{},crypto:webcrypto,ArrayBuffer,Uint8Array,AbortController,Blob,Response,DecompressionStream,URL,fetch,indexedDB:{},console});
context.window.SouluBergamot={TranslatorBacking:class{},BatchTranslator:class{}};
for(const file of ['ui/translation-models.js','ui/third_party/tinyld.js','ui/translation-service.js'])vm.runInContext(fs.readFileSync(file,'utf8'),context);
const s=context.window.SouluTranslate;
assert.equal(s.normalize('EN_us'),'en');assert.equal(s.resolve('en','ru').length,1);assert.equal(s.resolve('de','ru').length,2);assert.equal(s.resolve('ru','ru').length,0);assert.throws(()=>s.resolve('zh','ru'));
assert.equal(s.detect('This is an English article about local page translation, browsers and their menus.','ru'),'en');assert.equal(s.detect('Это русская статья о локальном переводе веб-страниц и настройках браузера.','en'),'ru');assert.equal(s.detect('Das ist eine deutsche Seite über die lokale Übersetzung und die Einstellungen des Browsers.','en'),'de');
(async()=>{const b=new TextEncoder().encode('fixture').buffer;assert.equal(await s.verify(b,{size:7,sha256:'invalid'}),false);console.log('PASS: pair resolution, pivot, unsupported language, wrong HTML lang, integrity rejection');})();
