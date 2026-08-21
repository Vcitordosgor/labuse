// M137-U — captures : couches ZNIEFF (contrainte) et Équipements INSEE BPE (2e source, distincte d'OSM).
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 150)) } };
const pickCommune = async (nom) => {
  await page.locator('[data-commune-select]').click(); await page.waitForTimeout(500);
  await page.getByRole('button', { name: nom, exact: true }).click(); await page.waitForTimeout(3000);
};
const openCouches = async () => {
  if (await page.locator('[data-layer="parcelles"]').isVisible().catch(() => false)) return;  // déjà ouvert
  const t = page.locator('[data-couches-toggle]').first();
  if (await t.count()) { await t.click(); await page.waitForTimeout(500); }
};
const isOn = async (key) => (await page.locator(`[data-layer="${key}"] span.bg-mint`).count()) > 0;

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);
await openCouches();

// ── A) ZNIEFF sur une commune (Saint-Paul : ZNIEFF côtières + Hauts) ──
await soft(async () => { await page.locator('[data-layer="znieff"]').click(); await page.waitForTimeout(800); }, 'toggle znieff');
await soft(() => pickCommune('Saint-Paul'), 'commune Saint-Paul');
console.log('A · ZNIEFF on:', await isOn('znieff'), '· légende ZNIEFF:', (await page.locator('[data-legend-znieff]').count()) > 0);
await page.screenshot({ path: `${OUT}/A_znieff.png`, fullPage: false });
// le « i » de la ZNIEFF (type I / type II distingués)
await soft(async () => {
  await page.locator('[data-layer="znieff"]').locator('xpath=following-sibling::*').getByText('i', { exact: true }).first().hover();
  await page.waitForTimeout(700);
}, 'i znieff');
await page.screenshot({ path: `${OUT}/A_znieff_info.png`, fullPage: false });

// ── B) Équipements OSM + BPE (les deux, distincts) sur une commune dense (Le Port, petite/urbaine) ──
await openCouches();
await soft(async () => { if (await isOn('znieff')) await page.locator('[data-layer="znieff"]').click(); }, 'znieff off');   // vue nette
await soft(async () => { await page.locator('[data-layer="equipements"]').click(); await page.waitForTimeout(400); }, 'toggle OSM');
await soft(async () => { await page.locator('[data-layer="equipements_bpe"]').click(); await page.waitForTimeout(400); }, 'toggle BPE');
await soft(() => pickCommune('Le Port'), 'commune Le Port');
// zoomer à l'échelle rue (icônes OSM + cercles BPE lisibles, minzoom 12)
await soft(async () => { for (let i = 0; i < 3; i++) { await page.mouse.move(880, 500); await page.mouse.wheel(0, -500); await page.waitForTimeout(700); } await page.waitForTimeout(2000); }, 'zoom rue');
console.log('B · OSM on:', await isOn('equipements'), '· BPE on:', await isOn('equipements_bpe'),
            '· légende BPE:', (await page.locator('[data-legend-bpe]').count()) > 0);
await page.screenshot({ path: `${OUT}/B_equipements_osm_bpe.png`, fullPage: false });

await b.close();
console.log('captures écrites dans', OUT);
