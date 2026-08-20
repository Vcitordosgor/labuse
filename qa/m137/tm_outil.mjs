import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const IDU = process.argv[2] || '97414000EN0451';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0,120)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
// ouvrir le menu Outils via le rail
await soft(async () => { await page.locator('button[title="Outils"]').click(); await page.waitForTimeout(800); }, 'rail outils');
// lancer « Remonter le temps »
await soft(async () => { await page.locator('[data-outil="temps"]').click(); await page.waitForTimeout(1200); }, 'lancer temps');
// désigner la parcelle (ÉTAPE 1)
await soft(async () => { const i = page.locator('[data-temps-idu]'); await i.fill(IDU); await i.press('Enter'); await page.waitForTimeout(3000); }, 'designer parcelle');
await page.waitForFunction(() => !!window.__labuse_tm, { timeout: 15000 }).catch(()=>console.log('WARN pas de __labuse_tm'));
await page.waitForTimeout(8000);
const rects = await page.evaluate(() => { const tm=window.__labuse_tm; if(!tm) return null; const r=m=>{const b=m.getContainer().getBoundingClientRect(); return {y:Math.round(b.y),h:Math.round(b.height)};}; return {past:r(tm.past), now:r(tm.now)}; });
console.log('rects:', JSON.stringify(rects));
await page.screenshot({ path: `${OUT}/tm_outil.png` });
await soft(async () => { const bx = await page.locator('.select-none').first().boundingBox(); if (bx) await page.screenshot({ path: `${OUT}/tm_outil_zoom.png`, clip: { x: bx.x, y: bx.y, width: bx.width, height: bx.height } }); }, 'crop');
await b.close();
console.log('outil done');
