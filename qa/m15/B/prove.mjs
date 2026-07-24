// M15 LOT B — preuve des plafonds levés (« voir plus ») sur l'app en marche (:8060/socle/).
// Outil 14 Radar permis (M03) · Outil 15 Promesses mortes (M04) · Outil 4 Foncier fantôme (M07).
import { chromium } from '../../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';
const BASE = process.env.BASE || 'http://127.0.0.1:8060/socle/';
const OUT = new URL('.', import.meta.url).pathname; mkdirSync(OUT, { recursive: true });
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.setDefaultTimeout(25000);
await p.goto(BASE, { waitUntil: 'networkidle' });
await p.waitForTimeout(1500);

async function toMenu() {
  const retour = p.locator('[data-module-retour]');
  if (await retour.count()) { await retour.first().click(); await p.waitForTimeout(500); return; }
  await p.getByRole('button', { name: 'Outils', exact: true }).click();
  await p.waitForTimeout(500);
}
async function openTool(label) {
  await toMenu();
  await p.getByText(label, { exact: true }).first().click();
  // attendre la fin du chargement : bouton « voir plus » présent OU au moins une ligne rendue
  await p.waitForSelector('[data-more], [data-permis-row], [data-idu-row]', { timeout: 20000 }).catch(() => {});
  await p.waitForTimeout(1200);
}
async function countRows(sel) { return await p.locator(sel).count(); }
async function moreLabel() {
  const btn = p.locator('[data-more]');
  if (await btn.count() === 0) return null;
  return (await btn.first().innerText()).replace(/\s+/g, ' ').trim();
}

// ───────── Outil 14 — Radar permis ─────────
await openTool('Radar permis');
const sansLoc = await p.locator('[data-permis-sansloc]').count()
  ? (await p.locator('[data-permis-sansloc]').first().innerText()).trim() : '(absent)';
const permisRows0 = await countRows('[data-permis-row]');
const more14a = await moreLabel();
await p.screenshot({ path: `${OUT}/14a_permis_page0.png` });
console.log('14 — rows page0:', permisRows0, '| sans_loc mention:', sansLoc, '| voir-plus:', more14a);
// clic « voir plus »
if (more14a) { await p.locator('[data-more]').first().click(); await p.waitForTimeout(1500); }
const permisRows1 = await countRows('[data-permis-row]');
const more14b = await moreLabel();
await p.screenshot({ path: `${OUT}/14b_permis_voirplus.png` });
console.log('14 — rows after voir-plus:', permisRows1, '| voir-plus:', more14b);

// ───────── Outil 15 — Promesses mortes ─────────

await openTool('Promesses mortes');
// promesses rows = Row buttons ; on mesure via le compteur affiché + le bouton voir plus
const cnt15 = (await p.locator('p', { hasText: 'promesses mortes' }).first().innerText()).replace(/\s+/g, ' ');
const more15a = await moreLabel();
await p.screenshot({ path: `${OUT}/15a_promesses_page0.png` });
console.log('15 — compteur:', cnt15, '| voir-plus:', more15a);
if (more15a) { await p.locator('[data-more]').first().click(); await p.waitForTimeout(9000); }
const cnt15b = (await p.locator('p', { hasText: 'promesses mortes' }).first().innerText()).replace(/\s+/g, ' ');
const more15b = await moreLabel();
await p.screenshot({ path: `${OUT}/15b_promesses_voirplus.png` });
console.log('15 — compteur après voir-plus:', cnt15b, '| voir-plus:', more15b);

// ───────── Outil 4 — Foncier fantôme ─────────

await openTool('Foncier fantôme');
const cnt4 = (await p.locator('p', { hasText: 'parcelles gelées' }).first().innerText()).replace(/\s+/g, ' ');
const more4a = await moreLabel();
await p.screenshot({ path: `${OUT}/04a_fantome_page0.png` });
console.log('04 — compteur:', cnt4, '| voir-plus:', more4a);
if (more4a) { await p.locator('[data-more]').first().click(); await p.waitForTimeout(4000); }
const cnt4b = (await p.locator('p', { hasText: 'parcelles gelées' }).first().innerText()).replace(/\s+/g, ' ');
const more4b = await moreLabel();
await p.screenshot({ path: `${OUT}/04b_fantome_voirplus.png` });
console.log('04 — compteur après voir-plus:', cnt4b, '| voir-plus:', more4b);

console.log('done');
await b.close();
