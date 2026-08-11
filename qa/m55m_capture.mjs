// =============================================================================
// M55-M — captures Playwright (panneau : listing, bandeau critères, « Changer les filtres »)
// Usage : BASE=http://localhost:5173/socle/ node qa/m55m_capture.mjs [--out reports/m55-m/captures]
// Le dev vite (HMR) sert le code courant → capture l'état RÉEL des 3 points.
// =============================================================================
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const outIdx = process.argv.indexOf('--out');
const OUT = outIdx > -1 ? process.argv[outIdx + 1] : 'reports/m55-m/captures';
mkdirSync(OUT, { recursive: true });

const results = [];
const browser = await chromium.launch({ channel: 'chrome' });

async function grab(name, hash, note, { width = 1440, height = 900, prep } = {}) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.setDefaultTimeout(20000);
  try {
    await page.goto(BASE + '#' + hash, { waitUntil: 'domcontentloaded' });
    // le bandeau (Retour) prouve verdict=true ; sinon on attend au moins l'aside
    await page.waitForSelector('aside', { timeout: 20000 });
    await page.waitForTimeout(1500);
    if (prep) await prep(page);
    await page.waitForTimeout(700);
    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
    // relève le texte du bandeau critères (title = récap complet) s'il existe
    const crit = await page.$('[data-analyse-criteres]');
    const critTxt = crit ? await crit.textContent() : null;
    const critTitle = crit ? await crit.getAttribute('title') : null;
    results.push({ name, note, ok: true, critTxt, critTitle });
    console.log(`  📸 ${name} — ${note}${critTxt ? ` | affiché="${critTxt}" title="${critTitle}"` : ''}`);
  } catch (e) {
    results.push({ name, note, ok: false, err: String(e).slice(0, 140) });
    console.log(`  ⚠ ${name} — ${note} : ${String(e).slice(0, 140)}`);
  } finally {
    await page.close();
  }
}

// ── POINT 3 · bandeau avec 1, 4, et un cas long (troncature) ────────────────
await grab('p3-bandeau-1critere', 'f=1&al=1&es=nu', 'bandeau — 1 critère (terrain nu)');
await grab('p3-bandeau-4criteres', 'f=1&al=1&cs=Cilaos&smin=500&zf=U&es=nu',
  'bandeau — 4 critères (Cilaos, >500 m², zone U, terrain nu)');
await grab('p3-bandeau-long-340', 'f=1&al=1&cs=Saint-Paul,Saint-Denis&smin=300&smax=5000&zf=U,AU&es=nu&sv=procedure,permis_actif,friche,defisc',
  'bandeau — cas LONG, panneau 340px (troncature + title complet)');
await grab('p3-bandeau-long-240', 'f=1&al=1&cs=Saint-Paul,Saint-Denis&smin=300&smax=5000&zf=U,AU&es=nu&sv=procedure,permis_actif,friche,defisc',
  'bandeau — cas LONG, panneau 240px étroit (troncature)', { width: 980, height: 900 });

// ── POINT 1 · automate listing ──────────────────────────────────────────────
// état d'arrivée = listing (deux sections rétractées), listing sous le bandeau
await grab('p1-listing', 'f=1&al=1&cs=Cilaos&es=nu', 'listing — deux sections rétractées, listing plein');
// rouvrir Filtres à la main (montre aussi le point 2 : « Changer les filtres » / « Désactiver »)
await grab('p1-reouvre-filtres', 'f=1&al=1&cs=Cilaos&es=nu',
  'listing → rouvre Filtres (post-analyse : Changer les filtres / Désactiver)',
  { prep: async (p) => { await p.click('[data-filtres-toggle]'); } });
// puis rouvrir Couches (exclusivité : Filtres se referme)
await grab('p1-reouvre-couches', 'f=1&al=1&cs=Cilaos&es=nu',
  'listing → rouvre Couches (Filtres se referme, exclusivité)',
  { prep: async (p) => { await p.click('[data-couches-toggle]'); } });
// refermer la section rouverte → retour au listing
await grab('p1-referme-vers-listing', 'f=1&al=1&cs=Cilaos&es=nu',
  'Couches rouverte puis refermée → place rendue au listing',
  { prep: async (p) => { await p.click('[data-couches-toggle]'); await p.waitForTimeout(300); await p.click('[data-couches-toggle]'); } });
// Retour → Filtres ouvert éditable
await grab('p1-retour-filtres', 'f=1&al=1&cs=Cilaos&es=nu',
  '« Retour » → Filtres ouvert et éditable (formulaire complet)',
  { prep: async (p) => { await p.click('[data-verdict-off]'); } });

// ── POINT 2 · « Changer les filtres » défige → tri factuel éditable ─────────
await grab('p2-apres-changer-filtres', 'f=1&al=1&cs=Cilaos&es=nu',
  '« Changer les filtres » → formulaire éditable, listing reste (tri factuel)',
  { prep: async (p) => {
      await p.click('[data-filtres-toggle]'); await p.waitForTimeout(400);
      await p.click('[data-changer-filtres]');
    } });

await browser.close();
const ok = results.filter((r) => r.ok).length;
console.log(`\n${ok}/${results.length} captures → ${OUT}`);
console.log(JSON.stringify(results, null, 1));
process.exit(ok >= 8 ? 0 : 1);
