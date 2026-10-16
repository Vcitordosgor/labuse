import { ouvrir, aller, shot, lien } from './harness.mjs';

const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});

await aller(page, lien.outil('courriers'));
await page.waitForTimeout(2500);
const input = await page.$('[data-courrier-idu]');
await input.click(); await input.type('97416000EW0446', { delay: 50 });
await page.waitForTimeout(1800); await input.press('Enter'); await page.waitForTimeout(2500);

// -> Rédiger
let btns = await page.$$('button');
for (const b of btns) { const t=(await b.innerText().catch(()=>'')).trim(); if(/Rédiger/.test(t)){await b.click();break;} }
await page.waitForTimeout(2500);
// -> Vérifier l'envoi
btns = await page.$$('button');
for (const b of btns) { const t=(await b.innerText().catch(()=>'')).trim(); if(/Vérifier l'envoi|Vérifier/.test(t)){await b.click();break;} }
await page.waitForTimeout(3000);
let b3 = await page.evaluate(() => document.body.innerText);
// extract the envoi-relevant region
const i = b3.indexOf('3 · Envoi');
console.log('--- STEP3 ENVOI region ---\n', b3.slice(i, i + 1800));
await shot(page, F, 'A_step3_envoi_v2', { full: true });

// look for send/deposit button and status
btns = await page.$$('button');
const labels = [];
for (const b of btns) { const t=(await b.innerText().catch(()=>'')).trim(); if(t) labels.push(t); }
console.log('BTNS:', JSON.stringify(labels));
console.log('HTTP', JSON.stringify(journal.httpErrors));
await browser.close();
