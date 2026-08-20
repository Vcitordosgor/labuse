// M130 · Phase 1 — captures de la queue M129-D : l'état SERVI (après refonte) des écrans touchés.
// carte + compteur (vivier 285 781) · panneau Filtre (les 3 facettes « Le bien ») · fiche parcelle
// (gloses, motifs FR, nom du score « Probabilité de vente sous 1 an ») · parcours projet · kanban
// avec le rejeu qui DIT « entrée par refonte cascade ».
// Usage : BASE=http://localhost:5173/ node qa/m130/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 1024 } });
page.setDefaultTimeout(30000);
const shots = [];
async function shot(n, note) { await page.screenshot({ path: `${OUT}/${n}.png` }); shots.push(`${n} — ${note}`); console.log(`📸 ${n} — ${note}`); }
const soft = async (fn, what) => { try { await fn(); } catch (e) { console.log(`⚠ ${what}: ${String(e).slice(0, 120)}`); } };

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);

// 01 · carte + compteur (accueil : la carte servie + le compteur du vivier)
await shot('01-carte-accueil', 'carte + accueil (vivier servi)');

// 02 · panneau Filtre — ouvrir le tiroir, montrer les 3 facettes « Le bien »
await soft(async () => {
  await page.click('[data-filtres-toggle]');
  await page.waitForSelector('[data-filtres-drawer]');
  await page.waitForTimeout(600);
}, 'ouverture tiroir filtres');
await shot('02-filtre-panneau', 'panneau Filtre ouvert (compteur SQL-exact)');

// 02b · faire défiler jusqu'au groupe « Le bien » (droits résiduels + propriétaire public)
await soft(async () => {
  const chip = page.locator('text=On peut encore construire').first();
  await chip.scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
}, 'scroll groupe Le bien');
await shot('02b-facettes-le-bien', 'facettes « Le bien » : droits résiduels (encore/maximum) + propriétaire public');

// 02c · activer les facettes → compteur vivant réagit
await soft(async () => {
  await page.click('text=On peut encore construire');
  await page.waitForTimeout(800);
}, 'activer facette « encore construire »');
await shot('02c-facette-active-compteur', 'facette « On peut encore construire » active — compteur vivant');

// 03 · fiche parcelle — recherche par IDU (gloses, motifs FR, nom du score)
await soft(async () => {
  await page.click('[data-filtres-toggle]').catch(() => {}); // referme le tiroir si ouvert
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(400);
  // ouvrir la fiche : cliquer une parcelle du vivier sur la carte (centre) sinon recherche
  await page.mouse.click(880, 512);
  await page.waitForTimeout(1500);
}, 'ouverture fiche par clic carte');
await shot('03-fiche-parcelle', 'fiche parcelle (gloses · motifs FR · « Probabilité de vente sous 1 an »)');

// 04 · parcours projet — cadrage (les facettes réutilisées + compteur vivant du vivier)
await soft(async () => {
  await page.click('[title="Projets"]').catch(async () => { await page.click('text=Projets'); });
  await page.waitForSelector('[data-projets-liste], [data-projets-vide]');
  await page.waitForTimeout(500);
}, 'aller à Projets');
await shot('04-projets-liste', 'liste des projets (cadrage figé)');

await soft(async () => {
  await page.click('[data-projet-nouveau], [data-projet-nouveau-vide]');
  await page.waitForSelector('[data-parcours-projet]');
  await page.waitForTimeout(500);
}, 'ouvrir parcours projet');
await shot('05-parcours-projet', 'parcours projet — identité → cadrage');

// 06 · kanban avec REJEU → « entrée par refonte cascade »
await soft(async () => {
  await page.keyboard.press('Escape').catch(() => {});
  await page.waitForTimeout(400);
  // ouvrir le projet 24 (démo Saint-Paul) via la liste
  await page.click('[title="Projets"]').catch(() => {});
  await page.waitForTimeout(400);
  const card = page.locator('text=Démo — 40 logements').first();
  await card.click();
  await page.waitForSelector('[data-projet-kanban]');
  await page.waitForTimeout(800);
}, 'ouvrir kanban projet 24');
await shot('06-kanban', 'kanban projet (cadrage du JJ/MM)');

await soft(async () => {
  await page.click('text=Rejouer');
  await page.waitForTimeout(2500);      // le run + le diff
}, 'clic Rejouer');
await shot('07-kanban-rejeu-refonte', 'rejeu : « entrée(s) par refonte cascade — nouveau vivier »');

console.log('\n── captures ──');
shots.forEach((s) => console.log('  ' + s));
console.log(`\n→ ${OUT}`);
await browser.close();
