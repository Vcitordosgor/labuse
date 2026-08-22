// Capture de recette — l'outil FUSIONNÉ « Étudier un bien » (scoreur + calculette).
// Parcours complet : entrée (IDU) → CONSTAT (verdict + charge calibrée + confrontation zone) →
// prix demandé (marge calibrée) → HYPOTHÈSES (calculette réglable, « selon vos hypothèses »).
// Usage : BASE=http://localhost:5173/socle/ node qa/etudier-bien/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const IDU = process.env.IDU || '97415000DK1044';
const OUT = new URL('./captures', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 1400 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(700);

// ouvrir l'outil « Étudier un bien » (créneau phare O2)
await page.click('button[title="Outils"]');
await page.click('[data-outil="scoreur-adresse"]');
await page.waitForSelector('[data-etudier-form]', { state: 'visible' });
await page.screenshot({ path: `${OUT}/1-entree.png` });

// ENTRÉE UNIFIÉE (patron omnibox) : IDU dans le MÊME champ que l'adresse → Entrée → CONSTAT
await page.fill('[data-etudier-adresse]', IDU);
await page.press('[data-etudier-adresse]', 'Enter');
await page.waitForSelector('[data-etudier-resultat]', { state: 'visible' });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/2-constat.png` });

const present = async (sel) => (await page.locator(sel).count()) > 0;
const txt = async (sel) => (await present(sel)) ? (await page.locator(sel).first().innerText()).replace(/\s+/g, ' ').trim() : null;

// PRIX DEMANDÉ → marge calibrée
await page.fill('[data-etudier-prix]', '200000');
await page.waitForSelector('[data-etudier-marge-calibree]', { state: 'visible' });
await page.waitForTimeout(300);
await page.screenshot({ path: `${OUT}/3-prix-demande.png` });

// HYPOTHÈSES → la calculette réglable (selon vos hypothèses)
await page.click('[data-etudier-hyp-toggle]');
await page.waitForSelector('[data-calculette]', { state: 'visible' });
await page.waitForSelector('[data-calc-resultat], [data-calc-indispo]', { state: 'visible' });
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/4-hypotheses.png`, fullPage: true });

const inv = {
  idu: IDU,
  // le CONSTAT (calibré)
  tier: await txt('[data-etudier-resultat] span'),
  charge_calibree: await txt('[data-etudier-charge-calibree]'),
  terrain_zone_confrontation: await txt('[data-etudier-terrain-zone]'),
  marge_calibree: await txt('[data-etudier-marge-calibree]'),
  // les HYPOTHÈSES (calculette) — présence des 4 corrections Phase 1, sourcé masqué (dit une fois)
  cout_plancher: await txt('[data-calc-plancher]'),
  vrd: await txt('[data-calc-vrd]'),
  ca_reglee: await txt('[data-calc-ca]'),
  terrain_zone_reglee: await txt('[data-calc-terrain-zone]'),
  source_masquee_dans_hypotheses: !(await present('[data-calculette] p:has-text("LA BUSE (sourcé)")')),
  prix_input_unique: (await page.locator('[data-etudier-prix]').count()) + (await page.locator('input[placeholder="si connu"]').count()),
};
writeFileSync(`${OUT}/inventaire.json`, JSON.stringify(inv, null, 2));
console.log(JSON.stringify(inv, null, 2));
await browser.close();
console.log('OUT:', OUT);
