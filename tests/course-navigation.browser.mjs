import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createServer} from 'node:http';
import {resolve,extname} from 'node:path';
import {chromium} from './playwright-helper.mjs';
const root=resolve(new URL('../',import.meta.url).pathname),out=resolve(process.env.UI_EVIDENCE_DIR||resolve(root,'../implementation/screenshots'));
fs.mkdirSync(out,{recursive:true});
const server=createServer((req,res)=>{let p=resolve(root,'.'+new URL(req.url,'http://local').pathname);if(fs.existsSync(p)&&fs.statSync(p).isDirectory())p=resolve(p,'index.html');try{res.setHeader('Content-Type',({'.js':'text/javascript','.json':'application/json','.html':'text/html','.css':'text/css','.webp':'image/webp'})[extname(p)]||'application/octet-stream');res.end(fs.readFileSync(p));}catch{res.writeHead(404).end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true});
const course=JSON.parse(fs.readFileSync(resolve(root,'learn/content/modules/pfa/0.4.1/en.json')));
const observations=[];
async function position(p,lesson){const rail=p.locator('.course-position');assert.ok(await rail.isVisible());assert.match(await rail.innerText(),new RegExp(`Lesson ${lesson} of 5`));const geometry=await rail.boundingBox();assert.ok(geometry.y>=0&&geometry.y+geometry.height<=900);assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);}
try{await test('ordinary forward journey finishes reading only, crosses Skill Loop, scores quiz and returns',async()=>{
 for(const width of [390,320,1280])for(const theme of ['light','dark']){
  const p=await browser.newPage({viewport:{width,height:900}});await p.route('https://fonts.googleapis.com/**',r=>r.abort());await p.goto(`http://127.0.0.1:${server.address().port}/learn/`);await p.waitForSelector('body[data-ready]');if(theme==='dark')await p.locator('#theme').click();await p.locator('[data-module-launch="pfa"]').click();
  for(let lesson=1;lesson<=5;lesson++){
   await position(p,lesson);assert.match(await p.locator('.course-position').innerText(),/Step 1 of/);const task=p.locator('#course-content fieldset legend,.contrast_pair h3').first();const taskBox=await task.boundingBox();assert.ok(taskBox.y>=0&&taskBox.y+taskBox.height<=900,JSON.stringify({width,theme,lesson,taskBox}));await p.screenshot({path:resolve(out,`${width}-${theme}-lesson${lesson}-entry.png`)});
   const summary=p.locator('#lesson-menu > summary');await p.keyboard.press('Shift+Tab');for(let tab=0;tab<80&&await p.evaluate(()=>document.activeElement?.parentElement?.id!=='lesson-menu');tab++)await p.keyboard.press('Tab');assert.equal(await p.evaluate(()=>document.activeElement?.parentElement?.id),'lesson-menu');await p.keyboard.press('Enter');assert.equal(await p.locator('#lesson-menu [data-lesson]').count(),5);assert.match(await p.locator('#lesson-menu [aria-current="step"]').innerText(),new RegExp(`${lesson}\\.`));await p.keyboard.press('Enter');
   if(lesson===3)assert.deepEqual(await p.locator('#skill-loop-phases option').allTextContents(),['View examples','Observe','Choose a response','Understand','Practise','Try another response','Take away']);
   let steps=0;while(await p.locator('#step-next').count()){assert.equal(await p.locator('.step-controls .primary-forward').count(),1);await p.locator('#step-next').click();await position(p,lesson);steps++;assert.ok(steps<30);}
   assert.match(await p.locator('.course-position').innerText(),new RegExp(`${lesson-1} of 5 lessons read`));
   await p.screenshot({path:resolve(out,`${width}-${theme}-lesson${lesson}-finish.png`)});
   const finish=p.locator('#next-lesson');assert.match(await finish.innerText(),lesson<5?/^Finish & continue: /:/^Finish & start 10-question quiz$/);await finish.click();observations.push({width,theme,lesson,steps:steps+1});
  }
  assert.match(p.url(),/view=quiz/);assert.equal(await p.locator('#quiz-content fieldset').count(),10);
  for(const q of course.questions)await p.locator(`#quiz-content input[name="${q.question_id}"][value="${q.correct_option_id}"]`).check();
  await p.locator('#quiz-submit').click();assert.match(await p.locator('#quiz-result').innerText(),/10\s*\/\s*10/);await p.locator('#quiz-return').click();await position(p,5);assert.match(await p.locator('.course-position').innerText(),/5 of 5 lessons read/);
  await p.locator('#step-back').click();await position(p,5);assert.equal(await p.locator('.step-controls .primary-forward').count(),1);assert.equal(await p.evaluate(()=>localStorage.length),0);
  await p.close();
 }
 fs.writeFileSync(resolve(out,'journey.json'),JSON.stringify({complete:true,observations},null,2));
});
await test('free exploration does not mark read; opt-in reload resumes last lesson at first step',async()=>{
 const p=await browser.newPage({viewport:{width:390,height:900}});await p.goto(`http://127.0.0.1:${server.address().port}/learn/`);await p.waitForSelector('body[data-ready]');await p.locator('[data-module-launch="pfa"]').click();
 await p.locator('#lesson-menu > summary').click();await p.locator('[data-lesson="pfa-03"]').click();await p.locator('#skill-loop-phases').selectOption('6');assert.match(await p.locator('.course-position').innerText(),/0 of 5 lessons read/);
 await p.locator('.course-details > summary').click();await p.locator('#save-progress').check();await p.reload();await p.waitForSelector('body[data-ready]');await p.locator('[data-module-launch="pfa"]').click();await position(p,3);assert.match(await p.locator('.course-position').innerText(),/Step 1 of 7/);assert.match(await p.locator('.course-position').innerText(),/0 of 5 lessons read/);
 await p.locator('.course-details > summary').click();await p.locator('#save-progress').uncheck();assert.equal(await p.evaluate(()=>localStorage.length),0);await p.close();
});}finally{await browser.close();await new Promise(r=>server.close(r));}
