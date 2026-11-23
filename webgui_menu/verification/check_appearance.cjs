// Storage and document-wide behavior without opening a browser or the game.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../appearance.js'), 'utf8');
function boot(saved, blocked = false) {
  const store = new Map(saved === undefined ? [] : [['pocketmate.theme', saved]]);
  const listeners = new Map(), events = [];
  const context = {
    document: {documentElement: {dataset: {}}},
    localStorage: {
      getItem(key) {if (blocked) throw Error('unavailable'); return store.get(key) ?? null;},
      setItem(key, value) {if (blocked) throw Error('unavailable'); store.set(key, value);}
    },
    CustomEvent: class {constructor(type, options) {this.type = type; this.detail = options.detail;}},
    window: {
      addEventListener(type, fn) {listeners.set(type, fn);},
      dispatchEvent(event) {events.push(event);}
    }
  };
  vm.runInNewContext(source, context);
  return {context, store, events, storage: event => listeners.get('storage')(event), api: context.window.PocketmateTheme};
}
const fresh = boot();
assert.equal(fresh.api.get(), 'dark');
fresh.api.set('light');
assert.equal(fresh.context.document.documentElement.dataset.theme, 'light');
assert.equal(fresh.store.get('pocketmate.theme'), 'light');
assert.equal(boot(fresh.store.get('pocketmate.theme')).api.get(), 'light');
fresh.api.set('unexpected');
assert.equal(fresh.api.get(), 'light');
assert.equal(boot('corrupt').api.get(), 'dark');
const blocked = boot(undefined, true);
blocked.api.set('light');
assert.equal(blocked.api.get(), 'light');
assert.equal(blocked.context.document.documentElement.dataset.theme, 'light');
fresh.storage({key: 'unrelated', newValue: 'dark'});
assert.equal(fresh.api.get(), 'light');
fresh.storage({key: 'pocketmate.theme', newValue: 'dark'});
assert.equal(fresh.api.get(), 'dark');
fresh.storage({key: null, newValue: null});
assert.equal(fresh.context.document.documentElement.dataset.theme, 'dark');
assert.equal(fresh.events.at(-1).type, 'pocketmate:themechange');
assert.equal(fresh.events.at(-1).detail.theme, 'dark');
console.log('Appearance persistence, invalid values, unavailable storage, and shared root/event checks passed.');
