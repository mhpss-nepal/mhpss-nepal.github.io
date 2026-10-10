import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const root=new URL('../../',import.meta.url);
test('public catalogue accurately separates completed review from pending publication',()=>{
 const html=readFileSync(new URL('learn/index.html',root),'utf8');
 const ui=JSON.parse(readFileSync(new URL('learn/assets/ui.json',root),'utf8'));
 const expected='Content review complete; publication pending. No clinical course is enabled.';
 assert.ok(html.includes(expected));
 for(const lang of ['en','ne']){
  assert.equal(ui[lang].catalogue_23,expected);
  assert.equal(ui[lang].catalogue_28,'Publication pending');
 }
 assert.equal(html.includes('third-eye corrections pending'),false);
 const catalogue=JSON.parse(readFileSync(new URL('learn/content/catalogue.json',root),'utf8'));
 assert.deepEqual(catalogue,{schema_version:1,modules:[]});
});
