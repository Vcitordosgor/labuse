// Capture de recette — la calculette foncière (outil) sur une parcelle CALCULABLE.
// Prouve les 4 corrections : (1) le coût-plancher est DIT, (2) plus de doublon du central,
// (3) CA + fourchette + prix terrain nu de la zone surfacés à côté du résultat, (4) champ VRD.
// Usage : LABEL=apres BASE=http://localhost:5173/socle/ node qa/calculette/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const LABEL = process.env.LABEL || 'apres';
const IDU = process.env.IDU || '97415000DK1044';   // Saint-Paul, calculable (SDP 159 · terrain 426 · 4730 €/m²)
const OUT = new URL(`./captures/${LABEL}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 1200 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(700);
await page.click('button[title="Outils"]');
await page.click('[data-outil="calculette-fonciere"]');
await page.waitForSelector('[data-picker-idu]', { state: 'visible' });
await page.fill('[data-picker-idu]', IDU);
await page.click('[data-picker-go]');
// le résultat chiffré (ou l'indispo honnête)
await page.waitForSelector('[data-calc-resultat], [data-calc-indispo]', { state: 'visible' });
await page.waitForTimeout(900);   // laisse le recalcul se poser (débounce 350 ms)

// inventaire des éléments-clés présents (les 4 corrections)
const present = async (sel) => (await page.locator(sel).count()) > 0;
const inv = {
  resultat: await present('[data-calc-resultat]'),
  cout_plancher_dit: await present('[data-calc-plancher]'),      // #1
  doublon_fourchette: await present('[data-calc-fourchette]'),   // #2 : ABSENT si prix = point unique (plus de central en double)
  ca_surface: await present('[data-calc-ca]'),                   // #3
  terrain_zone_confrontation: await present('[data-calc-terrain-zone]'), // #3
  vrd_note: await present('[data-calc-vrd]'),                    // #4
};
const txtOf = async (sel) => (await present(sel)) ? (await page.locator(sel).first().innerText()).replace(/\s+/g, ' ').trim() : null;
const textes = {
  plancher: await txtOf('[data-calc-plancher]'),
  cf: await txtOf('[data-calc-cf]'),
  ca: await txtOf('[data-calc-ca]'),
  terrain_zone: await txtOf('[data-calc-terrain-zone]'),
  vrd: await txtOf('[data-calc-vrd]'),
};
writeFileSync(`${OUT}/inventaire.json`, JSON.stringify({ idu: IDU, present: inv, textes }, null, 2));
console.log(`[${LABEL}]`, JSON.stringify(inv), '\n  plancher:', textes.plancher, '\n  terrain_zone:', textes.terrain_zone, '\n  vrd:', textes.vrd);

await page.locator('[data-calculette]').screenshot({ path: `${OUT}/calculette.png` });
await browser.close();
console.log('OUT:', OUT);
