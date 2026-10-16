// Vérifie que les boutons d'action des réponses Copilote NE SONT PAS morts :
//  - Q5 "Voir sur la carte ... Saint-Leu" → applique un filtre + ouvre le listing
//  - Q1 "Ouvrir la fiche" (voie) → ouvre la fiche parcelle
import { ouvrir, aller, shot } from './harness.mjs';
const FAM = '06-copilote';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await (await page.$('[data-rail="copilote"]')).click();
await page.waitForSelector('[data-copilote]', { timeout: 10000 });
await page.waitForTimeout(800);

async function demander(q) {
  const nf = await page.$('[data-fil-nouveau]'); if (nf) { await nf.click().catch(()=>{}); await sleep(400); }
  const ta = await page.$('[data-brief]'); await ta.fill(q);
  await (await page.$('[data-accueil-envoyer]')).click();
  await page.waitForSelector('[data-reponse]', { timeout: 45000 });
  await sleep(1500);
}

// Q5 — carte_filtre
await demander('Montre-moi les terrains de plus de 1000 m² à Saint-Leu');
const carteBtn = await page.$('[data-reponse-carte]');
console.log('carte bouton présent:', !!carteBtn);
if (carteBtn) {
  await carteBtn.click();
  await page.waitForTimeout(3500);
  const etat = await page.evaluate(() => ({
    url: location.hash,
    listing: !!document.querySelector('[data-results], .results, [class*="result"]'),
    bodyA: document.body.innerText.slice(0, 0),
  }));
  console.log('après clic carte:', JSON.stringify(etat));
  await shot(page, FAM, '20_carte_filtre_applique', { full: true });
}

// Q1 — voie "Ouvrir la fiche"
await (await page.$('[data-rail="copilote"]')).click(); await sleep(600);
await demander('Que puis-je construire sur la parcelle 97422000BX1106 ?');
const voieBtn = await page.$('[data-reponse-voie]');
console.log('voie bouton présent:', !!voieBtn, voieBtn ? await voieBtn.textContent() : '');
if (voieBtn) {
  await voieBtn.click();
  await page.waitForTimeout(3500);
  const ficheOuverte = await page.evaluate(() => ({
    url: location.hash,
    fiche: !!document.querySelector('[data-fiche], [class*="Fiche"]'),
    titreIdu: /97422000BX1106/.test(document.body.innerText),
  }));
  console.log('après clic voie fiche:', JSON.stringify(ficheOuverte));
  await shot(page, FAM, '21_voie_ouvrir_fiche', { full: true });
}

console.log('journal err', journal.consoleErrors.length, 'http', journal.httpErrors.length, 'page', journal.pageErrors.length);
if (journal.httpErrors.length) console.log(JSON.stringify(journal.httpErrors.slice(0,8)));
await browser.close();
console.log('FINI');
