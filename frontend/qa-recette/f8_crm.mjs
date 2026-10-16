import { ouvrir, aller, shot, debordements } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
// click CRM in left rail
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);
const body = await page.evaluate(() => (document.querySelector('main')||document.body).innerText.slice(0,2500));
console.log('--- CRM ---\n', body);
await shot(page, F, 'C_crm_pipeline', { full: true });
const deb = await debordements(page);
console.log('DEBORDEMENTS:', JSON.stringify(deb.slice(0,6)));
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,8)), 'ERR', journal.consoleErrors.length, JSON.stringify(journal.consoleErrors.slice(0,3)));
await browser.close();
