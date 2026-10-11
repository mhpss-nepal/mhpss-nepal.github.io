import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, mkdirSync, writeFileSync} from 'node:fs';
import {createServer} from 'node:http';
import {resolve, extname} from 'node:path';
import {chromium} from '/root/.hermes/outputs/mhpss-learning-architecture/prototype-build/learn-demo/node_modules/playwright/index.mjs';
const root=resolve(new URL('../',import.meta.url).pathname);
const course=JSON.parse(readFileSync(root+'/learn/content/modules/pfa/0.3.1/en.json'));
const evidence=resolve(root,'../implementation-evidence');mkdirSync(evidence,{recursive:true});
const server=createServer((req,res)=>{let path=resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://local').pathname));if(path.endsWith('/learn'))path+='/';if(path.endsWith('/'))path+='index.html';if(!path.startsWith(root+'/')){res.writeHead(403).end();return;}try{const data=readFileSync(path);res.setHeader('Content-Type',({'.js':'text/javascript','.css':'text/css','.json':'application/json','.html':'text/html','.webp':'image/webp'})[extname(path)]||'application/octet-stream');res.end(data);}catch{res.writeHead(404).end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}/learn/`;
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome'});
process.on('exit',()=>server.close());
async function page(){const p=await browser.newPage();await p.goto(base+'?view=quiz');await p.waitForSelector('body[data-ready]');return p;}
try{
await test('dedicated quiz scores only a complete independent attempt, invalidates on edit and retries cleanly',async()=>{
 const p=await page();await p.waitForSelector('#quiz-submit',{timeout:3000});
 assert.equal(await p.locator('#quiz-content fieldset').count(),10);
 assert.deepEqual(await p.locator('#quiz-content legend').allTextContents(),course.questions.map(q=>q.prompt));
 assert.deepEqual(await p.locator('#quiz-content .option span').allTextContents(),course.questions.flatMap(q=>q.options.map(o=>o.text)));
 assert.equal(await p.locator('#quiz-content input:checked').count(),0);
 assert.equal(await p.locator('.trial-details').count(),1);
 assert.equal(await p.locator('[data-rationale]').count(),0);
 await p.locator('#quiz-submit').click();assert.match(await p.locator('#quiz-error').innerText(),/1.*2.*10/);assert.equal(await p.evaluate(()=>document.activeElement.name),course.questions[0].question_id);
 for(const q of course.questions)await p.locator(`input[name="${q.question_id}"][value="${q.correct_option_id}"]`).check();
 await p.locator('#quiz-submit').click();assert.match(await p.locator('#quiz-result').innerText(),/10\/10.*100%/);await p.screenshot({path:evidence+'/quiz-score-10.png',fullPage:true});assert.equal(await p.locator('[data-rationale]').count(),40);assert.deepEqual(await p.locator('[data-rationale] p').allTextContents(),course.questions.flatMap(q=>q.options.map(o=>o.rationale)));
 const q=course.questions[0],wrong=q.options.find(o=>o.option_id!==q.correct_option_id);await p.locator(`input[name="${q.question_id}"][value="${wrong.option_id}"]`).check();assert.equal(await p.locator('[data-rationale]').count(),0);assert.doesNotMatch(await p.locator('#quiz-result').innerText(),/100%/);
 await p.locator('#quiz-submit').click();assert.match(await p.locator('#quiz-result').innerText(),/9\/10.*90%/);
 await p.locator('#quiz-retry').click();assert.equal(await p.locator('#quiz-content input:checked').count(),0);
 await p.locator(`input[name="${q.question_id}"][value="${q.correct_option_id}"]`).check();await p.locator('#quiz-submit').click();assert.match(await p.locator('#quiz-error').innerText(),/2.*10/);
 await p.locator('#quiz-retry').click();for(const q of course.questions){const w=q.options.find(o=>o.option_id!==q.correct_option_id);await p.locator(`input[name="${q.question_id}"][value="${w.option_id}"]`).check();}await p.locator('#quiz-submit').click();assert.match(await p.locator('#quiz-result').innerText(),/0\/10.*0%/);
 await p.reload();await p.waitForSelector('#quiz-submit');assert.equal(await p.locator('#quiz-content input:checked').count(),0);
 await p.locator('#quiz-return').click();await p.waitForSelector('#step-title');assert.equal(new URL(p.url()).searchParams.has('view'),false);
 await p.close();
});
await test('all five lessons teach a reviewed model and varied source activities with atomic consent and complete reading',async()=>{
 const p=await page();await p.locator('#quiz-return').click();
 for(const [i,l] of course.lessons.entries()){
  await p.locator(`[data-lesson="${l.lesson_id}"]`).click();
  assert.equal(await p.locator('.decision-grid img').count(),i===1?1:0,'only reviewed preparation context is bound to its question');
  if(i===1){assert.match(await p.locator('.decision-grid img').getAttribute('src'),/pfa-learning-v2\/preparation-landslide\.webp$/);await p.waitForFunction(()=>document.querySelector('.decision-grid img').complete&&document.querySelector('.decision-grid img').naturalWidth>0);}
  await p.locator('#step-next').click();assert.equal(await p.locator('[data-activity="model"]').count(),1);
  const model=l.blocks.find(b=>b.type==='example');assert.equal((await p.locator('.model-sequence [data-source-excerpt]').allInnerTexts()).join(' ').replace(/\s+/g,' ').trim(),model.body.replace(/\s+/g,' ').trim());
  assert.ok(await p.locator('.model-cue').count()>=3);assert.ok(await p.locator('.model-sequence > li').count()<=5);
  assert.equal(await p.locator('.lesson-goal[open]').count(),0);
  const options=await p.locator('#step-picker option').evaluateAll(es=>es.map(e=>({value:e.value,text:e.textContent})));
  assert.ok(options.some(o=>/Compare|Checklist|Observe/.test(o.text)));
  if(i===3){const consent=options.find(o=>o.text.includes('Consent and confidentiality'));await p.locator('#step-picker').selectOption(consent.value);assert.equal(await p.locator('[data-source-block="6"]').innerText().then(t=>t.includes(l.blocks[6].body)),true);assert.equal(options.filter(o=>o.text.includes('Consent and confidentiality')).length,1);}
  await p.locator('#step-picker').selectOption(options.at(-1).value);assert.equal(await p.locator('[data-activity="recap"]').count(),1);for(const b of l.blocks.filter(b=>b.type==='safety'))assert.ok((await p.locator('#course-content').innerText()).includes(b.body));
 }
 await p.locator('#full-reference').click();let count=0;for(const l of course.lessons){await p.locator(`[data-lesson="${l.lesson_id}"]`).click();const blocks=await p.locator('[data-block]').allInnerTexts();assert.equal(blocks.length,l.blocks.length);for(const b of l.blocks)assert.ok(blocks.some(t=>t.includes(b.body)));count+=blocks.length;}assert.equal(count,49);
 await p.close();
});
await test('quiz entry and retry preserve opted-in course practice while catalogue navigation exits quiz route',async()=>{
 const p=await page();await p.locator('#quiz-return').click();await p.locator('#learning-tools > summary').click();await p.locator('#save-progress').check();const q=course.questions[0];await p.locator(`input[name="${q.question_id}"][value="${q.correct_option_id}"]`).check();await p.locator('[data-check]').click();const before=await p.evaluate(()=>JSON.stringify(localStorage));
 await p.locator('#quiz-entry').click();assert.equal(await p.locator('#quiz-content input:checked').count(),0);assert.equal(await p.locator('[data-rationale]').count(),0);await p.locator('#quiz-retry').click();assert.equal(await p.evaluate(()=>JSON.stringify(localStorage)),before);await p.locator('#quiz-return').click();assert.equal(await p.locator('input:checked').first().inputValue(),q.correct_option_id);assert.ok(await p.locator('[data-rationale]').count()>0);
 await p.locator('#quiz-entry').click();await p.locator('.nav a[href="#catalogue"]').click();assert.equal(new URL(p.url()).searchParams.has('view'),false);await p.reload();await p.waitForSelector('body[data-ready]');assert.equal(await p.locator('#quiz-submit').count(),0);await p.close();
});
await test('phone and desktop journey has readable activities, real Tab navigation, theme and locale support',async()=>{
 const measurements=[];
 for(const width of [320,390,1280])for(const theme of ['light','dark']){
  const p=await page();await p.setViewportSize({width,height:900});await p.evaluate(t=>document.documentElement.dataset.theme=t,theme);await p.locator('#quiz-return').click();
  for(const [li,l] of course.lessons.entries()){
   await p.locator(`[data-lesson="${l.lesson_id}"]`).click();
   const positions=await p.locator('#step-picker option').evaluateAll(es=>es.map(e=>e.value));
   for(const position of positions){await p.locator('#step-picker').selectOption(position);const measure=await p.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,font:parseFloat(getComputedStyle(document.querySelector('#course-content')).fontSize),step:document.querySelector('#step-title').textContent,colors:[...document.querySelectorAll('.model-cue,.model-sequence p,.source-comparison p,.action-checklist li,.activity-task')].map(e=>{let b=e;while(b.parentElement&&getComputedStyle(b).backgroundColor==='rgba(0, 0, 0, 0)')b=b.parentElement;return {text:getComputedStyle(e).color,background:getComputedStyle(b).backgroundColor};})}));assert.equal(measure.scroll,width,`${width} ${theme} ${l.lesson_id} ${position}`);assert.equal(measure.font,width<=700?19:21);measurements.push({...measure,theme,lesson:l.lesson_id});}
  }
  await p.locator('[data-lesson="pfa-03"]').click();
  for(const [name,pos] of [['question','0'],['model','1'],['recap',String(await p.locator('#step-picker option').count()-1)]]){await p.locator('#step-picker').selectOption(pos);await p.locator('#step-title').scrollIntoViewIfNeeded();await p.screenshot({path:`${evidence}/${name}-${width}-${theme}.png`,fullPage:true});}
  await p.locator('#quiz-entry').click();await p.locator('#quiz-submit').click();assert.equal(await p.evaluate(()=>document.activeElement.name),'pfa-q01');await p.keyboard.press('Tab');assert.ok(await p.evaluate(()=>document.activeElement.getBoundingClientRect().width>0));
  await p.locator('#locale').selectOption('ne');assert.equal(await p.locator('#quiz-content').getAttribute('lang'),'en');assert.match(await p.locator('#reader-root').innerText(),/Reviewed Nepali course content is not available/);
  await p.locator('#locale').selectOption('en');await p.locator('#quiz-return').click();await p.locator('#step-picker').selectOption('1');await p.locator('#step-title').focus();const focused=[];for(let i=0;i<8;i++){await p.keyboard.press('Tab');focused.push(await p.evaluate(()=>({tag:document.activeElement.tagName,text:document.activeElement.textContent.slice(0,80),outline:getComputedStyle(document.activeElement).outlineStyle})));}assert.ok(focused.some(f=>f.tag==='SUMMARY'));assert.ok(focused.filter(f=>f.tag!=='BODY').every(f=>f.outline!=='none'),JSON.stringify(focused));await p.close();
 }
 writeFileSync(evidence+'/geometry.json',JSON.stringify(measurements,null,2));
});
await test('hash mismatch closes quiz before exposing questions or score',async()=>{
 const p=await browser.newPage();await p.route('**/content/modules/pfa/0.3.1/en.json',async route=>{const response=await route.fetch();await route.fulfill({response,body:(await response.text())+' '});});await p.goto(base+'?view=quiz');await p.waitForSelector('#retry:not([hidden])');assert.equal(await p.locator('#quiz-submit').count(),0);assert.equal(await p.locator('[data-question]').count(),0);await p.close();
});
}finally{await browser.close();await new Promise(r=>server.close(r));}
