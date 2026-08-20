import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/';
const OUT = new URL('./captures/2026-08-20-07-44', import.meta.url).pathname;
const b = await chromium.launch({ channel:'chrome' });
const page = await b.newPage({ viewport:{ width:1440, height:1024 }, deviceScaleFactor:2 });
await page.goto(BASE, { waitUntil:'domcontentloaded' }); await page.waitForTimeout(2500);
await page.click('[data-filtres-toggle]'); await page.waitForSelector('[data-filtres-drawer]'); await page.waitForTimeout(600);
await page.locator('text=On peut encore construire').first().scrollIntoViewIfNeeded(); await page.waitForTimeout(400);
// clip sur le panneau gauche (filtres)
await page.screenshot({ path: `${OUT}/02b-facettes-le-bien.png`, clip:{ x:0, y:60, width:360, height:900 } });
console.log('shot 02b (clip)');
await b.close();
