import { ouvrir, aller, shot, lien } from './harness.mjs';
import { FAM } from './_outils_lib.mjs';

const { browser, page, journal } = await ouvrir({});
// Ouvrir le menu Outils via deep-link d'un outil puis inspecter le rail,
// mais d'abord la page d'accueil pour cliquer le rail.
const ms = await aller(page, '');
await page.waitForTimeout(1500);

// Cherche l'entrée "Outils" dans le rail gauche
const relevé = await page.evaluate(() => {
  const txts = Array.from(document.querySelectorAll('button,a,[role="button"]'))
    .map(e => (e.innerText||'').replace(/\s+/g,' ').trim())
    .filter(t => t && t.length < 60);
  return txts;
});
console.log('loadMs', ms);
console.log('BOUTONS VISIBLES:', JSON.stringify(relevé.slice(0,40)));

// Tente de cliquer un bouton contenant "Outils" ou "16 outils"
const clicked = await page.evaluate(() => {
  const cand = Array.from(document.querySelectorAll('button,a,[role="button"]'))
    .find(e => /outil/i.test(e.innerText||''));
  if (cand) { cand.click(); return (cand.innerText||'').trim(); }
  return null;
});
console.log('CLIC OUTILS:', clicked);
await page.waitForTimeout(1500);
const p1 = await shot(page, FAM, 'menu-outils-ouvert', { full: true });
console.log('shot', p1);

// Liste les cartes d'outils maintenant affichées
const cartes = await page.evaluate(() => {
  return Array.from(document.querySelectorAll('button,a,[role="button"],[class*="card"],[class*="Card"]'))
    .map(e => (e.innerText||'').replace(/\s+/g,' ').trim())
    .filter(t => t && t.length < 80);
});
console.log('CARTES OUTILS:', JSON.stringify([...new Set(cartes)].slice(0,60)));

console.log('err', journal.consoleErrors.length, 'http', journal.httpErrors.length, 'page', journal.pageErrors.length);
if (journal.consoleErrors.length) console.log('CONSOLE', journal.consoleErrors.slice(0,5));
if (journal.httpErrors.length) console.log('HTTP', journal.httpErrors.slice(0,8));
await browser.close();
