import { ouvrir, aller, shot, lien } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.fiche('97411000AT0427'));
await page.waitForTimeout(3000);
// button now should say "Ne plus suivre"
const info = await page.evaluate(() => {
  const b = [...document.querySelectorAll('button')].find(x => /suivre cette parcelle|ne plus suivre|suivie/i.test((x.getAttribute('aria-label')||'')+(x.innerText||'')));
  return b ? { aria: b.getAttribute('aria-label'), txt: (b.innerText||'').trim() } : null;
});
console.log('button state:', JSON.stringify(info));
// click to un-follow
const sel = 'button[aria-label*="suivre"], button[aria-label*="Suivre"]';
const b = await page.$(sel);
if (b) { await b.click(); await page.waitForTimeout(2000); console.log('un-followed'); }
await shot(page, F, 'B_fiche_ne_plus_suivre', { full: false });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
