import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '#surveillance=criteres');
await page.waitForTimeout(3000);
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/Nouvelle alerte/.test(x.innerText)); b&&b.click(); });
await page.waitForTimeout(1200);
// add a commune (click "Cilaos")
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>x.innerText.trim()==='Cilaos'); b&&b.click(); });
await page.waitForTimeout(800);
await shot(page, F, 'B_alerte_form_rempli', { full: true });
// find create/valider button
const createLabel = await page.evaluate(() => {
  const b=[...document.querySelectorAll('button')].find(x=>/Créer|Valider|Enregistrer|Ajouter l.alerte|Activer/i.test(x.innerText));
  if(b){ b.click(); return b.innerText.trim(); } return null;
});
console.log('create button:', JSON.stringify(createLabel));
await page.waitForTimeout(2500);
await shot(page, F, 'B_alerte_creee', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,8)), 'ERR', journal.consoleErrors.length);
await browser.close();
