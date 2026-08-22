// Capture de recette — le bouton PDF du Courrier fonctionne sur les 3 modèles :
// le PDF se télécharge (magic %PDF), son contenu correspond au courrier affiché.
// Usage : BASE=http://localhost:5173/socle/ node qa/courrier/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const BASE = (process.env.BASE || 'http://localhost:5173/socle/').replace(/\/?$/, '/');
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-');
const OUT = new URL(`./captures/${STAMP}`, import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const IDU = '97415000DK1044';
const MOTIFS = ['standard', 'indivision', 'succession'];

const browser = await chromium.launch({ channel: 'chrome' });
const ctx = await browser.newContext({ viewport: { width: 1180, height: 940 }, deviceScaleFactor: 2, acceptDownloads: true });
const page = await ctx.newPage();
page.setDefaultTimeout(30000);
await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(600);
await page.click('button[title="Outils"]');
await page.click('[data-outil="courriers"]');

async function unModele(motif, i) {
  // étape 1 — parcelle (patron omnibox : IDU dans le champ unifié → Entrée pour valider)
  await page.waitForSelector('[data-courrier-idu]', { state: 'visible' });
  await page.fill('[data-courrier-idu]', IDU);
  await page.press('[data-courrier-idu]', 'Enter');
  await page.waitForSelector('[data-courrier-next]:not([disabled])');
  await page.click('[data-courrier-next]');
  // étape 2 — motif
  await page.waitForSelector(`[data-courrier-motif="${motif}"]`, { state: 'visible' });
  await page.click(`[data-courrier-motif="${motif}"]`);
  await page.click('[data-courrier-next]');   // génère → étape 3
  // étape 3 — rédaction (texte affiché)
  await page.waitForSelector('[data-courrier-texte]', { state: 'visible' });
  const affiche = await page.inputValue('[data-courrier-texte]');
  await page.click('[data-courrier-next]');   // → étape 4
  await page.waitForSelector('[data-courrier-pdf]', { state: 'visible' });
  await page.waitForTimeout(300);
  if (i === 0) await page.screenshot({ path: `${OUT}/courrier-etape4.png` });
  // téléchargement RÉEL
  const [dl] = await Promise.all([
    page.waitForEvent('download'),
    page.click('[data-courrier-pdf]'),
  ]);
  const buf = readFileSync(await dl.path());
  writeFileSync(`${OUT}/${motif}.pdf`, buf);                 // sauvegardé → vérif contenu en Python (pypdf)
  writeFileSync(`${OUT}/${motif}.affiche.txt`, affiche);     // le courrier AFFICHÉ (pour comparaison)
  const errVisible = await page.locator('[data-courrier-pdf-err]').count();
  console.log(`  ${motif}: magic=${buf.subarray(0, 5).toString()} · téléchargé=${buf.length}o · erreur_écran=${errVisible}`);
  await page.click('text=Nouveau courrier');   // recommencer pour le motif suivant
}

for (let i = 0; i < MOTIFS.length; i++) await unModele(MOTIFS[i], i);
await browser.close();
console.log('OUT:', OUT);
