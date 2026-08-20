import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/';
const OUT = new URL('./captures/2026-08-20-07-44', import.meta.url).pathname;
const b = await chromium.launch({ channel:'chrome' });
const page = await b.newPage({ viewport:{ width:1440, height:1024 } });
await page.goto(BASE, { waitUntil:'domcontentloaded' }); await page.waitForTimeout(2500);
await page.click('[data-filtres-toggle]'); await page.waitForSelector('[data-filtres-drawer]'); await page.waitForTimeout(500);
// lancer l'analyse LABUSE (bouton « Demander à LABUSE ») → rituel 3 s → vivier révélé
await page.click('[data-analyser-btn]').catch(async ()=>{ await page.click('text=Demander à LABUSE'); });
await page.waitForTimeout(5000);
await page.screenshot({ path: `${OUT}/01b-vivier-analyse-on.png` });
console.log('shot 01b (vivier analyse ON)');
await b.close();
