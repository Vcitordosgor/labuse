// Recette ASSEMBLAGE refonte — le constat réel remplace le score frustre.
// Parcours : sélection (2 parcelles contiguës via window.__labuse) → bilan RÉEL (capacité + charge
// foncière cumulées) → valorisation (prix terrain nu de zone) → lien Courrier par parcelle.
// Le score « 57 » a DISPARU de l'écran (doctrine M120) ; à la place, les faits.
// Usage : BASE=http://localhost:5173/socle/ node qa/assemblage/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const PAIR = (process.env.PAIR || '97415000AY0248,97415000AY0247').split(',');
const OUT = new URL('./captures', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 1200 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(900);

// ouvrir l'outil Assemblage + composer l'assiette (msel via le store QA)
await page.evaluate((k) => window.__labuse.setModule(k), 'assemblage');
await page.waitForTimeout(400);
await page.evaluate((ids) => window.__labuse.setMsel(ids), PAIR);
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}/1-assiette.png` });

// analyser
await page.click('text=Analyser l\'assiette');
await page.waitForSelector('[data-asm-gain], [data-asm-sans-potentiel]', { state: 'visible' });
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/2-bilan.png`, fullPage: true });

const has = async (sel) => (await page.locator(sel).count()) > 0;
const txt = async (sel) => (await has(sel)) ? (await page.locator(sel).first().innerText()).replace(/\s+/g, ' ').trim() : null;

const inv = {
  score_absent_de_l_ecran: !(await has('text=score d\'assemblage')),   // #3 : le 57 a disparu
  faits: await txt('[data-asm-faits]'),                                // d'un seul tenant · N interlocuteurs · ×gain
  bilan_reel: await txt('[data-asm-bilan]'),                           // #1 : CA + charge foncière cumulées
  valorisation: await txt('[data-asm-valorisation]'),                  // #2 : prix terrain nu de zone
  note_sens: await txt('[data-asm-gain] + * , [data-asm-gain] ~ div'), // (best-effort)
  lien_courrier_present: await has('[data-asm-courrier]'),             // #4 : action au bout du constat
};
writeFileSync(`${OUT}/inventaire.json`, JSON.stringify(inv, null, 2));
console.log(JSON.stringify(inv, null, 2));

// #4 — cliquer le lien Courrier de la 1re parcelle → l'outil Courrier s'ouvre prérempli
if (inv.lien_courrier_present) {
  await page.locator('[data-asm-courrier]').first().click();
  await page.waitForSelector('[data-courrier-idu]', { state: 'visible' });
  await page.waitForTimeout(500);
  const prefilled = await page.locator('[data-courrier-next]:not([disabled])').count();
  console.log('courrier prérempli (Suivant actif) :', prefilled > 0);
  await page.screenshot({ path: `${OUT}/3-courrier-prerempli.png` });
}

await browser.close();
console.log('OUT:', OUT);
