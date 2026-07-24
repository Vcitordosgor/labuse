// M14 LOT F — captures de preuve (F1 verdicts sans « v2 », F2 sans « + Chercher plus »)
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://127.0.0.1:8043/socle/').replace(/\/?$/, '/');
const OUT = new URL('.', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 940 } });
page.setDefaultTimeout(20000);

async function shot(name) {
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log('  shot', name);
}

// ── F1 : verdicts sans « v2 » (cartes + légende + panneau filtre + entonnoir) ──
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' });
await page.waitForTimeout(2500);
// ouvre le panneau « + Filtre » (chips de verdict) si présent
try {
  const filtre = page.getByText('+ Filtre', { exact: false }).first();
  if (await filtre.count()) { await filtre.click(); await page.waitForTimeout(600); }
} catch (e) { console.log('  filtre?', String(e).slice(0, 80)); }
// ouvre l'entonnoir « pourquoi ? »
try {
  const pourquoi = page.locator('[data-entonnoir-btn]').first();
  if (await pourquoi.count()) { await pourquoi.click(); await page.waitForTimeout(600); }
} catch (e) { console.log('  entonnoir?', String(e).slice(0, 80)); }
await shot('f1_verdicts_sans_v2');

// ── F2 : ouvrir un projet (kanban) — plus de « + Chercher plus », phrase à la place ──
await page.goto(BASE, { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);
try {
  // aller à la vue Projets via le store (deep-link), fallback clic nav
  await page.evaluate(() => {
    const s = (window).__labuseStore || null;
    // pas d'API store exposée : on clique le lien nav
  });
} catch {}
// navigation par clic
try {
  const navProjets = page.getByRole('button', { name: /projets/i }).first();
  if (await navProjets.count()) { await navProjets.click(); await page.waitForTimeout(1200); }
  else {
    const link = page.getByText('Projets', { exact: false }).first();
    if (await link.count()) { await link.click(); await page.waitForTimeout(1200); }
  }
} catch (e) { console.log('  nav projets?', String(e).slice(0, 80)); }
// ouvrir un projet
try {
  const projet = page.getByText(/Projet (Beta|Alpha)/).first();
  if (await projet.count()) { await projet.click(); await page.waitForTimeout(1800); }
} catch (e) { console.log('  open projet?', String(e).slice(0, 80)); }
await page.waitForTimeout(1200);
await shot('f2_sans_chercher_plus');

await browser.close();
console.log('done');
