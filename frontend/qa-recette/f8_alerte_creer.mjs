import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '#surveillance=criteres');
await page.waitForTimeout(3000);

// click "+ Nouvelle alerte"
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/Nouvelle alerte/.test(x.innerText)); b&&b.click(); });
await page.waitForTimeout(1500);
await shot(page, F, 'B_alerte_form', { full: true });
const form = await page.evaluate(() => (document.querySelector('main,aside')||document.body).innerText.slice(0,1200));
console.log('--- FORM ---\n', form);

// find a submit/create button inside the form
const createBtns = await page.$$eval('button', bs => bs.map(b=>(b.innerText||'').trim()).filter(Boolean));
console.log('BTNS:', JSON.stringify(createBtns));
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,6)), 'ERR', journal.consoleErrors.length);
await browser.close();
