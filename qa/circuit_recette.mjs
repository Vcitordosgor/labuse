// =============================================================================
// CIRCUIT-1 lot 5.7 — RECETTE NAVIGATEUR de la page Circuit, sur la base réelle LOCALE.
// Gestes joués : Injecter (BODACC, job court) · Calculer (lancé PUIS ARRÊTÉ proprement —
// un flux-run complet dure des heures, l'état « abandonné » est un état conçu) · Note de
// version · Basculer (vers le candidat q_v12 RÉEL) · Vérifier que tout coule · REVENIR
// (la base est remise dans son état de départ : run servi q_v11_m137).
// Captures avant/après de chaque geste → docs/CIRCUIT/RECETTE-CIRCUIT-1/.
// Usage : BASE=http://127.0.0.1:8010 node qa/circuit_recette.mjs
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:8010').replace(/\/$/, '');
const OUT = new URL('../docs/CIRCUIT/RECETTE-CIRCUIT-1', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

// chromium local (cache -1217 — la version npm attend -1234) : exécutable pointé explicitement.
const browser = await chromium.launch({ executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);

const shot = async (name, note) => {
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name} — ${note}`);
};
const api = async (method, path, body) => {
  const r = await page.request.fetch(`${BASE}${path}`, {
    method, headers: { 'Content-Type': 'application/json' },
    data: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
};

// ── 0. la page Circuit (Données ouvre sur l'onglet Circuit par défaut) ──
await page.goto(`${BASE}/socle/#admin=1`);
await page.waitForTimeout(1500);
await page.locator('button, a', { hasText: 'Données' }).first().click();
await page.waitForSelector('.cx .status', { timeout: 20000 });
const servi_avant = (await api('GET', '/admin/circuit')).run_servi;
console.log(`run servi au départ : ${servi_avant}`);
await shot('01-circuit-avant', `la page Circuit (run servi ${servi_avant})`);

// ── 1. INJECTER — BODACC (vanne courte) ──
await page.fill('.cx .legend input', 'BODACC');
await page.waitForTimeout(400);
await page.locator('.cx .row', { hasText: 'BODACC' }).first().click();
await shot('02-injecter-avant', 'réservoir BODACC sélectionné, fiche du bas ouverte');
const vanneBtn = page.getByRole('button', { name: /Ouvrir la vanne/ });
if (await vanneBtn.count()) {
  await vanneBtn.click();
  await page.waitForTimeout(1200);
  await shot('03-injecter-apres', 'vanne BODACC ouverte (job détaché, journalisé avec qui)');
} else {
  console.log('  ⚠ BODACC sans vanne à l’écran (sonde absente en local ?) — geste joué par l’API');
  await api('POST', '/admin/sources/29/veille/injecter').catch(() => {});
  await shot('03-injecter-apres', 'injection BODACC (repli API — pas de ligne de veille locale)');
}
await page.fill('.cx .legend input', '');
await page.locator('.cx .row.sel').first().click().catch(() => {});

// ── 2. CALCULER — lancé PUIS ARRÊTÉ (état « abandonné », conçu pour ça) ──
await page.getByRole('button', { name: 'Faire tourner' }).click();
await page.waitForTimeout(2500);
await shot('04-calculer-lance', 'run candidat lancé (détaché, journal « calculer » avec qui)');
const etat = await api('GET', '/admin/flux/run/etat');
if (etat?.en_cours?.label) {
  await api('POST', '/admin/flux/run/arreter', { label: etat.en_cours.label });
  console.log(`  ✋ run ${etat.en_cours.label} arrêté proprement (état abandonné)`);
}
await page.waitForTimeout(800);

// ── 3. NOTE DE VERSION puis BASCULER vers le candidat réel (q_v12) ──
await page.getByRole('button', { name: 'Note de version' }).click();
await page.waitForTimeout(1200);
await shot('05-note-version', 'note de version du candidat (registre) — Basculer devient actif');
await page.getByRole('button', { name: 'Basculer', exact: true }).click();
await page.waitForTimeout(3000);
const servi_bascule = (await api('GET', '/admin/circuit')).run_servi;
await shot('06-bascule-apres', `basculé — run servi ${servi_bascule} (manifeste posé, un seul écrit)`);

// ── 4. VÉRIFIER QUE TOUT COULE ──
await page.getByRole('button', { name: /Vérifier que tout coule/ }).click();
await page.waitForTimeout(4000);
await shot('07-verifier-apres', 'sonde passée (circuit_controles, verdict au bandeau)');

// ── 5. REVENIR — la base retrouve son état de départ ──
await page.getByRole('button', { name: 'Revenir' }).click();
await page.waitForTimeout(3000);
const servi_final = (await api('GET', '/admin/circuit')).run_servi;
await shot('08-revenir-apres', `retour arrière joué — run servi ${servi_final}`);

console.log(`\nrun servi : ${servi_avant} → ${servi_bascule} → ${servi_final}`);
if (servi_final !== servi_avant) {
  console.error('✗ LA BASE N’EST PAS REVENUE À SON ÉTAT DE DÉPART');
  process.exit(1);
}
console.log('✓ recette complète — base locale remise dans son état de départ');
await browser.close();
