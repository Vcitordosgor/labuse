// M120 · Phase 5 — captures de recette du flux Projet complet : identité (nom · périmètre · budget ·
// type · livraison) → cadrage (facettes réutilisées + compteur vivant) → run figé → shortlist →
// tri (carte unifiée, 2 densités) → fiche. Usage : BASE=http://localhost:5173/ node qa/m120/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1280, height: 1040 } });
page.setDefaultTimeout(30000);
async function shot(n, note) { await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`); }
async function next() { await page.click('[data-projet-suivant]'); await page.waitForTimeout(250); }

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.click('[data-rail="projets"]').catch(async () => { await page.click('text=Projets'); });
await page.waitForSelector('[data-projets-liste], [data-projets-vide]');
await page.click('[data-projet-nouveau], [data-projet-nouveau-vide]');
await page.waitForSelector('[data-parcours-projet]');

// 01 · identité — nom
await page.fill('[data-projet-nom]', 'Recette Saint-Leu');
await shot('01-identite-nom', 'étape 1/7 · nom');
await next();

// 02 · identité — périmètre (communes précises)
await page.click('[data-projet-communes-mode]').catch(() => {});
await page.click('[data-projet-communes] >> text=Saint-Leu').catch(() => {});
await shot('02-identite-perimetre', 'étape 2/7 · périmètre (commune)');
await next();

// 03 · identité — budget (INDICATIF, l'écran le dit)
await page.fill('[data-projet-budget]', '720000');
await shot('03-identite-budget-indicatif', 'étape 3/7 · budget « indicatif — sans effet sur la sélection »');
await next();

// 04 · identité — type (INFORMATIF, servi par référentiel)
await page.click('[data-projet-type] >> text=Logement social').catch(() => {});
await shot('04-identite-type-informatif', 'étape 4/7 · type « le moteur ne distingue pas par type »');
await next();

// 05 · identité — livraison (INDICATIF)
await page.fill('[data-projet-livraison]', '2027-06').catch(() => {});
await shot('05-identite-livraison', 'étape 5/7 · date de livraison (indicatif)');
await next();

// 06 · CADRAGE — les facettes de la carte réutilisées + compteur vivant
await page.fill('[data-cadrage-facettes] input', '800').catch(() => {});
await page.waitForTimeout(900);   // compteur vivant (debounce 400ms + /filtre)
await shot('06-cadrage-facettes', 'étape 6/7 · cadrage (facettes carte réutilisées + compteur vivant)');
await next();

// 07 · récap
await page.waitForSelector('[data-projet-recap]');
await shot('07-recap', 'étape 7/7 · récapitulatif (facettes vs indicatifs)');

// 08 · créer = le run part une fois → shortlist figée
await page.click('[data-projet-creer]');
await page.waitForSelector('[data-parcours-projet-cree]');
await shot('08-shortlist-figee', 'projet créé — shortlist figée + datée');

// 09 · tri — la carte unifiée, deux densités
await page.click('[data-projet-voir]');
await page.waitForSelector('[data-projet-kanban]');
await page.waitForSelector('[data-tri-card]', { timeout: 15000 }).catch(() => {});
await page.waitForTimeout(500);
await shot('09-tri-carte-unifiee', 'tri : carte unifiée (À trier dense · Retenues/Écartées allégées) + « cadrage du … »');

// 10 · clic carte → fiche
await page.click('[data-tri-card]').catch(() => {});
await page.waitForTimeout(1200);
await shot('10-fiche', 'clic sur une parcelle → la fiche s’ouvre');

console.log(`\n✅ captures dans ${OUT}`);
await browser.close();
