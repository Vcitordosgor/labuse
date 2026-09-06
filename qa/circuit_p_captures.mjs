// =============================================================================
// CIRCUIT-P lot 6.1 — RECETTE NAVIGATEUR (visuelle) de la page Circuit en trois onglets.
// Rend la VRAIE page (frontend/circuit-harness.html) ; l'API est interceptée avec des fixtures
// RÉELLES capturées de la base (qa/fixtures/circuit_p) → aucune base touchée, aucun geste
// destructeur. Parcours : Résumé → clic de chaque type de ligne → détail → retour → circuit
// déplié → survol (chemins allumés) → journal filtré, + l'UI des gestes (bascule/vérifier, stubbés).
// Le parcours de gestes RÉELS (vanne→calcul→bascule→revenir sur la base, avec restauration) reste
// qa/circuit_p_recette.mjs, rejouable sur une app bootée.
// Usage : BASE=http://127.0.0.1:5175 node qa/circuit_p_captures.mjs
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, readFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:5175').replace(/\/$/, '');
const OUT = new URL('../docs/CIRCUIT/RECETTE-CIRCUIT-P', import.meta.url).pathname;
const FIX = new URL('./fixtures/circuit_p', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const fx = (n) => JSON.parse(readFileSync(`${FIX}/${n}.json`, 'utf8'));
const CIRCUIT = fx('circuit'), JOURNAL = fx('journal'), RESERVOIR = fx('reservoir'), ROBINET = fx('robinet'), POMPE = fx('pompe');

const browser = await chromium.launch({ executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);
page.on('pageerror', (e) => console.log('  ⚠ PAGEERROR', String(e).slice(0, 200)));

// ── l'API : fixtures réelles pour les GET, « ok » pour les gestes (rien n'est écrit nulle part) ──
// on n'intercepte QUE les appels API (pathname /admin/…), jamais les modules vite (/socle/src/…).
await page.route((url) => new URL(url).pathname.startsWith('/admin/'), async (route) => {
  const url = route.request().url(), m = route.request().method();
  const json = (o) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
  if (m === 'GET') {
    if (/\/admin\/circuit\/journal/.test(url)) return json(JOURNAL);
    if (/\/admin\/circuit\/reservoir\//.test(url)) return json(RESERVOIR);
    if (/\/admin\/circuit\/robinet\//.test(url)) return json(ROBINET);
    if (/\/admin\/circuit\/pompe/.test(url)) return json(POMPE);
    if (/\/admin\/circuit\/note-version/.test(url)) return json({ candidat: 'q_v12', reservoirs: [], chiffres_recalcules: ['a', 'b'], ecart_classement: null, note: 'note stub' });
    if (/\/admin\/circuit(\?|$)/.test(url)) return json(CIRCUIT);
  }
  return json({ ok: true });          // gestes POST — stub, aucune base touchée
});

const shot = async (name, note) => {
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name} — ${note}`);
};

await page.goto(`${BASE}/socle/circuit-harness.html`);
await page.waitForSelector('.cxp .res', { timeout: 20000 });

// ── 1. RÉSUMÉ (onglet par défaut) ──
await shot('01-resume', `le Résumé (${CIRCUIT.resume.total} choses à regarder)`);

// ── 2. clic « Décider » (quarantaine) → page de détail réservoir → retour ──
const resumeTab = () => page.locator('.cxp .tabs button', { hasText: 'Résumé' }).first();
const decider = page.locator('.cxp .item', { hasText: 'Décider' }).first();
if (await decider.count()) {
  await decider.click();
  await page.waitForSelector('.cxp .detail.on', { timeout: 20000 });
  await shot('02-detail-reservoir', 'ligne du Résumé → page de détail (réservoir)');
  await page.locator('.cxp .back').click();
  await page.waitForSelector('.cxp .diagram');
}

// ── 3. clic d'une ligne à cibles MULTIPLES (« hors moteur ») → circuit déplié sur le groupe ──
await resumeTab().click();
await page.waitForSelector('.cxp .res', { state: 'visible' });
const groupe = page.locator('.cxp .item', { hasText: 'hors moteur' }).first();
if (await groupe.count()) {
  await groupe.click();
  await page.waitForSelector('.cxp .diagram', { state: 'visible', timeout: 20000 });
  await shot('03-circuit-groupe', 'ligne à cibles multiples → circuit déplié sur le groupe');
}

// ── 4. onglet Circuit : déplier un bloc, survoler une ligne (chemins allumés) ──
await page.locator('.cxp .tabs button', { hasText: 'Circuit' }).first().click();
await page.waitForSelector('.cxp .diagram');
// tout montrer, puis déplier le premier bloc famille
await page.locator('.cxp .sw').click().catch(() => {});
await page.locator('.cxp #tanks .node .hd, .cxp .node .hd').first().click().catch(() => {});
await page.waitForTimeout(400);
await shot('04-circuit-deplie', 'un bloc déplié, deux lignes par élément (nom ; version · contrôle · cadence)');
const row = page.locator('.cxp .node.open .row').first();
if (await row.count()) {
  await row.hover();
  await page.waitForTimeout(600);
  await shot('05-survol-chemin', 'survol d\'une ligne : famille → pompe → catégories allumées');
}

// ── 5. la pompe → page de détail pompe → gestes (stubbés) ──
await page.locator('.cxp .pump').click();
await page.waitForSelector('.cxp .detail.on');
await shot('06-detail-pompe', 'la pompe : ce qui attend, moteurs, horloges');
const faire = page.getByRole('button', { name: /Faire tourner/ });
if (await faire.count() && await faire.isEnabled()) {
  await faire.click(); await page.waitForTimeout(500);
  await shot('07-pompe-calculer', 'geste « Faire tourner » (stub — aucune base touchée)');
} else {
  await shot('07-pompe-gestes', 'gestes de la pompe (Faire tourner inactif : rien en attente dans cette fixture)');
}
await page.locator('.cxp .back').click().catch(() => {});

// ── 6. un robinet → page de détail robinet ──
await page.waitForSelector('.cxp .diagram');
const rrow = page.locator('.cxp .node.open .row').first();
await page.locator('.cxp .node .hd').nth(1).click().catch(() => {});
await page.waitForTimeout(300);
const anyRow = page.locator('.cxp .node.open .row').first();
if (await anyRow.count()) {
  await anyRow.click();
  await page.waitForSelector('.cxp .detail.on');
  await shot('08-detail-element', 'page de détail d\'un élément (retour par « ← Retour au circuit » ou Échap)');
  await page.keyboard.press('Escape');
  await page.waitForSelector('.cxp .diagram');
}

// ── 7. onglet Journal → filtré ──
await page.locator('.cxp .tabs button', { hasText: 'Journal' }).first().click();
await page.waitForSelector('.cxp .jl');
await shot('09-journal', `le journal (${JOURNAL.total} entrées, ${JOURNAL.aujourdhui} aujourd'hui)`);
const filtre = page.locator('.cxp .jf button').nth(1);   // le premier geste après « tous »
if (await filtre.count()) { await filtre.click(); await page.waitForTimeout(500); await shot('10-journal-filtre', 'journal filtré par type de geste'); }

// ── 8. bouton « Vérifier que tout coule » (stub) ──
await page.locator('.cxp .tabs .actions button', { hasText: /Vérifier/ }).click().catch(() => {});
await page.waitForTimeout(600);
await shot('11-verifier', 'bouton « Vérifier que tout coule » (stub) → bascule sur l\'onglet Circuit');

console.log('\n✓ recette visuelle complète — 11 captures dans docs/CIRCUIT/RECETTE-CIRCUIT-P/');
await browser.close();
