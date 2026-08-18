// M114 · Phase 4 — captures de recette de la page Projets refondue : liste (deux intensités),
// parcours ouvert (une étape, seul à l'écran), onglet Archivés, « VOIR LES N AUTRES » déplié, état
// vide (via interception /projets → []). Usage : BASE=http://localhost:5173/ node qa/m114/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });
page.setDefaultTimeout(30000);
async function shot(n, note) { await page.screenshot({ path: `${OUT}/${n}.png`, fullPage: false }); console.log(`📸 ${n} — ${note}`); }
async function safe(n, note, fn) { try { await fn(); await shot(n, note); } catch (e) { console.log(`⚠️  ${n} — SAUTÉ (${String(e).slice(0, 90)})`); } }

async function allerProjets() {
  await page.click('[data-rail="projets"], text=Projets').catch(async () => { await page.click('text=Projets'); });
  await page.waitForSelector('[data-projets-liste], [data-projets-vide]');
}

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await allerProjets();

// 1 · la liste — deux intensités
await safe('01-liste', 'liste : bandes mint (à trier) vs grises (à jour), vignettes 64/52, commune mono', async () => {
  await page.waitForSelector('[data-projet-row]');
});

// 2 · VOIR LES N AUTRES déplié
await safe('02-voir-plus', '« VOIR LES N AUTRES » déplié', async () => {
  await page.click('[data-projets-plus]', { timeout: 5000 });
  await page.waitForTimeout(300);
});

// 3 · onglet Archivés
await safe('03-archives', 'onglet Archivés', async () => {
  await page.click('[data-tab-archives]');
  await page.waitForTimeout(300);
});
await page.click('[data-tab-actifs]').catch(() => {});

// 4 · parcours ouvert — SEUL à l'écran (pas de liste dessous)
await safe('04-parcours-nom', 'parcours ouvert (étape 1 · NOM), seul à l’écran', async () => {
  await page.click('[data-projet-nouveau]');
  await page.waitForSelector('[data-parcours-projet]');
  await page.waitForTimeout(200);
});

// 5 · parcours étape PROGRAMME (la vitrine de la maquette : 3/5, choix + champ)
await safe('05-parcours-programme', 'parcours étape 3/5 · PROGRAMME (question 24px, progression, trail)', async () => {
  await page.fill('[data-projet-nom]', 'Résidence Barsac');
  await page.click('[data-projet-suivant]');                  // → COMMUNE
  await page.selectOption('[data-projet-commune]', { label: 'Sainte-Marie' }).catch(async () => {
    await page.selectOption('[data-projet-commune]', { index: 1 });
  });
  await page.click('[data-projet-suivant]');                  // → PROGRAMME
  await page.fill('[data-projet-programme]', '13');
  await page.waitForTimeout(200);
});

// 6 · état vide (interception /projets → [])
await safe('06-etat-vide', 'état vide : cadre pointillé, invite à créer', async () => {
  await page.route('**/projets', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await allerProjets();
  await page.waitForSelector('[data-projets-vide]');
});

await browser.close();
console.log(`\n✅ captures dans ${OUT}`);
