// Capture de recette — le champ « adresse » aligné sur le gabarit produit.
// Compare côte à côte le champ « Aller à une rue… » (Radar permis) et « Adresse… »
// (Scorer une adresse) : même fond, bordure, arrondi, typo (gabarit AddressAutocomplete par défaut).
// Usage : BASE=http://localhost:5173/socle/ node qa/champ-adresse/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, readFileSync } from 'node:fs';

const dataUri = (p) => `data:image/png;base64,${readFileSync(p).toString('base64')}`;

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1280, height: 1040 }, deviceScaleFactor: 2 });
page.setDefaultTimeout(30000);

async function openOutil(key) {
  await page.click('button[title="Outils"]');
  await page.waitForSelector(`[data-outil="${key}"]`, { state: 'visible' });
  await page.click(`[data-outil="${key}"]`);
}

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(500);

// 1 · Radar permis — champ « Aller à une rue… »
await openOutil('permis');
const radar = page.locator('input[placeholder="Aller à une rue, une commune…"]');
await radar.waitFor({ state: 'visible' });
await radar.scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await radar.screenshot({ path: `${OUT}/radar-permis-champ.png` });
console.log('📸 radar-permis-champ');

// 2 · Scorer une adresse — champ « Adresse… »
await openOutil('scoreur-adresse');
const scoreur = page.locator('[data-scoreur-adresse]');
await scoreur.waitFor({ state: 'visible' });
await scoreur.scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await scoreur.screenshot({ path: `${OUT}/scoreur-adresse-champ.png` });
console.log('📸 scoreur-adresse-champ');

// 3 · composition côte à côte (un seul PNG comparatif)
const compo = await browser.newPage({ viewport: { width: 900, height: 260 }, deviceScaleFactor: 2 });
await compo.setContent(`<!doctype html><html><body style="margin:0;background:#0f1115;font-family:ui-sans-serif,system-ui;color:#c9d1d9">
  <div style="display:flex;gap:28px;padding:28px;align-items:flex-start">
    <figure style="margin:0;flex:1">
      <figcaption style="font-size:12px;margin-bottom:8px;color:#8b949e">Radar permis — « Aller à une rue… »</figcaption>
      <img src="${dataUri(`${OUT}/radar-permis-champ.png`)}" style="width:100%;display:block"/>
    </figure>
    <figure style="margin:0;flex:1">
      <figcaption style="font-size:12px;margin-bottom:8px;color:#8b949e">Scorer une adresse — « Adresse… »</figcaption>
      <img src="${dataUri(`${OUT}/scoreur-adresse-champ.png`)}" style="width:100%;display:block"/>
    </figure>
  </div></body></html>`, { waitUntil: 'load' });
await compo.waitForTimeout(300);
await compo.screenshot({ path: `${OUT}/cote-a-cote.png` });
console.log('📸 cote-a-cote');

await browser.close();
console.log('OUT:', OUT);
