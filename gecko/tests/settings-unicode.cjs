const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('gecko/chrome/browser.js','utf8');
const helper=source.slice(source.indexOf('function vpnJSON('),source.indexOf('async function save()'));
const scope={};vm.createContext(scope);vm.runInContext(helper,scope);
const original={profiles:[{name:'Сервер 日本語 😀',key:'vless://unchanged',password:'секрет'}],directDomains:'пример.рф\n日本語.example'};
const ascii=scope.vpnJSON(original);assert(!/[^\x00-\x7f]/.test(ascii));assert.deepEqual(JSON.parse(ascii),original);
const legacy=JSON.stringify({profiles:[{name:'test\u0001name',key:'vless://unchanged'}]}).replace('\\u0001','\u0001');
const recovered=scope.readVPNJSON(legacy);assert(recovered.repaired);assert.equal(recovered.value.profiles[0].key,'vless://unchanged');assert.equal(recovered.value.profiles[0].name,'test\u0001name');assert.throws(()=>scope.readVPNJSON('{broken'));
console.log('PASS Unicode settings roundtrip, legacy control-byte recovery, preserved VPN key, reject unrelated malformed JSON');
