// NAV-KEYBOARD-01: native Tab, never direct focus on a middle link.
import {chromium} from '/root/.hermes/outputs/mhpss-learning-architecture/prototype-build/learn-demo/node_modules/playwright/index.mjs';
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
const root=resolve(import.meta.dirname,'..'), out=process.env.NAV_EVIDENCE;
if(!out)throw Error('Set NAV_EVIDENCE to owned evidence directory');
await mkdir(out,{recursive:true});
const server=createServer(async(req,res)=>{try{let p=new URL(req.url,'http://local').pathname;if(p.endsWith('/'))p+='index.html';res.setHeader('Content-Type',({'.html':'text/html','.css':'text/css','.js':'text/javascript'})[extname(p)]||'application/octet-stream');res.end(await readFile(resolve(root,'.'+p)));}catch{res.writeHead(404);res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
let browser;const results=[];
try{
 browser=await chromium.launch({headless:true,executablePath:'/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',args:['--no-sandbox']});
 for(const font of ['fallback','actual']){
  const context=await browser.newContext({serviceWorkers:'block'});
  if(font==='fallback')await context.route('https://**/*',r=>r.abort());
  const page=await context.newPage();
  for(const scheme of ['light','dark'])for(const width of [320,390,820,1024,1440]){
   await page.emulateMedia({colorScheme:scheme});await page.setViewportSize({width,height:900});
   await page.goto(`http://127.0.0.1:${server.address().port}/?lang=en`);await page.evaluate(()=>document.fonts.ready);
   const loaded=await page.evaluate(()=>[...document.fonts].some(f=>f.family.includes('Mukta')&&f.status==='loaded'));
   for(const lang of ['en','ne']){
    if(lang==='ne')await page.locator('button[data-lang="ne"]').click();
    await page.locator('.nav-middle').evaluate(e=>e.scrollLeft=0);
    const measure=()=>page.evaluate(()=>{
     const e=document.activeElement.closest('.nav-middle a')||document.querySelector('.nav-middle a'),m=e.parentElement;
     const r=e.getBoundingClientRect(),p=m.getBoundingClientRect();
     const labels=[...e.querySelectorAll('b,i')].map(t=>{const range=document.createRange();range.selectNodeContents(t);return [...range.getClientRects()].map(x=>({x:x.x,right:x.right,y:x.y,bottom:x.bottom}));}).flat();
     return {label:e.querySelector('b').textContent,visible:r.x>=p.x-1&&r.right<=p.right+1&&labels.every(x=>x.x>=p.x-1&&x.right<=p.right+1&&x.y>=r.y-1&&x.bottom<=r.bottom+1),target:r.width>=44&&r.height>=44,rect:{x:r.x,right:r.right,w:r.width,h:r.height},viewport:{x:p.x,right:p.right,w:p.width},outline:getComputedStyle(e).outlineStyle,rootOverflow:document.documentElement.scrollWidth>innerWidth};
    });
    const initial=await measure();
    // Enter navbar using real Tab from the document, then traverse all six links.
    await page.locator('body').click({position:{x:1,y:1}});
    let found=false;for(let i=0;i<30;i++){await page.keyboard.press('Tab');if(await page.locator('.nav-home').evaluate(e=>e===document.activeElement)){found=true;break;}}
    const links=[];if(found)for(let i=0;i<6;i++){await page.keyboard.press('Tab');await page.waitForTimeout(250);links.push(await measure());}
    const state={font,loaded,scheme,width,lang,initial,links,passed:found&&initial.visible&&links.length===6&&links.every(x=>x.visible&&x.target&&!x.rootOverflow&&x.outline==='solid')&&(font!=='actual'||loaded)};
    results.push(state);if(!state.passed)await page.locator('.navband').screenshot({path:`${out}/${font}-${width}-${scheme}-${lang}.png`});
   }
  }await context.close();
 }
 const summary={passed:results.every(x=>x.passed),states:results.length,failed:results.filter(x=>!x.passed).map(x=>({font:x.font,width:x.width,scheme:x.scheme,lang:x.lang,loaded:x.loaded,initial:x.initial,links:x.links.filter(l=>!l.visible)})),results};
 await writeFile(resolve(out,'keyboard-results.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify({passed:summary.passed,states:summary.states,failed:summary.failed}));if(!summary.passed)process.exitCode=1;
}finally{await browser?.close();await new Promise(r=>server.close(r));}
