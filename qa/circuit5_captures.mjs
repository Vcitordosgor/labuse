// =============================================================================
// CIRCUIT-5 lot 6.2 — RECETTE VISUELLE : le Résumé reçoit les lignes des verrous, le détail
// du repère « 68 » montre la carte table → réservoir. Même harnais que CIRCUIT-P
// (frontend/circuit-harness.html, fixtures RÉELLES capturées de la base — zéro base touchée).
// Avant/après : la fixture CIRCUIT-P (page d'avant) vs la fixture CIRCUIT-5 (page d'après),
// plus une variante « verrou cassé » (composée par le VRAI composer, pas bricolée à la main).
// Usage : BASE=http://127.0.0.1:5175 node qa/circuit5_captures.mjs
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, readFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:5175').replace(/\/$/, '');
const OUT = new URL('../docs/CIRCUIT/RECETTE-CIRCUIT-5', import.meta.url).pathname;
const FIX5 = new URL('./fixtures/circuit5', import.meta.url).pathname;
const FIXP = new URL('./fixtures/circuit_p', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const fx = (d, n) => JSON.parse(readFileSync(`${d}/${n}.json`, 'utf8'));
const AVANT = fx(FIXP, 'circuit'), APRES = fx(FIX5, 'circuit'), CASSE = fx(FIX5, 'circuit-casse');
const COMPTEUR = fx(FIX5, 'compteur'), JOURNAL = fx(FIXP, 'journal');

const browser = await chromium.launch({ executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);
page.on('pageerror', (e) => console.log('  ⚠ PAGEERROR', String(e).slice(0, 200)));

let CIRCUIT = AVANT;
await page.route((url) => new URL(url).pathname.startsWith('/admin/'), async (route) => {
  const url = route.request().url(), m = route.request().method();
  const json = (o) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(o) });
  if (m === 'GET') {
    if (/\/admin\/circuit\/journal/.test(url)) return json(JOURNAL);
    if (/\/admin\/circuit\/compteur/.test(url)) return json(COMPTEUR);
    if (/\/admin\/circuit(\?|$)/.test(url)) return json(CIRCUIT);
  }
  return json({ ok: true });
});

const shot = async (name, note) => {
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log(`  📸 ${name} — ${note}`);
};

// 1 — AVANT (fixture CIRCUIT-P : pas de lignes verrous)
await page.goto(`${BASE}/socle/circuit-harness.html`);
await page.waitForSelector('.cxp .res');
await shot('01-resume-avant', 'le Résumé d\'avant CIRCUIT-5 (aucune ligne verrous/orphelines)');

// 2 — APRÈS (fixture réelle du 06/09 : « tables orphelines à purger » + « réservoirs sans lecteur »)
CIRCUIT = APRES;
await page.reload();
await page.waitForSelector('.cxp .res');
await shot('02-resume-apres', 'les lignes « à décider » : 32 orphelines, réservoirs sans lecteur');

// 3 — VERROU CASSÉ (variante composée par le vrai composer : la ligne ROUGE)
CIRCUIT = CASSE;
await page.reload();
await page.waitForSelector('.cxp .res');
await shot('03-resume-verrou-casse', 'la ligne rouge « verrous cassés : V3b, V4b »');

// 4 — LE DÉTAIL DU REPÈRE « 68 » : la carte table → réservoir
CIRCUIT = APRES;
await page.reload();
await page.waitForSelector('.cxp .res');
await page.click('.kpi.lien');
await page.waitForSelector('.detail.on');
await page.getByText('La carte : chaque réservoir, ses tables').scrollIntoViewIfNeeded();
await shot('04-compteur-carte', 'le détail du repère 68 : chaque réservoir, ses tables, son millésime');

await browser.close();
console.log('✓ recette CIRCUIT-5 terminée →', OUT);
