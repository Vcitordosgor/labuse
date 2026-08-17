// M102 P4 — captures de recette Copilote : indicateur de traitement, porte cliquable,
// récap avec Corriger, accueil sans encart. Usage : BASE=http://localhost:5173/ node qa/m102/captures.mjs
// (vite dev + API :8000 ; PNG sous qa/m102/captures/<stamp>/, jamais commités.)
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ channel: 'chrome' });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(25000);

async function shot(name, note) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`📸 ${name} — ${note}`);
}

// Retenir la réponse /ask 2,5 s pour photographier l'INDICATEUR pendant le traitement.
await page.route('**/api/copilote-v2/ask', async (route) => {
  await new Promise((r) => setTimeout(r, 2500));
  await route.continue();
});

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.click('[data-rail="copilote"], button:has-text("IA")').catch(async () => {
  await page.click('text=IA');
});
await page.waitForSelector('[data-accueil-envoyer]');
await shot('01-accueil-sans-encart', 'accueil Copilote — encart « claim » retiré (P3)');

// 1 · indicateur pendant le traitement (réponse retenue 2,5 s)
await page.fill('textarea', "la commune de Saint-Leu est-elle en vérif procédure PLU ?");
await page.click('[data-accueil-envoyer]');
await page.waitForSelector('[data-traitement]', { timeout: 4000 });
await shot('02-indicateur-traitement', 'trois points mauves en pulsation — pas de fausse progression');

// 2 · la proposition est une ACTION : bouton « Ouvrir l'outil → »
await page.waitForSelector('[data-reponse-porte]');
await shot('03-porte-cliquable', 'proposition Vérif procédure PLU avec bouton Ouvrir l’outil');
await page.click('[data-reponse-porte]');
await page.waitForTimeout(1200);
await shot('04-outil-ouvert', 'le clic ouvre réellement l’outil (setModule → vue cartes)');

// 3 · récap avec bouton Corriger (mission lourde M78, inchangé mais photographié)
await page.click('button:has-text("IA")').catch(() => {});
await page.waitForSelector('[data-accueil-envoyer]');
await page.fill('textarea', '15 logements à Saint-Paul');
await page.click('[data-accueil-envoyer]');
await page.waitForSelector('text=Corriger', { timeout: 20000 });
await shot('05-recap-corriger', 'récap-confirmation avec bouton Corriger (péage mission lourde)');

await browser.close();
console.log(`\nCaptures : ${OUT}`);
