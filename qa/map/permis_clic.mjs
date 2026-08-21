// M-PERMIS-CLIC — vérifie : (1) points permis nettement plus grands et adaptés au zoom ;
// (2) un clic sur un point ouvre le PERMIS (drawer) et JAMAIS la fiche parcelle dessous.
// Deux captures : zoom faible (île) + zoom de travail. Le hook QA `window.__labuse_map` (MapView)
// donne accès à la carte pour localiser/projeter un point permis et cliquer précisément dessus.
//
// Prérequis : backend LABUSE (8000) + front dev (5173) en marche, radar permis alimenté.
//   BASE=http://localhost:5173/socle/ node qa/map/permis_clic.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = process.env.BASE || 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const log = (...a) => console.log(...a);
const soft = async (fn, w) => { try { await fn() } catch (e) { log('WARN', w, String(e).slice(0, 140)) } };

const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => !!window.__labuse_map, { timeout: 30000 }).catch(() => log('WARN carte non prête'));
await page.waitForTimeout(1500);

// Outils → radar permis (M03) : la carte se peuple de tous les permis géocodés.
await soft(async () => { await page.getByRole('button', { name: 'Outils' }).first().click(); await page.waitForTimeout(600); }, 'outils');
await soft(async () => { await page.locator('[data-outil="permis"]').click(); }, 'outil permis');
await page.waitForTimeout(3500);

const hasPts = await page.waitForFunction(() => {
  const m = window.__labuse_map; if (!m) return false;
  try { return m.querySourceFeatures('module-extra', { filter: ['==', ['get', 'kind'], 'permis'] }).length > 0 } catch { return false }
}, { timeout: 20000 }).then(() => true).catch(() => false);
log('points permis présents :', hasPts);

// CAPTURE A — zoom FAIBLE (île) : les points restent lisibles (petits + contour).
await soft(async () => { await page.evaluate(() => window.__labuse_map.easeTo({ zoom: 11, duration: 250 })); }, 'zoomA');
await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/permis_zoom_faible.png` });
log('capture A (zoom faible) → permis_zoom_faible.png');

// Localiser un point permis, y voler (CAPTURE B, zoom de travail), puis CLIQUER dessus.
const coord = await page.evaluate(() => {
  const m = window.__labuse_map;
  const fs = m.querySourceFeatures('module-extra', { filter: ['==', ['get', 'kind'], 'permis'] });
  return fs.length ? fs[0].geometry.coordinates : null;
});
if (!coord) { log('aucun point permis — clic non testable'); await b.close(); process.exit(0); }

await page.evaluate((c) => window.__labuse_map.easeTo({ center: c, zoom: 17, duration: 250 }), coord);
await page.waitForTimeout(1400);
await page.screenshot({ path: `${OUT}/permis_zoom_travail.png` });
log('capture B (zoom de travail) → permis_zoom_travail.png');

// projeter la coord du point en pixel écran et cliquer le canvas exactement dessus
const px = await page.evaluate((c) => { const p = window.__labuse_map.project(c); return { x: p.x, y: p.y } }, coord);
const canvas = page.locator('canvas.maplibregl-canvas').first();
const box = await canvas.boundingBox();
await page.mouse.click(box.x + px.x, box.y + px.y);
await page.waitForTimeout(900);

const drawer = await page.locator('[data-permis-drawer]').count();
const fiche = await page.locator('[data-fiche-idu]').count();     // fiche parcelle : NE DOIT PAS s'ouvrir
await page.screenshot({ path: `${OUT}/permis_clic_drawer.png` });
log('drawer PERMIS ouvert :', drawer > 0);
log('fiche PARCELLE ouverte (doit être 0) :', fiche);
await b.close();
console.log(drawer > 0 && fiche === 0
  ? 'OK — un clic sur le point ouvre le PERMIS, pas la parcelle'
  : 'À VÉRIFIER (voir WARN / captures)');
