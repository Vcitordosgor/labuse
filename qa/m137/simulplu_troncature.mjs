import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/socle/'; const OUT=new URL('./captures',import.meta.url).pathname;
const b=await chromium.launch({channel:'chrome'}); const page=await b.newPage({viewport:{width:1440,height:1024}});
const soft=async(fn,w)=>{try{await fn()}catch(e){console.log('WARN',w,String(e).slice(0,140))}};
await page.goto(BASE,{waitUntil:'domcontentloaded'}); await page.waitForTimeout(3500);
// choisir la commune Saint-Paul (l'outil M15 lit useApp.commune)
await soft(async()=>{ const box=page.locator('[data-omnibox]'); await box.click(); await box.fill('Saint-Paul'); await page.waitForTimeout(1200); await box.press('Enter'); await page.waitForTimeout(2500); },'commune');
// ouvrir Outils → Changement PLU (simulplu)
await soft(async()=>{ await page.locator('button[title="Outils"]').click(); await page.waitForTimeout(800); },'outils');
await soft(async()=>{ await page.locator('[data-outil="simulplu"]').click(); await page.waitForTimeout(2500); },'simulplu');
// cliquer la 1re zone AU (chip « AUc → U »)
await soft(async()=>{ await page.getByText('AUc → U',{exact:false}).first().click(); },'zone AUc');
// attendre le résultat (l'endpoint ~11s) : la phrase de troncature apparaît
await page.waitForFunction(()=>/premières sur/.test(document.body.innerText),{timeout:30000}).catch(()=>console.log('WARN phrase absente'));
const phrase=await page.evaluate(()=>{const m=document.body.innerText.match(/les [0-9 .]+ premières sur [0-9 .]+ parcelles en \S+/);return m?m[0]:'(?)';});
console.log('phrase de troncature:', phrase);
await page.screenshot({path:`${OUT}/simulplu_troncature.png`, clip:{x:0,y:0,width:430,height:900}});
await b.close();
console.log(/premières sur/.test(phrase)?'OK — phrase de troncature affichée':'À VÉRIFIER');
