import { chromium } from './node_modules/playwright/index.mjs';
import { readFileSync } from 'fs';
const EXE='/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell';
const dir='/Users/openclaw/Desktop/labuse/docs/audit-2026-08/ONBOARDING/planche';
const b=await chromium.launch({executablePath:EXE});
for(const vw of [{w:1440,h:900,t:'desktop'},{w:390,h:844,t:'mobile'}]){
  const p=await (await b.newContext({viewport:{width:vw.w,height:vw.h}})).newPage();
  for(const n of ['14-cgv','15-mentions-legales','16-confidentialite']){
    await p.setContent(readFileSync(`${dir}/${n}.html`,'utf8'),{waitUntil:'load'});
    await p.screenshot({path:`${dir}/${n}-${vw.t}.png`,fullPage:true});
    if(n==='14-cgv'&&vw.t==='desktop'){const w=await p.evaluate(()=>{const l=document.querySelector('.legal');const toc=document.querySelector('.toc');return {legalPx:Math.round(l.getBoundingClientRect().width),toc:!!toc,anchors:document.querySelectorAll('.legal h2[id]').length};});console.log('CGV desktop:',JSON.stringify(w));}
  }
  await p.close();
}
await b.close();
