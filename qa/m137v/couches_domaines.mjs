// M137-V — captures : BPE colorée par domaine (7 couleurs) + légende-filtre par domaine ;
// ZNIEFF libellé sur une ligne ; OSM sans arrêts de bus (retirés de l'affichage).
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 150)) } };
const openCouches = async () => {
  if (await page.locator('[data-layer="parcelles"]').isVisible().catch(() => false)) return;
  const t = page.locator('[data-couches-toggle]').first(); if (await t.count()) { await t.click(); await page.waitForTimeout(500); }
};
const pickCommune = async (nom) => {
  await page.locator('[data-commune-select]').click(); await page.waitForTimeout(500);
  await page.getByRole('button', { name: nom, exact: true }).click(); await page.waitForTimeout(3000);
};

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);
await openCouches();
// libellé ZNIEFF sur une ligne (panneau)
console.log('ZNIEFF label:', (await page.locator('[data-layer="znieff"]').innerText().catch(() => '?')).replace(/\s+/g, ' ').trim());

// activer BPE + zoomer sur Le Port
await soft(async () => { await page.locator('[data-layer="equipements_bpe"]').click(); await page.waitForTimeout(400); }, 'toggle BPE');
await soft(() => pickCommune('Le Port'), 'commune Le Port');
await soft(async () => { for (let i = 0; i < 3; i++) { await page.mouse.move(880, 500); await page.mouse.wheel(0, -500); await page.waitForTimeout(700); } await page.waitForTimeout(2000); }, 'zoom');
const nDomChips = await page.locator('[data-legend-bpe-dom]').count();
console.log('A · BPE par domaine · puces légende:', nDomChips);
await page.screenshot({ path: `${OUT}/A_bpe_par_domaine.png`, fullPage: false });

// filtre : masquer le domaine A (services, le plus nombreux) → les cercles gris disparaissent
await soft(async () => { await page.locator('[data-legend-bpe-dom="A"]').click(); await page.waitForTimeout(1500); }, 'filtre A off');
console.log('B · domaine A masqué (services)');
await page.screenshot({ path: `${OUT}/B_bpe_filtre_domaine.png`, fullPage: false });

await b.close();
console.log('captures écrites dans', OUT);
