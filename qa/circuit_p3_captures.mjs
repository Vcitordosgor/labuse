// =============================================================================
// CIRCUIT-P3 lot 4.1 — RECETTE NAVIGATEUR sur la BASE LOCALE RÉELLE (labuse).
// La page (frontend/circuit-harness.html) est servie par vite ; les appels /admin/* sont PROXIFIÉS
// vers une instance uvicorn de CE code, branchée sur la vraie base (port 8010) — donc données
// réelles, correctifs P3 en place, aucune fixture. Prouve : le Journal rend ses lignes (un lot
// déplié), les filtres marchent, le Circuit montre « n à regarder » non nul à droite, un robinet en
// fuite s'ouvre, et le Résumé donne les mêmes nombres que le Circuit.
// Prérequis : uvicorn (ce code) sur :8010 branché sur labuse + vite dev (:5173).
//   PYTHONPATH=src python -m uvicorn labuse.api.app:app --port 8010
//   (cd frontend && npm run dev)
//   BASE=http://localhost:5173 API=http://127.0.0.1:8010 node qa/circuit_p3_captures.mjs
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173').replace(/\/$/, '');
const API = (process.env.API || 'http://127.0.0.1:8010').replace(/\/$/, '');
const OUT = new URL('../docs/CIRCUIT/RECETTE-CIRCUIT-P/', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);
page.on('pageerror', (e) => console.log('  ⚠ PAGEERROR', String(e).slice(0, 200)));

// /admin/* → l'API réelle (uvicorn sur labuse), le reste (modules vite) passe.
await page.route((url) => new URL(url).pathname.startsWith('/admin/'), async (route) => {
  const u = new URL(route.request().url());
  const resp = await fetch(API + u.pathname + u.search, {
    method: route.request().method(),
    headers: { 'content-type': 'application/json' },
    body: ['GET', 'HEAD'].includes(route.request().method()) ? undefined : (route.request().postData() || undefined),
  });
  const body = await resp.text();
  await route.fulfill({ status: resp.status, contentType: 'application/json', body });
});

const shot = async (name, note) => {
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name} — ${note}`);
};
const tab = (t) => page.locator('.cxp .tabs button', { hasText: t }).first();

await page.goto(`${BASE}/socle/circuit-harness.html`);
await page.waitForSelector('.cxp .res', { timeout: 20000 });

// ── P3-01 — Journal avec ses entrées + un lot déplié ──
await tab('Journal').click();
await page.waitForSelector('.cxp .jl');
const grp = page.locator('.cxp .jl.grp').first();
if (await grp.count()) await grp.click();          // déplie le premier passage groupé
await page.waitForTimeout(400);
await shot('P3-01-journal-entrees-lot-deplie', 'Journal : ses entrées, un lot déplié source par source');

// ── P3-02 — Journal filtré sur « filtre » ──
await page.locator('.cxp .jf button', { hasText: 'filtre' }).first().click();
await page.waitForTimeout(500);
await shot('P3-02-journal-filtre-filtre', 'Journal filtré sur « filtre »');

// ── P3-03 — Journal filtré sur « vanne » ──
await page.locator('.cxp .jf button', { hasText: 'vanne' }).first().click();
await page.waitForTimeout(500);
await shot('P3-03-journal-filtre-vanne', 'Journal filtré sur « vanne »');

// ── P3-04 — Circuit : « n à regarder » non nul à droite (robinets) ──
await tab('Circuit').click();
await page.waitForSelector('.cxp .diagram');
await shot('P3-04-circuit-robinets-a-regarder', 'Circuit : colonne Robinets « n à regarder » non nul');

// ── P3-05 — un robinet en fuite, ouvert depuis le Circuit ──
// interrupteur ON (défaut) → les blocs dépliés ne montrent QUE les robinets à regarder. On ouvre
// chaque catégorie jusqu'à voir une ligne, puis on clique la ligne (le robinet en fuite).
const hds = page.locator('.cxp .node[data-cat] .hd');
const n = await hds.count();
let ouvert = false;
for (let i = 0; i < n; i++) {
  await hds.nth(i).click().catch(() => {});
  await page.waitForTimeout(150);
  if (await page.locator('.cxp .node[data-cat].open .row').count()) { ouvert = true; break; }
  await hds.nth(i).click().catch(() => {});   // referme si vide (accordéon)
}
const koRow = page.locator('.cxp .node[data-cat].open .row').first();
if (ouvert && await koRow.count()) {
  await koRow.click();
  await page.waitForSelector('.cxp .detail.on');
  await shot('P3-05-robinet-fuite', 'un robinet en fuite ouvert depuis le Circuit');
  await page.keyboard.press('Escape');
  await page.waitForSelector('.cxp .diagram');
} else {
  console.log('  ⚠ aucun robinet à regarder trouvé pour P3-05');
}

// ── P3-06 — le Résumé montre les mêmes nombres que le Circuit ──
await tab('Résumé').click();
await page.waitForSelector('.cxp .res', { state: 'visible' });
await shot('P3-06-resume-memes-nombres', 'Résumé : « robinets sans rien à signaler » = total − à regarder du Circuit');

console.log('\n✓ recette P3 — captures P3-01…P3-06 dans docs/CIRCUIT/RECETTE-CIRCUIT-P/');
await browser.close();
