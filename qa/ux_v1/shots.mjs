// UX V1 — captures avant/après. Usage : node qa/ux_v1/shots.mjs avant|apres
// Preuves → audit_shots/ux_v1/<phase>_<viewport>_<item>.png (+ console du boot 375 en JSON).
import { mkdirSync, writeFileSync } from 'node:fs';

const pw = await import('../../frontend/node_modules/playwright/index.mjs');
const { chromium } = pw;

const PHASE = process.argv[2] === 'apres' ? 'apres' : 'avant';
const BASE = process.env.BASE || 'http://127.0.0.1:8000/socle/';
const SHOTS = new URL('../../audit_shots/ux_v1/', import.meta.url).pathname;
mkdirSync(SHOTS, { recursive: true });

const browser = await chromium.launch();
const consoleLog = [];

async function page(viewport) {
  const ctx = await browser.newContext({ viewport });
  const p = await ctx.newPage();
  p.on('console', (m) => {
    if (m.type() === 'error' || m.type() === 'warning') consoleLog.push({ vp: viewport.width, type: m.type(), text: m.text().slice(0, 300) });
  });
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await p.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
  await p.waitForTimeout(1500);
  return { ctx, p };
}
const shot = (p, nom) => p.screenshot({ path: `${SHOTS}${PHASE}_${nom}.png`, timeout: 8000 });
const step = async (nom, fn) => {
  try { await fn(); console.log(`✓ ${nom}`); } catch (e) { console.log(`✗ ${nom}: ${String(e).slice(0, 200)}`); }
};

// ── 375 : boot cartes (1.1) + console MapLibre (1.3) ──
await step('375 boot', async () => {
  const { ctx, p } = await page({ width: 375, height: 812 });
  await p.waitForTimeout(2500);
  await shot(p, '375_1_1_boot');
  await ctx.close();
});

// ── 375 : builder segments (1.2) + galerie ──
await step('375 segments', async () => {
  const { ctx, p } = await page({ width: 375, height: 812 });
  await p.evaluate(() => window.__labuse.setView('segments'));
  await p.waitForTimeout(1800);
  await shot(p, '375_1_2_galerie');
  await p.locator('[data-seg-preset-open]').first().click();
  await p.waitForTimeout(2500);
  await shot(p, '375_1_2_builder');
  await ctx.close();
});

// ── 1440 : restitution NL (2.1) — recherche simple réelle ──
await step('1440 restitution NL', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => window.__labuse.setView('ia'));
  await p.waitForTimeout(800);
  const input = p.locator('[data-porte-recherche] input');
  await input.fill('les chaudes de Saint-Pierre');
  await input.press('Enter');
  await p.locator('[data-ia-restitution]').waitFor({ timeout: 30000 });
  await p.waitForTimeout(1500);
  await shot(p, '1440_2_1_restitution');
  await ctx.close();
});

// ── 1440 : restitution stub (2.1/2.2) — /ia/search intercepté = réponse stub réaliste ──
await step('1440 restitution stub', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.route('**/ia/search', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ stub: true,
      filters: { statuts: [], scoreMin: null, surfaceMin: null, surfaceMax: null, sdpMin: null, evenement: false, vueMer: false, flags: [], commune: 'Le Tampon' },
      explanation: 'Filtres appliqués : commune Le Tampon. (repli stub)' }),
  }));
  await p.evaluate(() => window.__labuse.setView('ia'));
  await p.waitForTimeout(800);
  const input = p.locator('[data-porte-recherche] input');
  await input.fill('maisons avec un DPE F ou G au Tampon');
  await input.press('Enter');
  await p.locator('[data-ia-restitution]').waitFor({ timeout: 30000 });
  await p.waitForTimeout(1500);
  await shot(p, '1440_2_1_restitution_stub');
  await ctx.close();
});

// ── 1440 : recherche à 0 résultat (2.3) — Cilaos n'a aucune chaude ──
await step('1440 zero resultat', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.route('**/ia/search', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ stub: false,
      filters: { statuts: ['chaude'], scoreMin: null, surfaceMin: 5000, surfaceMax: null, sdpMin: null, evenement: false, vueMer: false, flags: [], commune: 'Cilaos' },
      explanation: 'Filtres proposés par l\'IA (validés par schéma).' }),
  }));
  await p.evaluate(() => window.__labuse.setView('ia'));
  await p.waitForTimeout(800);
  const input = p.locator('[data-porte-recherche] input');
  await input.fill('les chaudes de Cilaos de plus de 5000 m²');
  await input.press('Enter');
  await p.locator('[data-ia-restitution]').waitFor({ timeout: 30000 });
  await p.waitForTimeout(1800);
  await shot(p, '1440_2_3_zero');
  await ctx.close();
});

// ── 1440 : page Sources (2.4) ──
await step('1440 sources', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => window.__labuse.setView('sources'));
  await p.waitForTimeout(1800);
  await shot(p, '1440_2_4_sources');
  await ctx.close();
});

// ── 1440 : fiche en erreur réseau (3.1) ──
await step('1440 fiche erreur', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.route('**/parcels/97411000*', (route) => route.abort('connectionrefused'));
  await p.evaluate(() => window.__labuse.select('97411000BH0670'));
  await p.waitForTimeout(12000);   // react-query épuise ses retries
  await shot(p, '1440_3_1_fiche_erreur');
  await ctx.close();
});

// ── 1440 : liste vide — Cilaos, verdict allumé (3.2) ──
await step('1440 liste vide Cilaos', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => { window.__labuse.setCommune('Cilaos'); window.__labuse.setVerdict(true); });
  await p.waitForTimeout(4000);
  await shot(p, '1440_3_2_liste_vide');
  await ctx.close();
});

// ── 1440 : galerie segments (3.4 note compteur + LOT 5 copy) ──
await step('1440 galerie', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => window.__labuse.setView('segments'));
  await p.waitForTimeout(1800);
  await shot(p, '1440_3_4_galerie');
  await ctx.close();
});

// ── 1440 : range du builder à -50 (4.1) ──
await step('1440 range -50', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => window.__labuse.setView('segments'));
  await p.waitForTimeout(1500);
  await p.locator('[data-seg-preset-open]').first().click();
  await p.waitForTimeout(2000);
  const min = p.locator('[data-seg-filtre] input[placeholder="min"]').first();
  await min.fill('-50');
  await p.waitForTimeout(1200);
  await shot(p, '1440_4_1_range_negatif');
  await ctx.close();
});

// ── 1440 : parcours clavier (4.2) — 4 tabulations depuis le boot ──
await step('1440 focus clavier', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  for (let i = 0; i < 4; i++) { await p.keyboard.press('Tab'); await p.waitForTimeout(150); }
  await shot(p, '1440_4_2_focus_rail');
  await ctx.close();
});

// ── 1440 : fiche synthèse (4.3 tooltips Q/A/V) ──
await step('1440 fiche synthese', async () => {
  const { ctx, p } = await page({ width: 1440, height: 900 });
  await p.evaluate(() => window.__labuse.select('97411000BH0670'));
  await p.waitForTimeout(4000);
  await shot(p, '1440_4_3_fiche_scores');
  await ctx.close();
});

writeFileSync(`${SHOTS}${PHASE}_console.json`, JSON.stringify(consoleLog, null, 1));
console.log(`console: ${consoleLog.length} messages → ${PHASE}_console.json`);
await browser.close();
