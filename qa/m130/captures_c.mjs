// M130 · Phase 1 (reprise kanban) — projet 24 déplié → rejeu → bannière refonte.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const OUT = new URL('./captures/2026-08-20-07-44', import.meta.url).pathname;
const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1024 } });
page.setDefaultTimeout(30000);
async function shot(n, note) { await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`); }
const soft = async (fn, what) => { try { await fn(); } catch (e) { console.log(`⚠ ${what}: ${String(e).slice(0, 160)}`); } };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);
await page.click('[title="Projets"]');
await page.waitForSelector('[data-projets-liste]');
await page.waitForTimeout(600);
await soft(async () => { await page.click('text=/VOIR LES \\d+ AUTRES/'); await page.waitForTimeout(600); }, 'déplier liste');
await soft(async () => {
  const card = page.locator('text=Démo — 40 logements').first();
  await card.scrollIntoViewIfNeeded();
  await card.click();
  await page.waitForSelector('[data-projet-kanban]');
  await page.waitForTimeout(1000);
}, 'ouvrir kanban 24');
await shot('06-kanban', 'kanban projet 24 (cadrage du JJ/MM)');
await soft(async () => {
  await page.click('text=/Rejouer/');
  await page.waitForTimeout(3500);
}, 'clic Rejouer');
await shot('07-kanban-rejeu-refonte', 'rejeu : « entrée(s) par refonte cascade — nouveau vivier »');
await browser.close();
console.log('OK');
