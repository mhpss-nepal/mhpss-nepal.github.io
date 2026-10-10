import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const root=new URL('../../',import.meta.url);
test('public catalogue distinguishes usability trial from field readiness',()=>{
 const html=readFileSync(new URL('learn/index.html',root),'utf8');
 const ui=JSON.parse(readFileSync(new URL('learn/assets/ui.json',root),'utf8'));
 const expected='Owner-reviewed PFA · English usability trial for teams and partners. Not a qualification or field-practice authorization.';
 assert.ok(html.includes(expected));
 for(const lang of ['en','ne']){
  assert.equal(ui[lang].catalogue_23,expected);
  assert.equal(ui[lang].catalogue_28,'English · formative practice');
 }
 assert.equal(html.includes('third-eye corrections pending'),false);
 const catalogue=JSON.parse(readFileSync(new URL('learn/content/catalogue.json',root),'utf8'));
 assert.equal(catalogue.modules.length,1);assert.equal(catalogue.modules[0].module_id,'pfa');assert.ok(html.includes('not for field practice'));assert.ok(html.includes('id="trial-boundary"'));
});
