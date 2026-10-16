import { ouvrir, aller, shot, lien } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.fiche('97411000AT0427'));
await page.waitForTimeout(3000);

const sel = 'button[aria-label*="Suivre cette parcelle"]';
await page.waitForSelector(sel, { timeout: 8000 });
const before = await page.getAttribute(sel, 'aria-label');
console.log('aria before:', before);
await page.click(sel);
await page.waitForTimeout(2500);
const after = await page.$eval(sel, el => el.getAttribute('aria-label')).catch(()=> 'selector-gone');
console.log('aria after click:', after);
await shot(page, F, 'B_fiche_suivre_toggle', { full: false });

// verify via API
await page.waitForTimeout(500);
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);

// now un-follow to restore state (toggle back)
const stillThere = await page.$(sel);
if (stillThere) { await page.click(sel); await page.waitForTimeout(1500);
  const a2 = await page.$eval(sel, el => el.getAttribute('aria-label')).catch(()=>'gone');
  console.log('aria after un-follow:', a2); }
await browser.close();
