// Recette « Densifier l'existant » (ex-Renouvellement, clé interne inchangée) — restitution au présent.
// §1 puce d'action (Classement, tier v2 servi) · §2 « les N premières sur M » · §3 tri dit ·
// §5 renommage (menu + en-tête = « Densifier l'existant », plus « Renouvellement »).
// Usage : BASE=http://localhost:5173/socle/ node qa/renouvellement/capture.mjs
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

// §5 — le MENU montre « Densifier l'existant », plus « Renouvellement »
await page.click('button[title="Outils"]');
await page.waitForTimeout(400);
const menuBody = await page.locator('body').innerText();
await page.screenshot({ path: `${OUT}/1-menu.png` });

// ouvrir l'outil (clé interne 'renouvellement' inchangée)
await page.evaluate(() => window.__labuse.setModule('renouvellement'));
await page.waitForSelector('[data-renouv-row]', { state: 'visible' });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/2-liste.png`, fullPage: true });

const body = await page.locator('body').innerText();
const chips = await page.locator('[data-renouv-row]').first().locator('span').allInnerTexts();
const inv = {
  menu_densifier: /densifier l.existant/i.test(menuBody),
  menu_sans_renouvellement: !/>?renouvellement/i.test(menuBody) || !/Renouvellement/.test(menuBody),
  entete_densifier: /densifier l.existant/i.test(body),
  puce_action: chips.some((t) => /priorité|à suivre|long terme|neutre|écartée|faible/i.test(t)),
  compte_n_sur_m: /premières sur|sur \d/i.test(body),
  tri_dit: /triées par/i.test(body),
  colonne_classement: /classement/i.test(body),
};
writeFileSync(`${OUT}/inventaire.json`, JSON.stringify({ ...inv, puce_chips: chips }, null, 2));
console.log(JSON.stringify(inv, null, 2), '\n1re ligne chips:', JSON.stringify(chips));
await browser.close();
console.log('OUT:', OUT);
