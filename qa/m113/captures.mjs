// M113 · Phase 5 — captures de recette du Copilote guidé : chips de contexte, placeholder adapté,
// parcours projet guidé, réponses par gabarit (web court / données+récap M109), bouton Nouveau fil,
// carte PRÉCISION. Usage : BASE=http://localhost:5173/ node qa/m113/captures.mjs
// (vite dev + API :8000 sur le code M113 ; PNG sous qa/m113/captures/<stamp>/, jamais commités.)
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 940 } });
page.setDefaultTimeout(30000);

async function shot(name, note) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`📸 ${name} — ${note}`);
}
async function safe(name, note, fn) {
  try { await fn(); await shot(name, note); }
  catch (e) { console.log(`⚠️  ${name} — SAUTÉ (${String(e).slice(0, 80)})`); }
}

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.click('[data-rail="copilote"], button:has-text("IA")').catch(async () => { await page.click('text=IA'); });
await page.waitForSelector('[data-accueil-chips]');

// 1 · les chips « Que souhaitez-vous faire ? »
await shot('01-chips', 'accueil avec les 6 chips de contexte servis par le serveur');

// 2 · un chip sélectionné → placeholder adapté
await safe('02-chip-donnees', 'chip « Interroger mes données » actif, placeholder adapté', async () => {
  await page.click('[data-chip-cle="donnees"]');
  await page.waitForTimeout(300);
});

// 3 · réponse DONNÉES : le compte + la phrase récap M109 (aucun bouton)
await safe('03-donnees-recap', 'réponse données : chiffre + récap M109 (phrase, pas de bouton)', async () => {
  await page.fill('textarea', 'Combien de parcelles à Saint-Paul ?');
  await page.click('[data-accueil-envoyer]');
  await page.waitForSelector('[data-reponse]', { timeout: 30000 });
  await page.waitForTimeout(600);
});

// 4 · bouton « Nouveau fil » (présent dès qu'un fil existe)
await safe('04-nouveau-fil', 'bouton « Nouveau fil » — vrai bouton secondaire à portée du champ', async () => {
  await page.waitForSelector('[data-fil-nouveau]');
});

// 5 · réponse WEB courte + source (chip web)
await safe('05-web-court', 'réponse web COURTE : le fait + Source : web · consulté le', async () => {
  await page.click('[data-fil-nouveau]');
  await page.waitForSelector('[data-accueil-chips]');
  await page.click('[data-chip-cle="web"]');
  await page.fill('textarea', 'Qui est le maire de Saint-Denis ?');
  await page.click('[data-accueil-envoyer]');
  await page.waitForSelector('[data-reponse]', { timeout: 40000 });
  await page.waitForTimeout(600);
});

// 6 · parcours PROJET guidé (chip « Créer un projet », prérempli depuis le texte libre)
await safe('06-parcours-projet', 'parcours projet guidé, prérempli (jamais de création directe)', async () => {
  await page.click('[data-fil-nouveau]');
  await page.waitForSelector('[data-accueil-chips]');
  await page.click('[data-chip-cle="projet"]');
  await page.fill('textarea', 'résidence 12 lots à Bras-Panon');
  await page.click('[data-accueil-envoyer]');
  await page.waitForSelector('[data-parcours-projet]', { timeout: 20000 });
  await page.waitForTimeout(400);
});

// 7 · l'étape Commune du parcours (référentiel, jamais texte libre)
await safe('07-projet-commune', 'étape Commune : select du référentiel /communes', async () => {
  await page.click('[data-projet-suivant]');            // Nom → Commune
  await page.waitForSelector('[data-projet-commune]');
  await page.waitForTimeout(300);
});

// 8 · carte PRÉCISION (récap-péage RECHERCHE avec clarification) — best effort
await safe('08-carte-precision', 'carte PRÉCISION : thème mint, placeholder « Votre réponse… »', async () => {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' });
  await page.click('[data-rail="copilote"], button:has-text("IA")').catch(() => {});
  await page.waitForSelector('textarea');
  await page.fill('textarea', 'Je cherche des terrains à fort potentiel');
  await page.click('[data-accueil-envoyer]');
  await page.waitForSelector('[data-recap-clarif], [data-recap]', { timeout: 30000 });
  await page.waitForTimeout(500);
});

await browser.close();
console.log(`\n✅ captures dans ${OUT}`);
