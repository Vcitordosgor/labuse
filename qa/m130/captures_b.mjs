// M130 · Phase 1 (reprise) — fiche + kanban, pilotés par window.__labuse (fiable).
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const IDU = process.env.IDU || '97411000IO0091';
const OUT = new URL('./captures/2026-08-20-07-44', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1024 } });
page.setDefaultTimeout(30000);
async function shot(n, note) { await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`); }
const soft = async (fn, what) => { try { await fn(); } catch (e) { console.log(`⚠ ${what}: ${String(e).slice(0, 160)}`); } };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);

// 03 · fiche parcelle du vivier bâti, via window.__labuse.select(idu)
await soft(async () => {
  await page.evaluate((idu) => window.__labuse.select(idu), IDU);
  await page.waitForTimeout(2500);
}, 'select(idu) fiche');
await shot('03-fiche-parcelle', `fiche ${IDU} (gloses · motifs FR · « Probabilité de vente sous 1 an »)`);

// faire défiler la fiche vers le bloc score pour voir le nom du score + tier
await soft(async () => {
  await page.evaluate(() => {
    const el = document.querySelector('[data-fiche-market-signal]') || document.querySelector('.ref');
    el?.scrollIntoView({ block: 'center' });
  });
  await page.waitForTimeout(600);
}, 'scroll fiche score');
await shot('03b-fiche-score', 'fiche — bloc score « Probabilité de vente sous 1 an »');

// 06 · kanban projet 24 + rejeu → « entrée par refonte cascade »
await soft(async () => {
  await page.evaluate(() => window.__labuse.select(null));
  await page.click('[title="Projets"]');
  await page.waitForSelector('[data-projets-liste]');
  await page.waitForTimeout(600);
}, 'aller à Projets');

await soft(async () => {
  const card = page.locator('text=Démo — 40 logements').first();
  await card.scrollIntoViewIfNeeded();
  await card.click();
  await page.waitForSelector('[data-projet-kanban]');
  await page.waitForTimeout(1000);
}, 'ouvrir kanban projet 24');
await shot('06-kanban', 'kanban projet 24 (cadrage du JJ/MM)');

await soft(async () => {
  await page.click('text=Rejouer');
  await page.waitForTimeout(3000);
}, 'clic Rejouer');
await shot('07-kanban-rejeu-refonte', 'rejeu : « entrée(s) par refonte cascade — nouveau vivier »');

console.log(`→ ${OUT}`);
await browser.close();
