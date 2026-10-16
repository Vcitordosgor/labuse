import { ouvrir, aller, shot, lien } from './harness.mjs';

const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});

await aller(page, lien.outil('courriers'));
await page.waitForTimeout(2500);
const input = await page.$('[data-courrier-idu]');
await input.click(); await input.type('97416000EW0446', { delay: 50 });
await page.waitForTimeout(1800); await input.press('Enter'); await page.waitForTimeout(2200);
let btns = await page.$$('button');
for (const b of btns) { const t=(await b.innerText().catch(()=>'')).trim(); if(/Rédiger/.test(t)){await b.click();break;} }
await page.waitForTimeout(2000);
btns = await page.$$('button');
for (const b of btns) { const t=(await b.innerText().catch(()=>'')).trim(); if(/Vérifier/.test(t)){await b.click();break;} }
await page.waitForTimeout(2500);
// click "Demander l'envoi à LABUSE"
btns = await page.$$('button');
let sent = false;
for (const b of btns) { const t=(await b.innerText().catch(()=>'')).trim(); if(/Demander l'envoi/.test(t)){await b.click(); sent=true; break;} }
console.log('clicked demander:', sent);
await page.waitForTimeout(3500);
let body = await page.evaluate(() => document.body.innerText);
const i = body.indexOf('3 · Envoi');
console.log('--- APRES DEMANDE ---\n', body.slice(i, i + 1400));
await shot(page, F, 'A_demande_confirmee', { full: true });
console.log('HTTP', JSON.stringify(journal.httpErrors), 'ERR', journal.consoleErrors.length);
await browser.close();
