// Recette BAROMÈTRE → onglet « Évolution » de Communes. Trois séries (ancien, terrain, permis) +
// tendance annuelle % + neuf en référence + Rapport PDF. Plus un trimestre PARTIEL simulé (grisé).
// Usage : BASE=http://localhost:5173/socle/ node qa/barometre/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const OUT = new URL('./captures', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 1200 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(900);

// ouvrir Communes → onglet « Évolution du marché »
await page.evaluate(() => window.__labuse.setModule('communes'));
await page.waitForSelector('[data-communes-vue="evolution"]', { state: 'visible' });
await page.click('[data-communes-vue="evolution"]');
await page.waitForSelector('text=Ancien bâti', { state: 'visible' });
await page.waitForTimeout(700);
await page.screenshot({ path: `${OUT}/1-evolution.png`, fullPage: true });

const body = await page.locator('body').innerText();
const inv = {
  serie_ancien: /ancien bâti/i.test(body),
  serie_terrain: /terrain nu/i.test(body),
  serie_permis: /permis autorisés/i.test(body),
  tendance_pct: /% \/ an/i.test(body),
  neuf_reference: /neuf\s*:/i.test(body),
  bouton_pdf: (await page.locator('a[href="/moteurs/barometre.pdf"]').count()) > 0,
};

// §1a — simuler un trimestre PARTIEL : intercepter l'API, marquer le dernier trimestre partiel,
// puis RECHARGER la page (fetch frais garanti, sans dépendre du cache react-query).
await page.route('**/moteurs/barometre', async (route) => {
  const resp = await route.fetch();
  const d = await resp.json();
  if (d.dvf_trimestres?.[0]) { d.dvf_trimestres[0].partiel = true; d.dvf_trimestres[0].mutations = 120; }
  if (d.terrain_trimestres?.[0]) { d.terrain_trimestres[0].partiel = true; d.terrain_trimestres[0].mutations = 60; }
  await route.fulfill({ response: resp, body: JSON.stringify(d) });
});
await page.reload({ waitUntil: 'domcontentloaded' });
await page.waitForTimeout(700);
await page.evaluate(() => window.__labuse.setModule('communes'));
await page.waitForSelector('[data-communes-vue="evolution"]', { state: 'visible' });
await page.click('[data-communes-vue="evolution"]');
await page.waitForSelector('text=délai de publication', { state: 'visible' });
await page.waitForTimeout(500);
await page.screenshot({ path: `${OUT}/2-trimestre-partiel-grise.png`, fullPage: true });
inv.trimestre_partiel_grise = (await page.locator('text=délai de publication').count()) > 0;

writeFileSync(`${OUT}/inventaire.json`, JSON.stringify(inv, null, 2));
console.log(JSON.stringify(inv, null, 2));
await browser.close();
console.log('OUT:', OUT);
