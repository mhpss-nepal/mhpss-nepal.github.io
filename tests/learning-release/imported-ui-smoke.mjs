// Optional browser smoke against an ACTUAL private release tree, not injected content.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve, extname} from 'node:path';
import assert from 'node:assert/strict';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE);
const root=resolve(process.env.LEARNING_DEPLOYMENT);
const server=createServer(async(req,res)=>{
 try {
  let pathname=new URL(req.url,'http://local').pathname;
  if(pathname.endsWith('/'))pathname+='index.html';
  const file=resolve(root,'.'+pathname);assert.ok(file.startsWith(root+'/'));
  res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.json':'application/json','.css':'text/css','.ttf':'font/ttf'})[extname(file)]||'text/plain');
  res.end(await readFile(file));
 }catch{res.writeHead(404);res.end();}
});
let browser;
try {
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE,args:['--no-sandbox']});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(`http://127.0.0.1:${server.address().port}/learn/index.html`);
 await page.locator('[data-start=synthetic-navigation]').click({timeout:15000});
 await page.locator('input[value=a]').check();await page.locator('[data-check]').click();
 const text=await page.locator('#course-content').innerText();
 assert.match(text,/Navigation exercise/);assert.match(await page.locator('body').innerText(),/Next is the synthetic forward label/);assert.deepEqual(errors,[]);
 console.log(JSON.stringify({status:'PASS',mode:'actual imported synthetic content on loopback',lesson_and_quiz_rendered:true,rationale_rendered:true,browser_errors:errors}));
}finally{await browser?.close();await new Promise(r=>server.close(r));}
