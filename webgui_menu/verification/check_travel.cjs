// Bridge contract only: this test never teleports a real player or opens the game.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const listeners=new Map(),sent=[],results=[],timers=new Map();let timer=0;
const sandbox={window:{webgui:{postToGame:p=>sent.push(p)},addEventListener:(name,fn)=>listeners.set(name,fn),dispatchEvent:e=>results.push(e.detail)},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options.detail;}},setTimeout:fn=>{timers.set(++timer,fn);return timer;},clearTimeout:id=>timers.delete(id)};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../travel.js'),'utf8'),sandbox);
const go=sandbox.window.PocketmateTravel.go,reply=listeners.get('webgui:pocketmate:estate');
go();assert.equal(sent.length,1);assert.equal(sent[0].action,'teleportHome');assert.deepEqual(Object.keys(sent[0]).sort(),['action','channel','requestId']);
go();assert.equal(sent.length,1);
reply({detail:{type:'travel',requestId:'someone-else'}});assert.equal(results.length,0);
reply({detail:{type:'error',requestId:sent[0].requestId,message:'소속 영지가 없습니다.'}});assert.equal(results[0].success,false);assert.equal(timers.size,0);
go();reply({detail:{type:'travel',requestId:sent[1].requestId,message:'이동 완료'}});assert.equal(results[1].success,true);
go();[...timers.values()][0]();assert.equal(results.at(-1).success,false);
delete sandbox.window.webgui;go();assert.equal(results.at(-1).success,false);
console.log('Travel bridge: no destination/identity payload, duplicate lock, response correlation, failure/success, timeout and missing bridge passed.');
