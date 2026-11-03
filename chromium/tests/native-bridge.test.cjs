const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../ui/native-bridge.js'), 'utf8');

function host(overrides = {}) {
  const sent = [], timers = new Map();
  let timer = 0;
  const context = {
    location: {protocol: 'chrome:', host: 'webui-browser'},
    chrome: {send: (...args) => sent.push(args)},
    setTimeout: callback => { timers.set(++timer, callback); return timer; },
    clearTimeout: id => timers.delete(id),
    addEventListener: () => {},
    ...overrides,
  };
  context.window = context;
  context.top = context;
  vm.runInNewContext(source, context);
  return {context, sent, timers};
}

test('ordinary web pages receive no privileged bridge', () => {
  for (const location of [
    {protocol: 'https:', host: 'webui-browser'},
    {protocol: 'chrome:', host: 'settings'},
  ]) {
    const {context, sent} = host({location});
    assert.equal(context.cefQuery, undefined);
    assert.equal(sent.length, 0);
  }
});
test('responses match requests even when native replies arrive out of order', () => {
  const {context, sent, timers} = host();
  const values = [];
  for (const action of ['browser.state.get', 'browser.settings.get']) {
    context.cefQuery({request: JSON.stringify({action}),
      onSuccess: value => values.push([action, JSON.parse(value)])});
  }
  context.souluChromiumReply(sent[1][1][0], true, {theme: 'dark'});
  context.souluChromiumReply(sent[0][1][0], true, {tabs: []});
  assert.deepEqual(values.map(v => v[0]), ['browser.settings.get', 'browser.state.get']);
  assert.equal(timers.size, 0);
});
test('native failures and timeouts never resolve as successful functionality', () => {
  const {context, sent, timers} = host();
  const failures = [];
  let successes = 0;
  const query = () => context.cefQuery({request: '{"action":"vpn.send"}',
    onSuccess: () => successes++, onFailure: (code, message) => failures.push([code, message])});
  query();
  context.souluChromiumReply(sent[0][1][0], false, 'Not implemented');
  query();
  [...timers.values()][0]();
  assert.equal(successes, 0);
  assert.deepEqual(failures.map(v => v[0]), [501, 408]);
});
test('malformed and persistent requests never reach native handlers', () => {
  const {context, sent} = host();
  let errors = 0;
  for (const request of ['broken', 'null', '{}']) {
    context.cefQuery({request, onFailure: () => errors++});
  }
  context.cefQuery({request: '{}', persistent: true, onFailure: () => errors++});
  assert.equal(errors, 4);
  assert.equal(sent.length, 0);
});
test('state subscription can be removed', () => {
  const {context} = host();
  let count = 0;
  const remove = context.souluChromiumOnState(() => count++);
  context.souluChromiumState({});
  remove();
  context.souluChromiumState({});
  assert.equal(count, 1);
});
