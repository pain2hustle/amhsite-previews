const assert = require('node:assert/strict');
const {status} = require('./_site/assets/open-now.js');
const cases = [
 ['2026-10-26T16:00:00Z','closed','tomorrow'], // Monday 9 AM PDT
 ['2026-10-27T15:59:59Z','closed','today'],
 ['2026-10-27T16:00:00Z','open','6 PM'],
 ['2026-10-28T00:59:59Z','open','6 PM'],
 ['2026-10-28T01:00:00Z','closed','tomorrow'],
 ['2026-10-31T14:59:59Z','closed','today'],
 ['2026-10-31T15:00:00Z','open','3 PM'],
 ['2026-10-31T22:00:00Z','closed','tomorrow'],
 ['2026-11-01T17:59:59Z','closed','today'], // DST ended, PST
 ['2026-11-01T18:00:00Z','open','4 PM'],
 ['2026-11-02T00:00:00Z','closed','Tue'],
 ['2026-11-03T16:59:59Z','closed','today'],
 ['2026-11-03T17:00:00Z','open','6 PM'],
 ['2026-03-08T16:59:59Z','closed','today'], // DST starts, PDT
 ['2026-03-08T17:00:00Z','open','4 PM'],
 ['2026-03-08T23:00:00Z','closed','Tue'],
 ['2026-10-30T07:00:00Z','closed','today']
];
for(const [time,state,fragment] of cases){const s=status(new Date(time));assert.equal(s.state,state,time);assert.ok(s.text.includes(fragment),time+': '+s.text);}
console.log('PASS',cases.length,'Pacific schedule boundaries, Monday closure, both DST transitions');
