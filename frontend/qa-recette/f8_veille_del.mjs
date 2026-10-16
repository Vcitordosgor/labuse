import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '#surveillance=parcelles');
await page.waitForTimeout(3000);

// find the row for AT 0427 (Saint-Denis) and click its "Ne plus suivre"
const rowTexts = await page.$$eval('tr', trs => trs.map(t => t.innerText.replace(/\s+/g,' ').trim()).filter(x=>/AT 0427/.test(x)));
console.log('AT 0427 rows:', JSON.stringify(rowTexts));
await shot(page, F, 'B_surveillance_avec_AT0427', { full: true });

// click "Ne plus suivre" in that row
const ok = await page.evaluate(() => {
  const tr = [...document.querySelectorAll('tr')].find(t => /AT 0427/.test(t.innerText));
  if (!tr) return 'no-row';
  const btn = [...tr.querySelectorAll('button')].find(b => /ne plus suivre|retirer/i.test(b.innerText));
  if (btn) { btn.click(); return 'clicked'; }
  return 'no-btn';
});
console.log('delete:', ok);
await page.waitForTimeout(2500);
await shot(page, F, 'B_surveillance_apres_suppr', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
