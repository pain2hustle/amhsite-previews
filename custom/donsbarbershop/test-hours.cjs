const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync(__dirname+'/_site/assets/open-now.js','utf8');
const {status,zone,week}=require('./_site/assets/open-now.js');
assert.equal(zone,'America/Los_Angeles');assert.equal(week[1],null);
const cases=[
 ['2026-10-25T22:59:59Z','open','Open now · until 4 PM'],
 ['2026-10-25T23:00:00Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-10-26T00:00:00Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-10-26T06:59:59Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-10-26T07:00:00Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-10-26T16:00:00Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-10-27T06:59:59Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-10-27T07:00:00Z','closed','Closed · opens 9 AM today'],
 ['2026-10-27T15:59:59Z','closed','Closed · opens 9 AM today'],
 ['2026-10-27T16:00:00Z','open','Open now · until 6 PM'],
 ['2026-10-28T00:59:59Z','open','Open now · until 6 PM'],
 ['2026-10-28T01:00:00Z','closed','Closed · opens Wednesday at 9 AM'],
 ['2026-10-31T14:59:59Z','closed','Closed · opens 8 AM today'],
 ['2026-10-31T15:00:00Z','open','Open now · until 3 PM'],
 ['2026-10-31T22:00:00Z','closed','Closed · opens Sunday at 10 AM'],
 ['2026-11-01T08:59:59Z','closed','Closed · opens 10 AM today'],
 ['2026-11-01T09:00:00Z','closed','Closed · opens 10 AM today'],
 ['2026-11-01T17:59:59Z','closed','Closed · opens 10 AM today'],
 ['2026-11-01T18:00:00Z','open','Open now · until 4 PM'],
 ['2026-11-02T00:00:00Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-11-02T07:59:59Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-11-02T08:00:00Z','closed','Closed · opens Tuesday at 9 AM'],
 ['2026-11-03T16:59:59Z','closed','Closed · opens 9 AM today'],
 ['2026-11-03T17:00:00Z','open','Open now · until 6 PM'],
 ['2026-03-08T09:59:59Z','closed','Closed · opens 10 AM today'],
 ['2026-03-08T10:00:00Z','closed','Closed · opens 10 AM today'],
 ['2026-03-08T16:59:59Z','closed','Closed · opens 10 AM today'],
 ['2026-03-08T17:00:00Z','open','Open now · until 4 PM'],
 ['2026-03-08T23:00:00Z','closed','Closed · opens Tuesday at 9 AM']
];
assert.equal((fs.readFileSync(__dirname+'/_site/index.html','utf8').match(/data-open-now=/g)||[]).length,3);
for(const [iso,state,text] of cases){
 assert.deepEqual(status(new Date(iso)),{state,text},iso);
 const nodes=Array.from({length:3},()=>({classes:new Set(),label:{textContent:''},querySelector(s){assert.equal(s,'.on-text');return this.label},classList:{toggle(){}}}));
 nodes.forEach(n=>n.classList.toggle=(k,on)=>on?n.classes.add(k):n.classes.delete(k));
 let tick,visibility;let time=iso;
 class FakeDate extends Date{constructor(...args){super(...(args.length?args:[time]))}}
 const ctx={Date:FakeDate,Intl,Object,String,Number,Math,window:{},setInterval(fn,ms){assert.equal(ms,30000);tick=fn},document:{hidden:false,querySelectorAll(s){assert.equal(s,'[data-open-now]');return nodes},addEventListener(s,fn){assert.equal(s,'visibilitychange');visibility=fn}}};
 vm.runInNewContext(code,ctx);
 for(const n of nodes){assert.equal(n.label.textContent,text);assert.deepEqual([...n.classes],['is-'+state]);assert.ok(!/\bPT\b|tomorrow/.test(n.label.textContent));}
 time='2026-10-27T16:00:00Z';tick();visibility();
 for(const n of nodes){assert.equal(n.label.textContent,'Open now · until 6 PM');assert.deepEqual([...n.classes],['is-open']);}
}
console.log(`PASS ${cases.length} exact Pacific/DST/UTC-midnight cases; all three indicator texts/classes and refresh handlers consistent`);
