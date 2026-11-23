// Exercise the real request guards without opening Minecraft or a browser.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const assert = require('node:assert/strict');
const listeners = new Map(), sent = [];
let dialogClosed = 0;
const code = fs.readFileSync(path.join(__dirname, '../estate-app.js'), 'utf8');
assert.equal(code.split('window.PocketmateEstates={').length, 2);
const instrumented = code.replace('window.PocketmateEstates={', `
  render=()=>{};refresh=()=>{};
  window.policyCheck={
    prepare(snapshot,dimension){data=snapshot;clientDimension=dimension;busy=false;loading=false;pending.clear();selected.clear();host={querySelector:()=>({close(){window.dialogClosed();}})};},
    request:send,select(){selected.set('0:0',{x:0,z:0});},selectedCount:()=>selected.size
  };
  window.PocketmateEstates={`);
const sandbox = {
  window: {PocketmateIcons:()=>'', webgui:{postToGame:message=>sent.push(message)},
    addEventListener:(name,handler)=>listeners.set(name,handler),dialogClosed:()=>dialogClosed++},
  localStorage:{getItem:()=>null},setTimeout:()=>1,clearTimeout:()=>{},requestAnimationFrame:()=>1
};
vm.runInNewContext(instrumented, sandbox);
const policy = sandbox.window.policyCheck;
const overworld = 'minecraft:overworld';
const dimensions = [overworld, 'minecraft:the_nether', 'minecraft:the_end', 'example:custom'];
let cases = 0;
for (const dimension of dimensions) for (const inOverworld of [true,false]) {
  for (const clientDimension of [null,...dimensions]) for (const action of ['create','buy']) {
    policy.prepare({dimension,inOverworld},clientDimension);
    const before = sent.length;
    policy.request(action, {x:0,z:0});
    const allowed = dimension === overworld && inOverworld && (clientDimension === null || clientDimension === overworld);
    assert.equal(sent.length-before, allowed ? 1 : 0, JSON.stringify({dimension,inOverworld,clientDimension,action}));
    cases++;
  }
}
for (const dimension of dimensions.slice(1)) {
  policy.prepare({dimension:overworld,inOverworld:true},overworld);
  policy.select();
  const before = dialogClosed;
  listeners.get('webgui:client')({detail:{dimension}});
  assert.equal(dialogClosed,before+1);
  assert.equal(policy.selectedCount(),0);
  const requests = sent.length;
  policy.request('buy',{x:0,z:0});
  assert.equal(sent.length,requests);
}
console.log(cases + ' dimension/request cases passed; dimension changes close purchase dialogs and clear selection.');
