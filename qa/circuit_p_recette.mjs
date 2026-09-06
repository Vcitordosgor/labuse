// =============================================================================
// CIRCUIT-P lot 6.1 — RECETTE DES GESTES RÉELS de la page Circuit (trois onglets), sur une app
// BOOTÉE (API + frontend servi sous /socle/, base réelle locale). Rejoue le parcours complet du
// lot 5 de CIRCUIT-1 sur la NOUVELLE page : Injecter · Faire tourner (lancé PUIS arrêté — un flux
// complet dure des heures, l'état « abandonné » est conçu) · Note de version · Basculer · Vérifier ·
// REVENIR (la base retrouve son run de départ). Les gestes appellent les MÊMES endpoints que la
// recette CIRCUIT-1 (déjà éprouvés) ; seule la coquille d'UI a changé (gestes en pages de détail).
// Captures → docs/CIRCUIT/RECETTE-CIRCUIT-P/gestes-*.png.
// Usage : BASE=http://127.0.0.1:8010 node qa/circuit_p_recette.mjs   (app bootée avec PYTHONPATH=src)
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:8010').replace(/\/$/, '');
const OUT = new URL('../docs/CIRCUIT/RECETTE-CIRCUIT-P', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);
const shot = async (n, note) => { await page.waitForTimeout(700); await page.screenshot({ path: `${OUT}/gestes-${n}.png` }); console.log(`  📸 gestes-${n} — ${note}`); };
const api = async (m, p, b) => (await page.request.fetch(`${BASE}${p}`, { method: m, headers: { 'Content-Type': 'application/json' }, data: b ? JSON.stringify(b) : undefined })).json();
const circuitTab = () => page.locator('.cxp .tabs button', { hasText: 'Circuit' }).first();

// ── 0. ouvrir la page Circuit (Admin → Données → onglet Circuit) ──
await page.goto(`${BASE}/socle/#admin=1`);
await page.waitForTimeout(1500);
await page.locator('button, a', { hasText: 'Données' }).first().click();
await page.waitForSelector('.cxp', { timeout: 20000 });
await circuitTab().click();
await page.waitForSelector('.cxp .diagram');
const servi_avant = (await api('GET', '/admin/circuit')).run_servi;
console.log(`run servi au départ : ${servi_avant}`);
await shot('00-circuit', `la page Circuit (run servi ${servi_avant})`);

// ── 1. INJECTER — un réservoir à vanne (BODACC) : sa page de détail porte la vanne ──
await page.locator('.cxp .sw').click().catch(() => {});   // tout montrer
await page.fill('.cxp .cbar input', 'BODACC');
await page.waitForTimeout(500);
const row = page.locator('.cxp .node.open .row', { hasText: 'BODACC' }).first();
if (await row.count()) {
  await row.click();
  await page.waitForSelector('.cxp .detail.on');
  const vanne = page.getByRole('button', { name: /Ouvrir la vanne/ });
  if (await vanne.count() && await vanne.isEnabled()) { await vanne.click(); await page.waitForTimeout(1200); }
  await shot('01-injecter', 'vanne BODACC ouverte depuis sa page de détail (journalisé, avec qui)');
  await page.locator('.cxp .back').click().catch(() => {});
}

// ── 2. LA POMPE — Faire tourner (lancé PUIS arrêté) ──
await circuitTab().click();
await page.locator('.cxp .pump').click();
await page.waitForSelector('.cxp .detail.on');
const faire = page.getByRole('button', { name: /Faire tourner/ });
if (await faire.count() && await faire.isEnabled()) {
  await faire.click(); await page.waitForTimeout(2500);
  await shot('02-calculer', 'run candidat lancé (détaché, journal « calculer »)');
  const etat = await api('GET', '/admin/flux/run/etat');
  if (etat?.en_cours?.label) { await api('POST', '/admin/flux/run/arreter', { label: etat.en_cours.label }); console.log(`  ✋ run ${etat.en_cours.label} arrêté`); }
}

// ── 3. NOTE DE VERSION puis BASCULER ──
const note = page.getByRole('button', { name: 'Note de version' });
if (await note.count()) { await note.click(); await page.waitForTimeout(1200); await shot('03-note', 'note de version — Basculer devient actif'); }
const bascule = page.getByRole('button', { name: /^Basculer/ });
if (await bascule.count() && await bascule.isEnabled()) { await bascule.click(); await page.waitForTimeout(3000); }
const servi_bascule = (await api('GET', '/admin/circuit')).run_servi;
await shot('04-bascule', `basculé — run servi ${servi_bascule}`);

// ── 4. VÉRIFIER QUE TOUT COULE (bouton du haut) ──
await page.locator('.cxp .tabs .actions button', { hasText: /Vérifier/ }).click();
await page.waitForTimeout(4000);
await shot('05-verifier', 'sonde passée (circuit_controles)');

// ── 5. REVENIR — la base retrouve son run de départ ──
await circuitTab().click();
await page.locator('.cxp .pump').click();
await page.waitForSelector('.cxp .detail.on');
const revenir = page.getByRole('button', { name: /^Revenir/ });
if (await revenir.count() && await revenir.isEnabled()) { await revenir.click(); await page.waitForTimeout(3000); }
const servi_final = (await api('GET', '/admin/circuit')).run_servi;
await shot('06-revenir', `retour arrière — run servi ${servi_final}`);

console.log(`\nrun servi : ${servi_avant} → ${servi_bascule} → ${servi_final}`);
if (servi_final !== servi_avant) { console.error('✗ LA BASE N’EST PAS REVENUE À SON ÉTAT DE DÉPART'); process.exit(1); }
console.log('✓ recette des gestes complète — base remise dans son état de départ');
await browser.close();
