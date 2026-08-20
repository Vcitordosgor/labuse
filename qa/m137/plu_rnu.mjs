import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/socle/'; const OUT=new URL('./captures',import.meta.url).pathname;
const b=await chromium.launch({channel:'chrome'}); const page=await b.newPage({viewport:{width:1440,height:1024}});
const soft=async(fn,w)=>{try{return await fn()}catch(e){console.log('WARN',w,String(e).slice(0,120))}};
await page.goto(BASE,{waitUntil:'domcontentloaded'}); await page.waitForTimeout(3500);
await soft(async()=>{ await page.locator('button[title="Outils"]').click(); await page.waitForTimeout(700); },'outils');
await soft(async()=>{ await page.locator('[data-outil="plu"]').click(); await page.waitForTimeout(1200); },'plu');
await soft(async()=>{ await page.locator('[data-plu-voie="annuaire"]').click(); await page.waitForTimeout(1200); },'annuaire');
// Saint-Philippe (RNU, 97417) → dit son statut, aucun bouton de téléchargement
await soft(async()=>{ await page.locator('[data-plu-commune="97417"]').click(); await page.waitForTimeout(800); },'RNU');
const indispo = await page.locator('[data-plu-indispo]').count();
const integral = await page.locator('[data-plu-integral]').count();
const msg = await soft(async()=>page.locator('[data-plu-indispo]').innerText(),'msg');
console.log('RNU dit son statut:', indispo, '| bouton intégral (doit être 0):', integral);
console.log('message affiché:', (msg||'').replace(/\s+/g,' ').slice(0,90));
await page.screenshot({path:`${OUT}/plu_annuaire_rnu.png`, clip:{x:0,y:0,width:430,height:600}});
await b.close(); console.log('OK');
