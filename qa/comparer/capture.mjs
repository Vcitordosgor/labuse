// Capture de recette — comparateur sur la source SERVIE (_q_v2_fiche) : puces d'ACTION,
// rang, fraction (« 1/N sous 1 an »), raison dominante. 3 parcelles côte à côte.
// On ajoute par la CARTE (mode picking) : flyTo chaque parcelle + clic (motif M82).
// Usage : BASE=http://localhost:5173/socle/ node qa/comparer/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const PARCELS = [
  { idu: '97408000AP1647', lng: 55.329322, lat: -20.959428 },
  { idu: '97408000AP1609', lng: 55.327934, lat: -20.961529 },
  { idu: '97408000AP1610', lng: 55.328119, lat: -20.961522 },
];

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 });
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(700);

// ouvrir Outils → Comparer (mode picking, sélection vide)
await page.click('button[title="Outils"]');
await page.click('[data-outil="comparer"]');
await page.waitForSelector('[data-compare-picking]', { state: 'visible' });

async function clickParcel(pt) {
  await page.evaluate(({ lng, lat }) => window.__labuse_map.jumpTo({ center: [lng, lat], zoom: 17.5 }), pt);
  await page.waitForTimeout(1100);   // laisse charger les tuiles parcellaires
  const px = await page.evaluate(({ lng, lat }) => {
    const m = window.__labuse_map, p = m.project([lng, lat]), r = m.getCanvas().getBoundingClientRect();
    return { x: r.left + p.x, y: r.top + p.y };
  }, pt);
  await page.mouse.click(px.x, px.y);
  await page.waitForTimeout(500);
}
for (const pt of PARCELS) await clickParcel(pt);

// « Voir la comparaison » → tableau
await page.click('[data-compare-picking] button:has-text("Voir la comparaison")');
await page.waitForSelector('[data-compare-panel]', { state: 'visible' });
await page.waitForSelector('[data-compare-col]');
await page.waitForTimeout(1300);   // getCompare (verdict/fraction/raison)

const n = await page.locator('[data-compare-col]').count();
const raisons = await page.locator('[data-compare-raison]').count();
console.log(`colonnes=${n} · pastilles raison=${raisons}`);
await page.locator('[data-compare-panel] > div').screenshot({ path: `${OUT}/comparer-3-parcelles.png` });
console.log('📸 comparer-3-parcelles');
await browser.close();
console.log('OUT:', OUT);
