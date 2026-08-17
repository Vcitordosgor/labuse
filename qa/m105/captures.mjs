// M105 P5 — captures : encart Sources hiérarchisé + états de fraîcheur, vue claire contours
// noirs, sélecteur de fond (Sombre en premier). BASE=http://localhost:5173/ node qa/m105/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(25000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });

// 1-2 · page Sources : encart + lignes d'état
await page.click('button:has-text("Sources")');
await page.waitForSelector('[data-sources-bandeau]');
await page.screenshot({ path: `${OUT}/01-encart-sources.png` });
console.log('📸 01 — encart hiérarchisé + date du radar');
const retard = await page.$('[data-source-retard-producteur]');
const amont = await page.$('[data-source-amont-detail]');
if (retard) { await retard.scrollIntoViewIfNeeded(); await page.screenshot({ path: `${OUT}/02-etat-publication-ancienne.png` }); console.log('📸 02 — état 1 (producteur) :', (await retard.textContent())?.trim().slice(0, 100)) }
else console.log('⚠ 02 — aucun état « publication ancienne » à l’écran');
if (amont) { await amont.scrollIntoViewIfNeeded(); await page.screenshot({ path: `${OUT}/03-etat-amont-en-avance.png` }); console.log('📸 03 — état 2 (nous) :', (await amont.textContent())?.trim().slice(0, 100)) }
else console.log('⚠ 03 — aucun état « amont en avance » à l’écran');

// 3-4 · carte : sélecteur (Sombre premier) + vue claire contours noirs
await page.click('button:has-text("Cartes")');
await page.waitForTimeout(2500);
await page.click('[data-basemap-toggle], button:has-text("Sombre")').catch(() => {});
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}/04-selecteur-fond.png` });
console.log('📸 04 — sélecteur de fond (Sombre en premier)');
await page.click('text=Clair').catch(() => {});
await page.waitForTimeout(2500);
await page.screenshot({ path: `${OUT}/05-vue-claire-contours-noirs.png` });
console.log('📸 05 — vue claire, contours de parcelle noirs');
await browser.close();
console.log(`Captures : ${OUT}`);
