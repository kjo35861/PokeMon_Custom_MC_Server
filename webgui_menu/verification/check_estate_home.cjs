// Settings rendering/visibility contract; server authority is covered by EstateHomeTest.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../estate-app.js'),'utf8').replace('  window.PocketmateEstates={',`  window.homeCheck={prepare(value,dimension){data=value;clientDimension=dimension;busy=false;tab='settings';},settings:settingsPage,nav};\n  window.PocketmateEstates={`);
const sandbox={window:{PocketmateIcons:()=>'',addEventListener(){}},localStorage:{getItem:()=>null}};
vm.runInNewContext(source,sandbox);
const ui=sandbox.window.homeCheck,overworld='minecraft:overworld';
const lord={hasEstate:true,isLord:true,inOverworld:true,dimension:overworld,canSetHome:true,home:{surface:false}};
ui.prepare(lord,overworld);
assert.match(ui.nav(),/영지 설정/);assert(!ui.nav().includes('data-estate-tab="history"'));
let html=ui.settings();assert.match(html,/data-estate-travel-home/);assert.match(html,/data-estate-set-home >/);
ui.prepare({...lord,isLord:false},overworld);html=ui.settings();assert(!html.includes('data-estate-set-home'));assert.match(html,/영주만 변경/);
ui.prepare(lord,'minecraft:the_nether');assert.match(ui.settings(),/data-estate-set-home disabled/);
ui.prepare({...lord,canSetHome:false},overworld);assert.match(ui.settings(),/data-estate-set-home disabled/);
ui.prepare({hasEstate:false},overworld);assert(!ui.settings().includes('data-estate-travel-home'));
console.log('Estate settings: history removed, member travel, lord-only setter, dimension/ownership disable and no-estate state passed.');
