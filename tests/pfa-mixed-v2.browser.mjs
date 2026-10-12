import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createServer} from 'node:http';
import {resolve,extname} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium, clickCourseControl} from './playwright-helper.mjs';
import demo from './fixtures/skill-loop-v2.fixture.mjs';
const root=resolve(new URL('../',import.meta.url).pathname);
const sourceBytes=fs.readFileSync(resolve(root,'learn/content/modules/pfa/0.3.1/en.json'));
assert.equal(createHash('sha256').update(sourceBytes).digest('hex'),'632ba399952e424e4c4d5bb37f164b48c432bb14c7dcc4be8ffd7ceda1d39a71');
const source=JSON.parse(sourceBytes);
function mixed(){
 const c=structuredClone(source);c.schema_version=2;c.approval.status='approved';
 // Engineering-only mixed fixture: unchanged reviewed clinical bytes plus synthetic UI blocks.
 c.sources.push(...structuredClone(demo.sources));
 const l=c.lessons[2],synthetic=structuredClone(demo.lessons[0]);
 l.blocks.unshift(...synthetic.blocks);c.scenes=structuredClone(demo.scenes);c.scenes.forEach(s=>s.status='approved');
 return c;
}
let served=mixed();
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const server=createServer((req,res)=>{
 const pathname=new URL(req.url,'http://local').pathname,raw=JSON.stringify(served),pin=hash(raw);let data,path;
 if(pathname==='/learn/content/catalogue.json')data=JSON.stringify({schema_version:1,modules:[{module_id:'pfa',content_version:served.content_version,language:'en',path:`modules/pfa/${served.content_version}/en.json`,sha256:pin}]});
 else if(pathname.endsWith(`/modules/pfa/${served.content_version}/en.json`))data=raw;
 else {path=pathname.startsWith('/learn/assets/scenes/')?resolve(root,'tests/fixtures/skill-loop-v2/assets',pathname.slice('/learn/assets/scenes/'.length)):resolve(root,'.'+pathname);if(pathname.endsWith('/'))path+='/index.html';try{data=fs.readFileSync(path);if(path.endsWith('/skill-loop-v2.js'))data=data.toString().replace(/const PUBLIC_RENDITION_PINS=Object\.freeze\(\[[^\]]*\]\);/,`const PUBLIC_RENDITION_PINS=Object.freeze(['${pin}']);`);}catch{res.writeHead(404).end();return;}}
 res.setHeader('Content-Type',({'.js':'text/javascript','.json':'application/json','.html':'text/html','.css':'text/css','.webp':'image/webp'})[extname(path||pathname)]||'application/json');res.end(data);
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true,});
async function open(){const p=await browser.newPage({viewport:{width:390,height:900}});p.setDefaultTimeout(4000);await p.goto(`http://127.0.0.1:${server.address().port}/learn/`);await p.waitForSelector('body[data-ready]');await p.locator('[data-module-launch="pfa"]').click();await p.waitForSelector('#lesson-title');return p;}
try{
 await test('mixed v2 preserves complete guided legacy four, synthetic Lesson 3 Skill Loop and separate scored quiz',async()=>{
  served=mixed();const p=await open();
  for(const index of [0,1,3,4]){
   const l=source.lessons[index];await clickCourseControl(p,`[data-lesson="${l.lesson_id}"]`);
   assert.equal(await p.locator('#step-picker').count(),1,`${l.lesson_id} must retain guided experience`);
   const count=await p.locator('#step-picker option').count(),seen=new Set();
   for(let step=0;step<count;step++){
    await p.locator('#step-picker').selectOption(String(step));
    for(const id of await p.locator('[data-source-block]').evaluateAll(es=>es.map(e=>Number(e.dataset.sourceBlock))))seen.add(id);
    for(const id of await p.locator('#course-content [data-question]').evaluateAll(es=>es.map(e=>e.dataset.question))){const question=source.questions.find(q=>q.question_id===id);await p.locator(`input[name="${id}"][value="${question.correct_option_id}"]`).check();await p.locator('[data-check]').click();assert.ok(await p.locator('[data-rationale]').count()>0);}
   }
   const recap=await p.locator('#course-content').innerText();
   for(const [i,b] of l.blocks.entries())if(b.type==='safety'||b.body.startsWith('Key points.'))assert.ok(recap.includes(b.body));else assert.ok(seen.has(i),`${l.lesson_id} source block ${i} retained`);
   await p.locator('#mark-read').click();await p.locator('#lesson-menu > summary').click();assert.match(await p.locator(`[data-lesson="${l.lesson_id}"]`).innerText(),/read/);
  }
  await clickCourseControl(p,'[data-lesson="pfa-03"]');assert.equal(await p.locator('#skill-loop-phases').count(),1);
  for(const [phase,type] of [['1','scene_tap'],['0','contrast_pair'],['4','buddy_practice']]){await p.locator('#skill-loop-phases').selectOption(phase);assert.equal(await p.locator(`[data-block="${type}"]`).count(),1);}
  await p.locator('#skill-loop-phases').selectOption('6');await p.locator('#mark-read').click();
  await clickCourseControl(p,'#quiz-entry');assert.equal(await p.locator('#quiz-content fieldset').count(),10);
  for(const q of source.questions)await p.locator(`input[name="${q.question_id}"][value="${q.correct_option_id}"]`).check();
  await p.locator('#quiz-submit').click();assert.match(await p.locator('#quiz-result').innerText(),/10\/10.*100%/);await p.close();
 });
 await test('all five unchanged v2 lessons match their explicit semantic baselines',async()=>{
  served=structuredClone(source);served.schema_version=2;served.approval.status='approved';const p=await open();
  for(const l of source.lessons){await clickCourseControl(p,`[data-lesson="${l.lesson_id}"]`);assert.equal(await p.locator('#step-picker').count(),1,l.lesson_id);assert.equal(await p.locator('#skill-loop-phases').count(),0);}
  await p.close();
 });
 await test('semantic parity refuses changed lesson, question, rationale, safety or cited source even under test pin',async()=>{
  for(const change of ['body','order','objective','question','rationale','safety','source','scope']){
   served=mixed();let id='pfa-01';
   if(change==='body')served.lessons[0].blocks[0].body+=' Changed.';
   if(change==='order')served.lessons[0].blocks.reverse();
   if(change==='objective'){served.objectives.push('Changed objective');served.lessons[0].objective='Changed objective';}
   if(change==='question')served.questions[0].prompt+=' Changed.';
   if(change==='rationale')served.questions[0].options[0].rationale+=' Changed.';
   if(change==='safety'){id='pfa-04';served.lessons[2].blocks.find(b=>b.body===source.lessons[2].blocks[9].body).body+=' Changed.';}
   if(change==='source')served.sources[0].location+=' Changed.';
   if(change==='scope')served.scope_limits[0]+=' Changed.';
   const p=await open();await clickCourseControl(p,`[data-lesson="${id}"]`);assert.equal(await p.locator('#step-picker').count(),0,change+' must not reuse reviewed guidance');assert.equal(await p.locator('#skill-loop-phases').count(),0);assert.ok(await p.locator('#course-content [data-block]').count()>0);await p.close();
  }
 });
 await test('explicit legacy block IDs preserve parity without loosening lesson or question semantics',async()=>{
  served=mixed();for(const l of served.lessons)for(const [i,b] of l.blocks.entries())if(!b.block_id)b.block_id=`${l.lesson_id}-original-${i}`;
  const p=await open();assert.equal(await p.locator('#step-picker').count(),1);await clickCourseControl(p,'[data-lesson="pfa-04"]');assert.equal(await p.locator('#step-picker').count(),1);
  const options=await p.locator('#step-picker option').allTextContents();await p.locator('#step-picker').selectOption(String(options.findIndex(t=>t.includes('Practise another'))));assert.ok((await p.locator('.decision-safety').innerText()).includes(source.lessons[2].blocks[9].body));await p.close();
 });
}finally{await browser.close();await new Promise(r=>server.close(r));}
