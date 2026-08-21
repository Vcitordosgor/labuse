// M137-Q — captures : voie « Procédure & changement » du hub PLU.
//  A) commune EN procédure (Saint-André) → « Simuler → » présélectionne la commune + statut en_cours.
//  B) commune SANS procédure (Saint-Paul) → mention « aucune procédure en cours, hypothétique ».
import { chromium } from '../../frontend/node_modules/playwright/index.mjs';
const BASE = 'http://localhost:5173/socle/';
const OUT = new URL('./captures', import.meta.url).pathname;
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage({ viewport: { width: 1440, height: 1024 } });
const soft = async (fn, w) => { try { await fn() } catch (e) { console.log('WARN', w, String(e).slice(0, 160)) } };
const has = (re) => page.evaluate((s) => new RegExp(s).test(document.body.innerText), re.source);

await page.goto(BASE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(3500);

// ouvrir le tiroir Outils → outil PLU
await soft(async () => { await page.getByRole('button', { name: 'Outils' }).first().click(); await page.waitForTimeout(700); }, 'outils');
await soft(async () => { await page.locator('[data-outil="plu"]').click(); await page.waitForTimeout(1200); }, 'plu');
// voie fusionnée « Procédure & changement »
await soft(async () => { await page.locator('[data-plu-voie="procchg"]').click(); await page.waitForTimeout(1500); }, 'voie procchg');

// la liste des communes en procédure doit apparaître (radar)
await page.waitForSelector('[data-procchg-commune]', { timeout: 15000 }).catch(() => console.log('WARN liste procédures absente'));
const nProc = await page.locator('[data-procchg-commune]').count();
console.log('communes en procédure listées:', nProc);

// ── A) commune EN procédure : « Simuler ce que ça changerait → » sur Saint-André ──
await soft(async () => {
  await page.locator('[data-procchg-commune="Saint-André"] [data-procchg-simuler]').click();
  await page.waitForTimeout(1500);
}, 'simuler Saint-André');
const statutEnCours = await page.locator('[data-procchg-statut="en_cours"]').count();
console.log('A · statut en_cours affiché:', statutEnCours > 0, '| commune préremplie:',
  await page.locator('[data-commune-scope]').inputValue().catch(() => '?'));
// lancer la bascule AU→U (chip) pour montrer la simulation reliée à la procédure
await soft(async () => { await page.getByText(/→ U$/).first().click(); await page.waitForTimeout(1200); }, 'chip AU→U');
await page.waitForFunction(() => /parcelles en |premières sur/.test(document.body.innerText), { timeout: 30000 }).catch(() => console.log('WARN résultat simu absent'));
await page.screenshot({ path: `${OUT}/A_procedure_simulation_preremplie.png`, fullPage: true });

// ── B) commune SANS procédure : sélectionner Saint-Paul → mention hypothétique ──
await soft(async () => { await page.locator('[data-commune-scope]').selectOption({ label: 'Saint-Paul' }); await page.waitForTimeout(1500); }, 'select Saint-Paul');
const hypo = await page.locator('[data-procchg-statut="hypothetique"]').count();
const mention = await page.evaluate(() => {
  const el = document.querySelector('[data-procchg-statut="hypothetique"]');
  return el ? el.textContent.replace(/\s+/g, ' ').trim() : '(absente)';
});
console.log('B · mention hypothétique affichée:', hypo > 0);
console.log('B · texte:', mention.slice(0, 130));
await page.screenshot({ path: `${OUT}/B_hors_procedure_hypothetique.png`, fullPage: true });

await b.close();
const okA = statutEnCours > 0, okB = hypo > 0;
console.log(okA && okB && nProc >= 3
  ? `OK — ${nProc} communes en procédure · A préremplie · B mention hypothétique`
  : 'À VÉRIFIER (voir WARN ci-dessus)');
