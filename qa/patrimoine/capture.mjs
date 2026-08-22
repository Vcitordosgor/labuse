// Recette SCAN PATRIMOINE refonte — le ménage, l'action, le signal qui dort.
// Parcours : recherche → portefeuille (actionnables + SDP résiduelle) → valorisation → signal INPI
// → assiette contiguë → courrier prérempli. Vestiges de matrice absents (q_score/a_score/statut).
// Usage : BASE=http://localhost:5173/socle/ node qa/patrimoine/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const SIREN = process.env.SIREN || 'U28719600';   // 3 parcelles, contiguës, INPI absent, valorisable
const OUT = new URL('./captures', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 1200 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(900);

await page.evaluate((k) => window.__labuse.setModule(k), 'patrimoine');
await page.waitForTimeout(400);
const input = page.locator('input[placeholder^="SIREN"]');
await input.fill(SIREN);
await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/1-recherche.png` });

// choisir la 1re suggestion → charge le portefeuille
await page.locator('button', { hasText: 'parc.' }).first().click();
await page.waitForSelector('[data-m02-courrier]', { state: 'visible' });
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/2-portefeuille.png`, fullPage: true });

const has = async (sel) => (await page.locator(sel).count()) > 0;
const txt = async (sel) => (await has(sel)) ? (await page.locator(sel).first().innerText()).replace(/\s+/g, ' ').trim() : null;
const panel = await page.locator('[data-outil-body], body').first().innerText();

const inv = {
  agregat_actionnables: /actionnables/.test(panel),
  sdp_residuelle_pas_totale: /SDP résiduelle/.test(panel) && !/SDP totale/.test(panel),
  valorisation: /Valorisation indicative du foncier nu/.test(panel),
  signal_inpi: await has('[data-m02-inpi]'),
  assiette_contigue: await txt('[data-m02-assiette]'),
  lien_courrier: await has('[data-m02-courrier]'),
  vestige_matrice_absent: !/matrice/i.test(panel),
};
writeFileSync(`${OUT}/inventaire.json`, JSON.stringify(inv, null, 2));
console.log(JSON.stringify(inv, null, 2));

// l'action : ✉ courrier de la 1re parcelle → l'outil Courrier s'ouvre prérempli
if (inv.lien_courrier) {
  await page.locator('[data-m02-courrier]').first().click();
  await page.waitForSelector('[data-courrier-idu]', { state: 'visible' });
  await page.waitForTimeout(500);
  const ok = await page.locator('[data-courrier-next]:not([disabled])').count();
  console.log('courrier prérempli (Suivant actif) :', ok > 0);
  await page.screenshot({ path: `${OUT}/3-courrier.png` });
}
await browser.close();
console.log('OUT:', OUT);
