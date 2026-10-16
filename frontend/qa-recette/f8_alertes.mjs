import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '#surveillance=criteres');
await page.waitForTimeout(3000);
const body = await page.evaluate(() => (document.querySelector('main,aside')||document.body).innerText.slice(0,1500));
console.log('--- ALERTES (criteres) ---\n', body);
await shot(page, F, 'B_alertes_criteres', { full: true });
// list buttons/controls
const btns = await page.$$eval('button', bs => bs.map(b=>(b.innerText||'').trim()).filter(Boolean).slice(0,40));
console.log('BTNS:', JSON.stringify(btns));
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
