// M47 P2 — captures de preuve : fiche du segment (AZ0004, avec étiquette source·millésime),
// filtre Renouvellement actif + compteur, calque carte Renouvellement.
// Usage : BASE=http://127.0.0.1:8000/socle/ node qa/m47/captures.mjs
import { chromium } from 'playwright';

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/');
const OUT = 'qa/m47/captures';
const IDU = process.env.IDU || '97404000AZ0004'; // rang 1 du segment (L'Étang-Salé)
const COMMUNE = process.env.COMMUNE || "L'Étang-Salé";

// mac13-arm64 : le chromium bundlé n'est pas supporté → on pilote Google Chrome installé.
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));

const app = async () => {
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
};

async function shot(name, fn) {
  try {
    await fn();
    await page.screenshot({ path: `${OUT}/${name}.png` });
    console.log(`✓ ${name}.png`);
  } catch (e) {
    await page.screenshot({ path: `${OUT}/${name}_FAIL.png` }).catch(() => {});
    console.log(`✗ ${name} — ${e.message}`);
  }
}

// ── 1. Fiche du segment + tiroir « pourquoi » (montre l'étiquette source·millésime M47) ──
await app();
await shot('1_fiche_segment_etiquette', async () => {
  await page.evaluate((idu) => window.__labuse.select(idu), IDU);
  await page.waitForTimeout(1500);
  // ouvrir le tiroir « pourquoi ce rang »
  const btn = page.locator('[data-drawer="renouvellement"] button').first();
  if (await btn.count()) { await btn.click(); await page.waitForSelector('[data-renouv-pourquoi]', { timeout: 8000 }); }
  await page.locator('[data-drawer="renouvellement"]').first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(600);
  // zoom lisible du tiroir : composantes + étiquette « Analyse LABUSE · run servi · maj » (M47)
  const box = await page.locator('[data-drawer="renouvellement"]').first().boundingBox().catch(() => null);
  if (box) {
    await page.screenshot({ path: `${OUT}/1b_fiche_etiquette_zoom.png`,
      clip: { x: Math.max(0, box.x - 6), y: Math.max(0, box.y - 6), width: Math.min(430, box.width + 12), height: Math.min(760, box.height + 12) } });
    console.log('✓ 1b_fiche_etiquette_zoom.png');
  }
});

// ── 2. Filtre Renouvellement actif + compteur ────────────────────────────────
await app();
await shot('2_filtre_renouvellement_compteur', async () => {
  // le panneau filtres (FiltreLabuse) n'apparaît qu'après « Afficher l'analyse LABUSE → »
  await page.getByText("Afficher l'analyse LABUSE", { exact: false }).first().click();
  await page.waitForSelector('[data-results-panel]', { timeout: 10000 });
  await page.waitForTimeout(800);
  const panel = page.locator('[data-results-panel]');
  // déplier le tiroir « Ça va muter ? »
  await panel.getByText('Ça va muter ?', { exact: false }).first().click();
  await page.waitForTimeout(400);
  // activer le chip Renouvellement (section Segments du tiroir)
  await panel.getByText('Renouvellement', { exact: true }).first().click();
  await page.waitForTimeout(2500); // recompte live (getFiltre)
  await panel.getByText('Ça va muter ?', { exact: false }).first().scrollIntoViewIfNeeded().catch(() => {});
  // zoom lisible du panneau gauche : chip Renouvellement ACTIF (section Segments)
  await page.screenshot({ path: `${OUT}/2b_filtre_chip_actif.png`, clip: { x: 0, y: 0, width: 372, height: 900 } });
  console.log('✓ 2b_filtre_chip_actif.png');
  // remonter en tête du panneau : le COMPTEUR (grand nombre) reflète le filtre Renouvellement posé
  await panel.evaluate((el) => { el.scrollTop = 0; });
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/2c_filtre_compteur.png`, clip: { x: 0, y: 0, width: 372, height: 420 } });
  console.log('✓ 2c_filtre_compteur.png');
});

// ── 3. Calque carte Renouvellement (panneau « Couches » ouvert par défaut) ────
await app();
await shot('3_calque_carte_renouvellement', async () => {
  await page.evaluate((c) => window.__labuse.setCommune(c), COMMUNE);
  await page.waitForTimeout(2500);
  // le panneau Couches est ouvert par défaut ; on clique la ligne du calque Renouvellement
  await page.getByRole('button', { name: 'Renouvellement', exact: true }).first().click();
  await page.waitForTimeout(3500); // fetch geojson + rendu + légende
});

await b.close();
console.log('captures →', OUT);
