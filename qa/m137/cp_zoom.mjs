import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const Q = 'combien de parcelles en procédure collective à Saint-Paul';
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0,140)) } };
await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForTimeout(3500);
await soft(async () => { await page.locator('button[title="IA"]').click(); await page.waitForTimeout(1200); }, 'copilote');
await soft(async () => { const t=page.locator('[data-brief]').first(); await t.click(); await t.fill(Q); await page.waitForTimeout(300); const e=page.locator('[data-accueil-envoyer]'); if(await e.count()) await e.click(); else await t.press('Enter'); }, 'question');
await page.waitForSelector('[data-reponse-carte]', { timeout: 45000 }).catch(()=>{});
await soft(async () => { await page.locator('[data-reponse-carte]').click(); await page.waitForTimeout(7000); }, 'clic');
// scroll le listing jusqu'au pied (montrer « 66 affichées / 66 au total »)
await soft(async () => { await page.evaluate(() => { const s=document.querySelector('[data-results-scroll]'); if(s) s.scrollTop=s.scrollHeight; }); await page.waitForTimeout(1200); }, 'scroll pied');
// crop le panneau gauche
const panel = page.locator('[data-results-panel]');
const bx = await panel.boundingBox().catch(()=>null);
await page.screenshot({ path: `${OUT}/copilote_listing_zoom.png`, clip: { x: 0, y: 0, width: 430, height: 1024 } });
const foot = await page.evaluate(() => { const p=document.querySelector('[data-results-panel]'); const m=(p?.innerText||'').replace(/\s+/g,' ').match(/\d+ affichée[s]? \/ \d+ au total|\d+ affichée[s]? \/ \d+/); return m?m[0]:'(?)'; });
console.log('pied visible:', foot);
await b.close();
