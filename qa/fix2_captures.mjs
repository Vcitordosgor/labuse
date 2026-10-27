// DONNEES-ETAT-FIX-2 — captures du Tableau de bord (cartes Lot A/B/C), via le harness circuit (vite dev)
// nourri par la fixture RÉELLE capturée du backend (/admin/circuit). Chrome système. Zéro base touchée.
// Usage : BASE=http://127.0.0.1:6080 node qa/fix2_captures.mjs
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, readFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:6080').replace(/\/$/, '');
const OUT = new URL('../captures/donnees-etat-fix2', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const FIX = process.env.FIXTURE || 'fixtures/_fix2_circuit.json';
const TAG = process.env.TAG || '';   // '' = après ; 'avant' = origine (cartes Lot A/B/C absentes)
const CIRCUIT = JSON.parse(readFileSync(new URL(`./${FIX}`, import.meta.url).pathname, 'utf8'));

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
page.setDefaultTimeout(20000);
page.on('pageerror', (e) => console.log('  ⚠ PAGEERROR', String(e).slice(0, 160)));

await page.route((url) => new URL(url).pathname.startsWith('/admin/'), async (route) => {
  const url = route.request().url();
  const json = (o) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
  if (/\/admin\/circuit(\?|$)/.test(url)) return json(CIRCUIT);
  if (/\/admin\/circuit\/journal/.test(url)) return json({ items: [] });
  if (/\/admin\/circuit\/taches/.test(url)) return json({ verifier: null, agents: null, verrous: null, sonde: null });
  if (/\/admin\/cockpit\/etat-prod/.test(url)) return json({ joignable: false });
  return json({ ok: true });
});

const shot = async (name, note) => {
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log(`  📸 ${name} — ${note}`);
};

await page.goto(`${BASE}/socle/circuit-harness.html`);
await page.waitForSelector('.ck-card');
if (TAG === 'avant') {
  await shot('00-tableau-AVANT', 'origine : ni copie hors-site, ni restauration, et vérité-sources INVISIBLE');
  await browser.close();
  console.log('✓ capture AVANT écrite'); process.exit(0);
}
await shot('01-tableau-de-bord', 'les cartes : copie hors-site (Lot B), restauration vérifiée (Lot A), vérité-sources (Lot C)');

// Lot C — « Voir le détail » de la carte vérité-sources → les 3 écarts lisibles
try {
  const carte = page.locator('.ck-card', { hasText: 'valeurs servies divergent' });
  await carte.getByRole('button', { name: /Voir le détail/i }).click();
  await page.waitForTimeout(500);
  await shot('02-verite-sources-detail', 'les 3 écarts parcelle ↔ source officielle (GPU/Géorisques/DVF)');
} catch (e) { console.log('  (détail non capturé :', String(e).slice(0, 120), ')'); }

await browser.close();
console.log('✓ captures écrites dans', OUT);
