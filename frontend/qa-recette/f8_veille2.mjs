import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';

for (const vue of ['parcelles','secteurs','criteres']) {
  const { browser, page, journal } = await ouvrir({});  // fresh browser each time
  const ms = await aller(page, `#surveillance=${vue}`);
  await page.waitForTimeout(2500);
  const body = await page.evaluate(() => {
    const el = document.querySelector('aside, [role="dialog"], main') || document.body;
    return el.innerText.slice(0, 1000);
  });
  // find the title / tabs
  const title = await page.evaluate(() => {
    const h = [...document.querySelectorAll('h1,h2,h3,[class*="title"]')].map(e=>e.innerText.trim()).filter(Boolean);
    return h.slice(0,5);
  });
  console.log(`\n==== ${vue} (loadMs ${ms}) TITLES: ${JSON.stringify(title)} ====\n`, body.slice(0, 700));
  await shot(page, F, `B_fresh_surveillance_${vue}`, { full: true });
  console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,5)), 'ERR', journal.consoleErrors.length);
  await browser.close();
}
