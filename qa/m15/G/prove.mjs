// M15 LOT G — RG1 (héritage commune coupé) + 3 entrées (IDU / adresse / clic carte).
// #c=<commune> pose le filtre commune GLOBAL ; #m=<outil> ouvre l'outil directement.
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060/socle/';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(25000);
let navN=0;
const nav = (hash) => p.goto(`${BASE}?t=${++navN}${hash}`, { waitUntil: 'networkidle' });
const txt = async (sel) => (await p.locator(sel).first().innerText().catch(() => '—')).replace(/\s+/g, ' ').trim();

// ───────── M07 Foncier fantôme — RG1 : commune globale = Saint-Denis, l'outil NE l'hérite PAS ─────────
await nav('#c=Saint-Denis&m=fantome');
await p.waitForSelector('[data-more], [data-commune-scope]', { timeout: 20000 }).catch(() => {});
await p.waitForTimeout(1500);
const scopeVal0 = await p.locator('[data-commune-scope]').first().inputValue().catch(() => 'ABSENT');
const cnt07_island = await txt('p:has-text("parcelles gelées")');
await p.screenshot({ path: `${OUT}/07a_fantome_global-SD_outil-ile.png` });
console.log('07 RG1 — filtre global=Saint-Denis | scope outil (défaut):', JSON.stringify(scopeVal0 || 'Toute l\'île'), '| compteur:', cnt07_island, '(île=6261 attendu, PAS 744)');
// maintenant on choisit explicitement Saint-Denis DANS l'outil → le compte doit tomber
await p.locator('[data-commune-scope]').first().selectOption('Saint-Denis');
await p.waitForTimeout(1500);
const cnt07_sd = await txt('p:has-text("parcelles gelées")');
const more07 = await p.locator('[data-more]').count();
await p.screenshot({ path: `${OUT}/07b_fantome_scope-SD.png` });
console.log('07 scope explicite=Saint-Denis | compteur:', cnt07_sd, '(744 attendu) | voir-plus présent:', more07 > 0);

// ───────── M06 Mode bailleur — RG1 ─────────
await nav('#c=Saint-Denis&m=bailleur');
await p.waitForSelector('[data-commune-scope]', { timeout: 20000 }).catch(() => {});
await p.waitForTimeout(1500);
const scope06 = await p.locator('[data-commune-scope]').first().inputValue().catch(() => 'ABSENT');
const note06 = await txt('label:has([data-commune-scope])');
await p.screenshot({ path: `${OUT}/06_bailleur_scope.png` });
console.log('06 RG1 — filtre global=Saint-Denis | scope outil (défaut):', JSON.stringify(scope06 || 'Toute l\'île'), '| note:', note06);

// ───────── M09 Courriers — 3 entrées ─────────
await nav('#m=courriers');
await p.waitForTimeout(1500);
const hasIdu09 = await p.locator('[data-courrier-idu]').count();
const hasAddr09 = await p.getByPlaceholder('… ou une adresse').count();
const intro09 = await txt('p:has-text("3 entrées")');
await p.screenshot({ path: `${OUT}/09_courriers_3entrees.png` });
console.log('09 — IDU input:', hasIdu09 > 0, '| adresse input:', hasAddr09 > 0, '| intro:', intro09.slice(0, 70));

// ───────── M10 Due diligence — 3 entrées alimentent le lot ─────────
await nav('#m=duediligence');
await p.waitForTimeout(1500);
const hasQuick = await p.locator('[data-diligence-quick]').count();
const hasAddr10 = await p.getByPlaceholder('… ou une adresse').count();
await p.locator('[data-diligence-quick]').fill('97415000AC0253');
await p.locator('[data-diligence-add]').click();
await p.waitForTimeout(400);
await p.locator('[data-diligence-quick]').fill('AC0254');
await p.locator('[data-diligence-add]').click();
await p.waitForTimeout(400);
const textareaVal = await p.locator('textarea').first().inputValue();
await p.screenshot({ path: `${OUT}/10_duediligence_3entrees.png` });
console.log('10 — quick input:', hasQuick > 0, '| adresse input:', hasAddr10 > 0, '| textarea après 2 ajouts:', JSON.stringify(textareaVal.replace(/\n/g, '⏎')));

console.log('done');
await b.close();
