// FOND-SOMBRE — preuve de rendu TEXTE (glyphs embarqués) : omnibox → IDU urbain (zone Ub),
// couche zonage_parcelle ON, z≥16 → les étiquettes de zone doivent se peindre avec la police locale.
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/');
const OUT = new URL('./out/apres', import.meta.url).pathname;
const EXE = process.env.CHROMIUM
  || `${process.env.HOME}/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell`;

const fontResponses = [];
const consoleErrors = [];
const browser = await chromium.launch({ executablePath: EXE });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
page.setDefaultTimeout(20000);
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
page.on('response', (r) => { if (/\/fonts\/.*\.pbf/.test(r.url())) fontResponses.push(`${r.status()} ${r.url().slice(0, 130)}`); });

// deep-link commune (hash #c=) → cadrage Saint-Paul, puis molette sur le CENTRE-VILLE (dense,
// zoné U*) jusqu'à z≥16 où les étiquettes de zone se peignent.
await page.goto(`${BASE}#c=Saint-Paul`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-omnibox]');
await page.waitForTimeout(6000);                 // carte + geojson commune
await page.mouse.move(720, 430);
for (let i = 0; i < 12; i++) { await page.mouse.wheel(0, -300); await page.waitForTimeout(280); }
await page.waitForTimeout(2500);
await page.click('[data-couches-toggle]');
await page.click('[data-layer="zonage_parcelle"]');
await page.waitForTimeout(5000);
await page.screenshot({ path: `${OUT}/6-glyphs-zone-ub.png` });
writeFileSync(`${OUT}/glyph_proof.json`, JSON.stringify({ fontResponses, consoleErrors }, null, 2));
console.log('fonts:', fontResponses, '· console errors:', consoleErrors.length);
await browser.close();
