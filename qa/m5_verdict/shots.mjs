// Correctif M5 verdict d'en-tête — captures avant/après. Usage : node qa/m5_verdict/shots.mjs avant|apres
// Preuves → audit_shots/m5_verdict/<phase>_<nom>.png — parcelle témoin 97410000AS1425
// (matrice legacy « écartée » Q 44 · Brûlante v2 rang 16).
import { mkdirSync } from 'node:fs';

const pw = await import('../../frontend/node_modules/playwright/index.mjs');
const { chromium } = pw;

const PHASE = process.argv[2] === 'apres' ? 'apres' : 'avant';
const BASE = process.env.BASE || 'http://127.0.0.1:8000/socle/';
const IDU = '97410000AS1425';
const SHOTS = new URL('../../audit_shots/m5_verdict/', import.meta.url).pathname;
mkdirSync(SHOTS, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const p = await ctx.newPage();
const shot = (nom) => p.screenshot({ path: `${SHOTS}${PHASE}_${nom}.png`, timeout: 8000 });
const step = async (nom, fn) => {
  try { await fn(); console.log(`✓ ${nom}`); } catch (e) { console.log(`✗ ${nom}: ${String(e).slice(0, 200)}`); }
};

await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 30000 });
await p.waitForFunction(() => window.__labuse, null, { timeout: 25000 });
await p.waitForTimeout(2000);

// 1 — fiche de la parcelle témoin : bannière + badge d'en-tête vs bloc v2
await step('fiche', async () => {
  await p.evaluate((idu) => window.__labuse.select(idu), IDU);
  await p.waitForTimeout(2500);
  await shot('1_fiche');
});

// 2 — liste (verdict allumé, écartées opt-in pour voir la parcelle témoin dans la liste)
await step('liste', async () => {
  await p.evaluate(() => window.__labuse.select(null));
  await p.evaluate(() => window.__labuse.setVerdict(true));
  await p.waitForTimeout(1200);
  await shot('2_liste');
});

await ctx.close();
await browser.close();
