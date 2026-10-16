import { ouvrir, aller, shot, lien, debordements } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
const out = {};
function dump(tag){ out[tag]={err:[...journal.consoleErrors],http:[...journal.httpErrors],pe:[...journal.pageErrors]}; journal.consoleErrors.length=0;journal.httpErrors.length=0;journal.pageErrors.length=0; }

for (const vue of ['parcelles','secteurs','criteres']) {
  const ms = await aller(page, lien.surveillance(vue));
  await page.waitForTimeout(2200);
  const body = await page.evaluate(() => document.body.innerText.slice(0, 1400));
  console.log(`\n==== SURVEILLANCE ${vue} (loadMs ${ms}) ====\n`, body.slice(0, 900));
  await shot(page, F, `B_surveillance_${vue}`, { full: true });
  dump('B_'+vue);
}
console.log('\nJOURNAL', JSON.stringify(out));
await browser.close();
