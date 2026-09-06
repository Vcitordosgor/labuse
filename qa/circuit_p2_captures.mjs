// =============================================================================
// CIRCUIT-P2 lot 5.1 — RECETTE NAVIGATEUR (visuelle) des retours de recette du 06/09.
// Rend la VRAIE page (frontend/circuit-harness.html) ; l'API est interceptée avec des fixtures
// RÉELLES capturées de la base (qa/fixtures/circuit_p2) → aucune base touchée. Les tâches longues
// (contrôle, agents) sont simulées par une petite machine à états dans le stub (progression →
// message ; agents sans crédit → message clair). Parcours : Résumé sans enrobage → repère 31/68 →
// compteur → Circuit (interrupteur 2 positions) → Vérifier (progression → message) → Agents (sans
// crédit) → détail réservoir/robinet/pompe (+ Échap) → journal groupé (dépliage, filtre vide).
// Usage : BASE=http://127.0.0.1:5173 node qa/circuit_p2_captures.mjs
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, readFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:5173').replace(/\/$/, '');
const OUT = new URL('../docs/CIRCUIT/RECETTE-CIRCUIT-P/', import.meta.url).pathname;
const FIX = new URL('./fixtures/circuit_p2', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const fx = (n) => JSON.parse(readFileSync(`${FIX}/${n}.json`, 'utf8'));
const CIRCUIT = fx('circuit'), COMPTEUR = fx('compteur'), JOURNAL = fx('journal'),
  RESERVOIR = fx('reservoir'), ROBINET = fx('robinet'), POMPE = fx('pompe');

// ── machine à états des tâches longues (contrôle / agents) ──
let verif = 'idle';  // idle | run | done
const tachesEtat = () => ({
  verifier: verif === 'run'
    ? { etat: 'en_cours', fait: 3, total: 5, message: 'Eau ancienne — 3 / 5', maj: '2026-09-06T08:00:00Z' }
    : verif === 'done'
      ? { etat: 'termine', fait: 5, message: 'Contrôle terminé : 0 fuite(s), 1 eau ancienne, 0 écart(s) ouverts.', maj: '2026-09-06T08:01:00Z' }
      : null,
  agents: null,
});

const browser = await chromium.launch({ executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);
page.on('pageerror', (e) => console.log('  ⚠ PAGEERROR', String(e).slice(0, 200)));

await page.route((url) => new URL(url).pathname.startsWith('/admin/'), async (route) => {
  const url = route.request().url(), m = route.request().method();
  const json = (o) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
  if (m === 'GET') {
    if (/\/admin\/circuit\/journal/.test(url)) return json(JOURNAL);
    if (/\/admin\/circuit\/compteur/.test(url)) return json(COMPTEUR);
    if (/\/admin\/circuit\/taches/.test(url)) return json(tachesEtat());
    if (/\/admin\/circuit\/reservoir\//.test(url)) return json(RESERVOIR);
    if (/\/admin\/circuit\/robinet\//.test(url)) return json(ROBINET);
    if (/\/admin\/circuit\/pompe/.test(url)) return json(POMPE);
    if (/\/admin\/circuit\/note-version/.test(url)) return json({ candidat: 'q_v12', reservoirs: [], chiffres_recalcules: [], ecart_classement: null });
    if (/\/admin\/circuit(\?|$)/.test(url)) return json(CIRCUIT);
  }
  if (m === 'POST') {
    if (/\/admin\/circuit\/verifier/.test(url)) { verif = 'run'; return json({ ok: true, lance: true }); }
    if (/\/admin\/circuit\/agents/.test(url)) return json({ ok: false, credit: false, message: 'Crédit API épuisé — recharge, puis relance.' });
  }
  return json({ ok: true });
});

const shot = async (name, note) => {
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name} — ${note}`);
};
const tab = (t) => page.locator('.cxp .tabs button', { hasText: t }).first();

await page.goto(`${BASE}/socle/circuit-harness.html`);
await page.waitForSelector('.cxp .res', { timeout: 20000 });

// ── P2-01 — Résumé sans enrobage ──
await shot('P2-01-resume', `Résumé sans enrobage (${CIRCUIT.resume.total} à regarder)`);

// ── P2-02 — le repère « N / 68 » ouvre la page du compteur ──
await page.locator('.cxp .kpi.lien').first().click();
await page.waitForSelector('.cxp .detail.on');
await shot('P2-02-compteur', 'repère réservoirs → page du compteur (par état + non servies)');
await page.locator('.cxp .back').click();

// ── P2-03 / P2-04 — le Circuit, interrupteur dans les deux positions ──
await tab('Circuit').click();
await page.waitForSelector('.cxp .diagram');
await page.locator('.cxp .node .hd').first().click().catch(() => {});
await page.waitForTimeout(300);
await shot('P2-03-interrupteur-on', 'interrupteur ALLUMÉ — seulement ce qui cloche');
await page.locator('.cxp .sw').click();
await page.waitForTimeout(300);
await shot('P2-04-interrupteur-off', 'interrupteur ÉTEINT — tout (titre de colonne identique)');

// ── P2-05 / P2-06 — Vérifier que tout coule : progression → message ──
await page.locator('.cxp .tabs .actions button', { hasText: /Vérifier/ }).click();
await page.waitForTimeout(700);
await shot('P2-05-verifier-progression', 'contrôle en cours — ligne de progression sous les onglets');
verif = 'done';
await page.waitForTimeout(1900);  // la prochaine sonde des tâches (1,5 s) voit « terminé »
await shot('P2-06-verifier-message', 'contrôle terminé — message + Résumé rafraîchi');

// ── P2-07 — Envoyer les agents : cas sans crédit (jamais grisé sans mot) ──
await page.locator('.cxp .tabs .actions button', { hasText: /agents/ }).click();
await page.waitForTimeout(500);
await shot('P2-07-agents-sans-credit', 'agents sans crédit → message clair, rien lancé');

// ── P2-08 — détail réservoir (via une ligne du Circuit ; interrupteur déjà ÉTEINT = tout montrer) ──
await tab('Circuit').click();
await page.waitForSelector('.cxp .diagram');
await page.locator('.cxp .node:not(.open) .hd').first().click().catch(() => {});  // ouvre un bloc fermé
await page.waitForTimeout(300);
const trow = page.locator('.cxp .node.open .row').first();
if (await trow.count()) {
  await trow.click();
  await page.waitForSelector('.cxp .detail.on');
  await shot('P2-08-detail-reservoir', 'page de détail d\'un réservoir (bouton « Envoyer un agent » actif)');
  await page.keyboard.press('Escape');
  await page.waitForSelector('.cxp .diagram');
}

// ── P2-09 — détail robinet (revenir d'un détail a remonté le diagramme → interrupteur ON par
//    défaut ; on l'éteint pour montrer toutes les lignes, puis on ouvre un bloc catégorie fermé) ──
await page.locator('.cxp .sw.on').click().catch(() => {});   // tout montrer
await page.waitForTimeout(200);
await page.locator('.cxp .node:not(.open) .hd').last().click().catch(() => {});
await page.waitForTimeout(300);
const rrow = page.locator('.cxp .node.open .row').last();
if (await rrow.count()) {
  await rrow.click();
  await page.waitForSelector('.cxp .detail.on');
  await shot('P2-09-detail-robinet', 'page de détail d\'un robinet (passe-plat neutre, hors moteur ambre)');
  await page.keyboard.press('Escape');
  await page.waitForSelector('.cxp .diagram');
}

// ── P2-10 — détail pompe + Échap ──
await page.waitForSelector('.cxp .diagram');
await page.locator('.cxp .pump').click();
await page.waitForSelector('.cxp .detail.on');
await shot('P2-10-detail-pompe', 'page de détail de la pompe');
await page.keyboard.press('Escape');
await page.waitForSelector('.cxp .diagram');

// ── P2-11 / P2-12 — journal groupé : une ligne, puis dépliage ──
await tab('Journal').click();
await page.waitForSelector('.cxp .jl');
await shot('P2-11-journal-groupe', `journal — passage groupé sur une ligne (${JOURNAL.total} passages)`);
const grp = page.locator('.cxp .jl.grp').first();
if (await grp.count()) {
  await grp.click();
  await page.waitForTimeout(400);
  await shot('P2-12-journal-deplie', 'journal — passage groupé déplié source par source');
}

// ── P2-13 — un filtre de catégorie vide (présent même vide) ──
const vide = page.locator('.cxp .jf button', { hasText: 'sonde' }).first();
if (await vide.count()) {
  await vide.click();
  await page.waitForTimeout(400);
  await shot('P2-13-journal-filtre-vide', 'filtre « sonde » présent même vide');
}

console.log('\n✓ recette P2 complète — captures P2-01…P2-13 dans docs/CIRCUIT/RECETTE-CIRCUIT-P/');
await browser.close();
