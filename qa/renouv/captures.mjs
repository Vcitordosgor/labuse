// M-RENOUV lot B — captures de preuve (fiche badge+tiroir, carte toggle Saint-Paul, outil liste).
// Usage : BASE=http://127.0.0.1:8031/socle/ node qa/renouv/captures.mjs
import { chromium } from 'playwright';

const BASE = (process.env.BASE || 'http://127.0.0.1:8031/socle/').replace(/\/?$/, '/');
const OUT = 'qa/renouv';
const IDU = process.env.IDU || '97403000AP1902'; // rang 1 du segment

const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('pageerror:', e.message));

const app = async () => {
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
};

// ── 1. fiche : badge (tiroir fermé) ──────────────────────────────────────────
await app();
await page.evaluate((idu) => window.__labuse.select(idu), IDU);
await page.waitForSelector('[data-renouv-badge]', { timeout: 20000 });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/fiche_badge_ferme.png`, fullPage: false });
console.log('✓ fiche_badge_ferme.png (badge + libellé doctrinal)');

// ── 2. fiche : tiroir « pourquoi » ouvert (4 composantes) ────────────────────
await page.click('[data-drawer="renouvellement"] button');
await page.waitForSelector('[data-renouv-pourquoi]', { timeout: 8000 });
await page.evaluate(() => document.querySelector('[data-drawer="renouvellement"]')?.scrollIntoView({ block: 'center' }));
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}/fiche_pourquoi_ouvert.png` });
console.log('✓ fiche_pourquoi_ouvert.png (4 composantes, barres points/max)');

// ── 3. carte Saint-Paul : toggle Renouvellement ON + légende ────────────────
await app();
await page.evaluate(() => window.__labuse.setCommune('Saint-Paul'));
await page.waitForTimeout(2500);
// le toggle vit dans le panneau gauche, section couches (libellé exact « Renouvellement »)
const toggle = page.locator('text=Renouvellement').first();
await toggle.click();
await page.waitForTimeout(3500); // fetch geojson + rendu + toast troncature
await page.screenshot({ path: `${OUT}/carte_saintpaul_toggle_on.png` });
console.log('✓ carte_saintpaul_toggle_on.png (couche cuivre + légende + toast troncature)');

// ── 4. outil « Renouvellement » : liste triable ──────────────────────────────
await app();
await page.evaluate(() => window.__labuse.setModule('renouvellement'));
await page.waitForSelector('[data-renouv-row]', { timeout: 20000 });
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/outil_liste.png` });
console.log('✓ outil_liste.png (liste triable, bandeau définition + limite)');

await b.close();
console.log('4/4 captures OK →', OUT);
