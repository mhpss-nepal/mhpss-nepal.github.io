import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root=new URL('../',import.meta.url);
const engine=readFileSync(new URL('learn/assets/engine.js',root),'utf8');
test('guided PFA is bound to the unchanged reviewed rendition and retains fallback',()=>{
 assert.match(engine,/function renderGuided/);
 assert.match(engine,/632ba399952e424e4c4d5bb37f164b48c432bb14c7dcc4be8ffd7ceda1d39a71/);
 assert.match(engine,/function renderReferenceReader/);
 assert.match(engine,/function validate\(c\)/);
 assert.match(engine,/generation!==openGeneration/);
});
test('five reusable human scenes have verified public bytes and no private paths',()=>{
 const m=JSON.parse(readFileSync(new URL('assets/iec/pfa-learning-v1/provenance.json',root)));
 assert.equal(m.assets.length,5);
 assert.equal(JSON.stringify(m).includes('/root/'),false);
 assert.equal(JSON.stringify(m).includes('/Users/'),false);
 for(const a of m.assets){const p=new URL('assets/iec/pfa-learning-v1/'+a.file,root);assert.ok(existsSync(p));assert.equal(createHash('sha256').update(readFileSync(p)).digest('hex'),a.sha256);assert.ok(a.alt.length>30);}
});
