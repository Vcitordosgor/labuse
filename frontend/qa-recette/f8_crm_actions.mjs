import { ouvrir, aller, shot } from './harness.mjs';
const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
await aller(page, '');
await page.waitForTimeout(2500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3500);

// 1) Click a card to open detail (the parcelle idu link)
const cardClick = await page.evaluate(() => {
  const b = [...document.querySelectorAll('button,a')].find(x => /^9740\d{7}$|^974\d{8}$|^\d{3}\d{2}\d{3}[A-Z]{2}\d{4}$/.test(x.innerText.trim()));
  if (b) { const l=b.innerText.trim(); b.click(); return l; }
  return null;
});
console.log('clicked card idu:', JSON.stringify(cardClick));
await page.waitForTimeout(2500);
const hash1 = await page.evaluate(()=>location.hash);
console.log('hash after card click:', hash1);
await shot(page, F, 'C_crm_card_click', { full: false });

// 2) Personnaliser
await aller(page, '');
await page.waitForTimeout(1500);
await page.evaluate(() => { const b=[...document.querySelectorAll('button,a')].find(x=>x.innerText.trim()==='CRM'); b&&b.click(); });
await page.waitForTimeout(3000);
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/Personnaliser/.test(x.innerText)); b&&b.click(); });
await page.waitForTimeout(2000);
const persoBody = await page.evaluate(() => (document.querySelector('[role="dialog"],main')||document.body).innerText.slice(0,900));
console.log('--- PERSONNALISER ---\n', persoBody);
await shot(page, F, 'C_crm_personnaliser', { full: true });

// 3) Archivées
await page.keyboard.press('Escape');
await page.waitForTimeout(800);
await page.evaluate(() => { const b=[...document.querySelectorAll('button')].find(x=>/Archivées/.test(x.innerText)); b&&b.click(); });
await page.waitForTimeout(2000);
const archBody = await page.evaluate(() => (document.querySelector('[role="dialog"],main')||document.body).innerText.slice(0,700));
console.log('--- ARCHIVÉES ---\n', archBody);
await shot(page, F, 'C_crm_archivees', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors.slice(0,8)), 'ERR', journal.consoleErrors.length);
await browser.close();
