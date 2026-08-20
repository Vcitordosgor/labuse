import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE='http://localhost:5173/'; const IDU='97411000IO0091';
const OUT = new URL('./captures/2026-08-20-07-44', import.meta.url).pathname;
const b = await chromium.launch({ channel:'chrome' });
const page = await b.newPage({ viewport:{ width:1440, height:1024 } });
await page.goto(BASE, { waitUntil:'domcontentloaded' }); await page.waitForTimeout(2500);
const sb = page.locator('input[placeholder*="Rechercher"]').first();
await sb.click(); await sb.fill(IDU); await page.waitForTimeout(1200);
await page.keyboard.press('Enter'); await page.waitForTimeout(1500);
await page.locator(`text=${IDU}`).first().click().catch(()=>{});
await page.waitForTimeout(8000);
// scroll dans le panneau fiche (droite) vers le bloc score/verdict
await page.mouse.move(1200, 500);
for (let i=0;i<6;i++){ await page.mouse.wheel(0, 400); await page.waitForTimeout(200); }
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/03b-fiche-score.png` });
console.log('shot 03b');
await b.close();
