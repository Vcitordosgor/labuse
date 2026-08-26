// =============================================================================
// FOND SOMBRE — harnais de captures avant/après (mandat fix/fond-sombre)
// -----------------------------------------------------------------------------
// 4 fonds (Sombre/Clair/Plan IGN/Ortho IGN) × 3 zooms (île/commune/parcelle)
// × 2D/3D, + preuve glyphs (étiquettes de zone) au zoom parcelle. Le MÊME script
// tourne sur l'état avant (raster CARTO) et après (sans raster) : TAG=avant|apres.
// Collecte : erreurs console, réponses >=400, requêtes carto* → meta.json.
//
// Usage : TAG=avant BASE=http://localhost:5174/socle/ node qa/fond-sombre/captures_fonds.mjs
// (PNG jamais commités — qa/fond-sombre/out/ est gitignoré)
// =============================================================================
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/');
const TAG = process.env.TAG || 'avant';
const OUT = new URL(`./out/${TAG}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const consoleErrors = [];
const badResponses = [];
const cartoRequests = [];
const fontResponses = [];

// mac13-arm64 : le chromium 1234 attendu par playwright n'est plus installable — on pointe
// l'exécutable 1217 déjà en cache (même moteur que les harnais qa/ historiques).
const EXE = process.env.CHROMIUM
  || `${process.env.HOME}/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell`;
const browser = await chromium.launch({ executablePath: EXE });
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
page.setDefaultTimeout(20000);
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 220)); });
page.on('pageerror', (e) => consoleErrors.push('PAGEERROR ' + String(e).slice(0, 220)));
page.on('response', (r) => {
  if (r.status() >= 400) badResponses.push(`${r.status()} ${r.url().slice(0, 150)}`);
  if (/\/fonts\/.*\.pbf/.test(r.url())) fontResponses.push(`${r.status()} ${r.url().slice(0, 130)}`);
});
page.on('request', (r) => { if (/cartocdn|carto\.com/.test(r.url())) cartoRequests.push(r.url().slice(0, 130)); });

async function shot(name) {
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name}`);
}

const FONDS = [
  ['sombre', 'Sombre'],
  ['clair', 'Clair'],
  ['plan', 'Plan IGN'],
  ['ortho', 'Ortho IGN'],
];

async function setFond(label) {
  await page.click('button[title="Fond de plan"]');
  await page.locator('.floating button', { hasText: label }).first().click();
  await page.mouse.click(700, 520);            // overlay plein écran → referme le menu
  await page.waitForTimeout(2600);             // laisse les tuiles arriver
}

async function toggle3D() {
  await page.locator('button', { hasText: /^3D$/ }).click();
  await page.waitForTimeout(2000);             // easeTo pitch 800 ms + tuiles MNT
}

async function stage(stageName) {
  for (const [key, label] of FONDS) {
    await setFond(label);
    await shot(`${stageName}-${key}-2d`);
    await toggle3D();
    await shot(`${stageName}-${key}-3d`);
    await toggle3D();
  }
}

// ── chargement ────────────────────────────────────────────────────────────────
const communesLoaded = page.waitForResponse((r) => r.url().includes('/communes'), { timeout: 30000 }).catch(() => null);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-omnibox]');
await page.waitForTimeout(4500);               // carte + tuiles initiales

// ── zoom 1 : île entière ─────────────────────────────────────────────────────
await stage('1-ile');

// ── zoom 2 : commune (Saint-Paul) ────────────────────────────────────────────
await communesLoaded;
await page.fill('[data-omnibox]', 'Saint-Paul');
await page.keyboard.press('Enter');
await page.waitForTimeout(3500);
await stage('2-commune');

// ── zoom 3 : parcelle (molette ×10 au centre carte) ──────────────────────────
await page.mouse.move(980, 450);
for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, -300); await page.waitForTimeout(280); }
await page.waitForTimeout(2600);
await stage('3-parcelle');

// ── preuve glyphs : étiquettes de zone (z≥16, couche zonage_parcelle) en Sombre ─
await setFond('Sombre');
await page.click('[data-couches-toggle]');
await page.click('[data-layer="zonage_parcelle"]');
await page.waitForTimeout(2500);
await shot('4-parcelle-sombre-zone-labels');
await page.click('[data-layer="zonage_parcelle"]');
await page.click('[data-couches-toggle]');

// ── preuve glyphs bis : zone URBAINE (centre-ville côtier de Saint-Paul, zone_lib garanti) ─────
await page.fill('[data-omnibox]', 'Saint-Paul');
await page.keyboard.press('Enter');
await page.waitForTimeout(3000);
await page.mouse.move(560, 300);
for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, -300); await page.waitForTimeout(280); }
await page.waitForTimeout(2000);
await page.click('[data-couches-toggle]');
await page.click('[data-layer="zonage_parcelle"]');
await page.waitForTimeout(2800);
await shot('5-urbain-sombre-zone-labels');

// ── fetch direct d'un range de glyphs (statut + octets), indépendant du rendu ─────────────────
const glyphProbe = await page.evaluate(async (base) => {
  const r = await fetch(`${base}fonts/Open Sans Regular/0-255.pbf`);
  const b = await r.arrayBuffer();
  return { status: r.status, bytes: b.byteLength };
}, BASE).catch((e) => ({ status: 0, bytes: 0, err: String(e).slice(0, 120) }));

writeFileSync(`${OUT}/meta.json`, JSON.stringify({ TAG, BASE, consoleErrors, badResponses, cartoRequests, fontResponses, glyphProbe }, null, 2));
console.log(`\nmeta → ${OUT}/meta.json`);
console.log(`console errors: ${consoleErrors.length} · réponses >=400: ${badResponses.length} · requêtes carto: ${cartoRequests.length} · glyphs: ${fontResponses.length} · probe: ${JSON.stringify(glyphProbe)}`);
await browser.close();
