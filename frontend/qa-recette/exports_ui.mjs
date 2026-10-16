// RECETTE Famille 5 — génération via l'UI (vrai geste utilisateur).
// Ouvre le rail Docs, ouvre une porte, résout une parcelle via ParcelInput, clique le CTA.
import { ouvrir, aller, shot, BASE } from './harness.mjs';

const FAM = '05-exports';
const IDU = process.argv[2] || '97422000BX1106';

const { browser, page, journal } = await ouvrir({});
const log = (...a) => console.log(...a);

// 1) pose le contexte parcelle d'abord (fiche), pour que ParcelInput prefill / resolve vite
await aller(page, `#idu=${IDU}`);
await page.waitForTimeout(1500);

// 2) clique le rail « Docs »
await page.click('[data-rail="documents"]');
await page.waitForTimeout(1200);
await shot(page, FAM, 'docs_catalogue');
log('catalogue affiché. cartes:', await page.locator('h1:has-text("Documents")').count());

// helper : ouvrir une porte par son nom de carte, résoudre la parcelle, cliquer le CTA
async function genererDoc(nomCarte, cta, { attendreTelechargement = true } = {}) {
  log(`\n--- ${nomCarte} ---`);
  // la carte porte le nom en titre ; clic sur la carte (button door) contenant le texte
  const carte = page.locator(`button:has-text("${nomCarte}")`).first();
  await carte.click();
  await page.waitForTimeout(700);
  // dans la porte : ParcelInput — on tape l'IDU complet et on valide par Enter
  const input = page.locator('.fixed input').first();
  await input.click();
  await input.fill(IDU);
  await page.waitForTimeout(800);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(1200);
  // si une liste de désambiguïsation s'affiche, choisir le bon candidat
  const cand = page.locator('.fixed [data-parcelinput-candidat]');
  if (await cand.count()) { await cand.first().click(); await page.waitForTimeout(600); }
  await shot(page, FAM, `porte_${nomCarte.replace(/\s/g,'_')}`);
  // attendre l'ouverture d'un éventuel onglet (window.open via blob) ou le téléchargement
  const popupP = page.context().waitForEvent('page', { timeout: 6000 }).catch(() => null);
  const btn = page.locator(`.fixed button:has-text("${cta}")`).first();
  const dispo = await btn.isEnabled().catch(() => false);
  log('  CTA « ' + cta + ' » activable =', dispo);
  if (dispo) {
    await btn.click();
    await page.waitForTimeout(2500);
    const popup = await popupP;
    log('  popup/onglet PDF ouvert =', !!popup, popup ? (await popup.url()).slice(0, 80) : '');
    if (popup) await popup.close().catch(() => {});
  }
  await shot(page, FAM, `apres_${nomCarte.replace(/\s/g,'_')}`);
  // fermer la porte (Échap)
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);
}

await genererDoc('Dossier', 'Générer le dossier');
await genererDoc('Apporteur', "Générer l’apporteur");
await genererDoc('Gabarit', 'Générer le gabarit');
await genererDoc('Pré-dossier PC', 'Générer le pré-dossier PC');

log('\n=== JOURNAL ===');
log('consoleErrors', journal.consoleErrors.length, JSON.stringify(journal.consoleErrors.slice(0, 5)));
log('httpErrors', journal.httpErrors.length, JSON.stringify(journal.httpErrors.slice(0, 10)));
log('pageErrors', journal.pageErrors.length, JSON.stringify(journal.pageErrors.slice(0, 3)));
await browser.close();
