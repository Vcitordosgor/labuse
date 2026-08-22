// Capture de recette — points permis agrandis + clic prioritaire (Radar permis, M03).
// Deux niveaux de zoom + preuve qu'un clic sur un point ouvre la fiche PERMIS (drawer),
// jamais la fiche parcelle. Usage : BASE=http://localhost:5173/socle/ node qa/permis-points/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 });
page.setDefaultTimeout(30000);
const shot = async (n, note) => { await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`); };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(500);

// ouvrir Radar permis (M03) → charge les points permis sur la carte
await page.click('button[title="Outils"]');
await page.click('[data-outil="permis"]');
await page.waitForSelector('input[placeholder="Aller à une rue, une commune…"]', { state: 'visible' });

// attendre que la source module-extra porte des points permis, récupérer un point
const pt = await page.waitForFunction(() => {
  const m = window.__labuse_map; if (!m) return null;
  const feats = m.querySourceFeatures('module-extra').filter((f) => f.properties?.kind === 'permis' && f.geometry?.type === 'Point');
  if (!feats.length) return null;
  const f = feats[0];
  return { lng: f.geometry.coordinates[0], lat: f.geometry.coordinates[1], pid: String(f.properties.permit_id) };
}, { timeout: 30000 }).then((h) => h.jsonValue());
console.log('point cible:', pt.pid);

// zoom A — vue large (chevauchement possible en centre-ville)
await page.evaluate(({ lng, lat }) => window.__labuse_map.jumpTo({ center: [lng, lat], zoom: 13 }), pt);
await page.waitForTimeout(900);
await shot('01-zoom13-large', 'z13 — points sur vue large');

// zoom B — vue rue (points nettement plus gros, cibles de clic)
await page.evaluate(({ lng, lat }) => window.__labuse_map.jumpTo({ center: [lng, lat], zoom: 16.5 }), pt);
await page.waitForTimeout(900);
await shot('02-zoom16-rue', 'z16.5 — points agrandis, cliquables');

// CLIC sur le point → doit ouvrir la fiche PERMIS, jamais la fiche parcelle
const px = await page.evaluate(({ lng, lat }) => {
  const m = window.__labuse_map; const p = m.project([lng, lat]);
  const r = m.getCanvas().getBoundingClientRect();
  return { x: r.left + p.x, y: r.top + p.y };
}, pt);
await page.mouse.click(px.x, px.y);
await page.waitForSelector('[data-permis-drawer]', { state: 'visible', timeout: 8000 });
const drawer = await page.locator('[data-permis-drawer]').count();
const fiche = await page.locator('[data-fiche-idu]').count();
await shot('03-clic-ouvre-permis', `clic point → drawer permis=${drawer}, fiche parcelle=${fiche}`);

console.log(`RÉSULTAT clic : drawer permis ouvert=${drawer > 0 ? 'OUI' : 'NON'} · fiche parcelle ouverte=${fiche > 0 ? 'OUI (BUG)' : 'NON (ok)'}`);
if (drawer < 1 || fiche > 0) { console.error('❌ ÉCHEC : le clic n’a pas ouvert le permis seul'); process.exitCode = 1; }
else console.log('✅ le clic ouvre le permis, pas la parcelle');

await browser.close();
console.log('OUT:', OUT);
