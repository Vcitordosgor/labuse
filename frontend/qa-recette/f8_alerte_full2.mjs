import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '#surveillance=criteres');
await page.waitForTimeout(3000);
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/Nouvelle alerte/.test(x.innerText)); b&&b.click(); });
await page.waitForSelector('[data-veille-form]', { timeout: 6000 });
// select a commune via the <select>
await page.selectOption('[data-veille-form-ajout-commune]', 'Cilaos');
await page.waitForTimeout(600);
// set a surface min
await page.fill('[data-veille-form-surface]', '500');
await page.waitForTimeout(400);
const chips = await page.$$eval('[data-veille-form-commune]', e => e.map(x=>x.innerText.trim()));
console.log('commune chips:', JSON.stringify(chips));
await shot(page, F, 'B_alerte_form_rempli_v2', { full: true });
await page.click('[data-veille-form-creer]');
await page.waitForTimeout(2800);
const msg = await page.$$eval('[data-veille-form-msg]', e=>e.map(x=>x.innerText)).catch(()=>[]);
console.log('form msg:', JSON.stringify(msg));
await shot(page, F, 'B_alerte_creee_v2', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,8)), 'ERR', journal.consoleErrors.length);
await browser.close();
