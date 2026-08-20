import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/';
const OUT = new URL('./captures/2026-08-20-07-44', import.meta.url).pathname;
const b = await chromium.launch({ channel:'chrome' });
const page = await b.newPage({ viewport:{ width:1440, height:1024 } });
await page.goto(BASE, { waitUntil:'domcontentloaded' }); await page.waitForTimeout(2500);
await page.click('[data-filtres-toggle]'); await page.waitForSelector('[data-filtres-drawer]'); await page.waitForTimeout(500);
await page.click('[data-analyser-btn]').catch(()=>{});
await page.waitForTimeout(4500);                       // rituel 3 s
await page.click('text=Voir les parcelles').catch(()=>{});  // révéler la liste + palette carte
await page.waitForTimeout(5000);
await page.screenshot({ path: `${OUT}/01b-vivier-analyse-on.png` });
// texte visible pour attester le nombre
const t = await page.evaluate(()=>document.querySelector('[data-compteur-vivant]')?.textContent || document.body.innerText.match(/285[  ]?781|431[  ]?663/)?.[0] || 'n/a');
console.log('compteur visible:', t);
await b.close();
