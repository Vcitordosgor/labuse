import { ouvrir, aller, shot, lien } from './harness.mjs';

const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});

await aller(page, lien.outil('courriers'));
await page.waitForTimeout(2500);

const sel = '[data-courrier-idu]';
await page.waitForSelector(sel, { timeout: 8000 });
const input = await page.$(sel);
await input.click();
await input.type('97416000EW0446', { delay: 60 });
await page.waitForTimeout(2000);
await input.press('Enter');
await page.waitForTimeout(3000);

let dests = await page.$$eval('[data-courrier-dest]', els => els.map(e => e.innerText.trim())).catch(() => []);
console.log('destinataires:', JSON.stringify(dests));
let msg = await page.$$eval('[data-parcelinput-msg]', els => els.map(e=>e.innerText)).catch(()=>[]);
console.log('msg:', JSON.stringify(msg));
await shot(page, F, 'A_step1_apres_enter', { full: true });

// click "Rédiger ›" button
const btns = await page.$$('button');
for (const b of btns) {
  const t = (await b.innerText().catch(()=>'')).trim();
  if (/Rédiger/.test(t)) { await b.click(); break; }
}
await page.waitForTimeout(3500);
let b2 = await page.evaluate(() => {
  const el = document.querySelector('[data-courrier-apercu], [data-module-panel], aside, [role="dialog"]');
  return (el || document.body).innerText.slice(0, 2500);
});
console.log('--- STEP2 ---\n', b2);
await shot(page, F, 'A_step2_apercu_v2', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors), 'ERR', journal.consoleErrors.length);
await browser.close();
