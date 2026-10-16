import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '#surveillance=criteres');
await page.waitForTimeout(3000);
// find the card with Cilaos + "En pause" and click its supprimer
const res = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('[data-alerte-supprimer]')];
  // find the one whose enclosing card mentions Cilaos and En pause
  for (const b of btns) {
    let c = b; for (let i=0;i<6 && c;i++) c=c.parentElement;
    const card = b.closest('article,li,div');
  }
  // simpler: match by nearest ancestor text
  const cards = [...document.querySelectorAll('div')].filter(d => /Cilaos/.test(d.innerText) && /En pause|Reprendre/.test(d.innerText) && d.querySelector('[data-alerte-supprimer]'));
  if (!cards.length) return 'no-card';
  // pick the smallest (most specific) card
  cards.sort((a,b)=>a.innerText.length-b.innerText.length);
  const b = cards[0].querySelector('[data-alerte-supprimer]');
  if (b) { b.click(); return 'deleted'; }
  return 'no-btn';
});
console.log('delete:', res);
await page.waitForTimeout(2500);
// handle possible confirm dialog
await shot(page, F, 'B_alerte_supprimee', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,5)));
await browser.close();
