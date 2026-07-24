// M15 LOT C — C1 Faisabilité 2 modes (M22) + C2 Calculette foncière (nouvel outil).
// ?t=N force un rechargement complet ; #c=<commune> pose le filtre global, #m=<outil> ouvre l'outil.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060/socle/';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const IDU = '97415000CW0658';
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(25000);
let navN = 0;
const nav = (hash) => p.goto(`${BASE}?t=${++navN}${hash}`, { waitUntil: 'networkidle' });
const has = async (sel) => (await p.locator(sel).count()) > 0;

// ───────── C1 — Faisabilité, mode « Par critères » (RG1) ─────────
await nav('#c=Saint-Denis&m=programme');
await p.waitForSelector('[data-faisa-mode]', { timeout: 20000 }).catch(() => {});
await p.waitForTimeout(1200);
const modeCrit = await has('[data-faisa-mode="criteres"]');
const modePar = await has('[data-faisa-mode="parcelle"]');
const scope = await p.locator('[data-commune-scope]').first().inputValue().catch(() => 'ABSENT');
await p.screenshot({ path: `${OUT}/c1a_criteres_RG1.png` });
console.log('C1 — toggle: critères', modeCrit, '· parcelle', modePar, '| RG1 périmètre (défaut, global=SD):', JSON.stringify(scope || "Toute l'île"));

// ───────── C1 — bascule « Par parcelle » → faisabilité de la fiche portée ─────────
await p.locator('[data-faisa-mode="parcelle"]').click();
await p.waitForTimeout(600);
const pickerC1 = await has('[data-picker-idu]');
await p.locator('[data-picker-idu]').fill(IDU);
await p.locator('[data-picker-go]').click();
await p.waitForSelector('[data-faisa-parcelle]', { timeout: 20000 }).catch(() => {});
await p.waitForTimeout(1500);
const steps = await p.locator('[data-faisa-steps]').count();
const calcInside = await has('[data-calculette]');
const capText = (await p.locator('[data-faisa-parcelle]').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 90);
await p.screenshot({ path: `${OUT}/c1b_parparcelle_faisa.png` });
console.log('C1 parcelle — picker', pickerC1, '| steps rendus', steps > 0, '| calculette incluse', calcInside, '| tête:', capText);

// ───────── C2 — Calculette foncière (nouvel outil autonome) ─────────
await nav('#m=calculette-fonciere');
await p.waitForSelector('[data-picker-idu]', { timeout: 20000 }).catch(() => {});
await p.waitForTimeout(1000);
const pickerC2 = await has('[data-picker-idu]');
await p.locator('[data-picker-idu]').fill(IDU);
await p.locator('[data-picker-go]').click();
await p.waitForSelector('[data-calculette]', { timeout: 20000 }).catch(() => {});
await p.waitForTimeout(1500);
const calcResult = await has('[data-calc-resultat]');
const cf = (await p.locator('[data-calc-cf]').innerText().catch(() => '—')).trim();
const sourced = (await p.locator('[data-calculette]').innerText().catch(() => '')).includes('sourcé');
await p.screenshot({ path: `${OUT}/c2_calculette_fonciere.png` });
console.log('C2 — picker', pickerC2, '| résultat charge foncière', calcResult, '| CF centrale:', cf, '| bloc sourcé présent:', sourced);

console.log('done');
await b.close();
