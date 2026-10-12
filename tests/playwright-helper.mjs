import {createRequire} from 'node:module';
import {existsSync} from 'node:fs';
const require=createRequire(import.meta.url);
let playwright;
if(process.env.PLAYWRIGHT_MODULE) playwright=require(process.env.PLAYWRIGHT_MODULE);
else {try {playwright=require('playwright');} catch(error) {
 const fallback='/root/.hermes/outputs/mhpss-learning-architecture/prototype-build/learn-demo/node_modules/playwright';
 if(!existsSync(fallback)) throw error;
 playwright=require(fallback);
}}
export async function clickCourseControl(page,selector){
 const control=page.locator(selector);
 if(!await control.isVisible())await page.locator(selector.includes('data-lesson')?'#lesson-menu > summary':'.course-details > summary').click();
 await control.click();
}
const native=playwright.chromium;
export const chromium={...native, launch(options={}){
 const configured=process.env.CHROMIUM_EXECUTABLE||process.env.CHROMIUM_PATH;
 const detected=native.executablePath();
 const legacy='/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome';
 const executablePath=configured||(existsSync(detected)?detected:existsSync(legacy)?legacy:undefined);
 return native.launch({...options,executablePath});
}};
