import { ouvrir, aller, shot, lien } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, lien.outil('courriers'));
await page.waitForTimeout(2500);
const input = await page.$('[data-courrier-idu]');
await input.click(); await input.type('97417000AL0131', { delay: 50 });
await page.waitForTimeout(1800); await input.press('Enter'); await page.waitForTimeout(2800);
let body = await page.evaluate(() => {
  const el = document.querySelector('[data-courrier-ajout-bloque]');
  return { bloque: el ? el.innerText : null,
           dest: [...document.querySelectorAll('[data-courrier-dest]')].map(e=>e.innerText.trim()) };
});
console.log('BLOQUE:', JSON.stringify(body.bloque));
console.log('DEST:', JSON.stringify(body.dest));
await shot(page, F, 'A_parcelle_nu_bloquee', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors), 'ERR', journal.consoleErrors.length);
await browser.close();
