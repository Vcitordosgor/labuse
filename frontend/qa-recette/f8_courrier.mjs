import { ouvrir, aller, shot, lien, debordements } from './harness.mjs';

const F = '08-courrier-veille-crm';
const { browser, page, journal } = await ouvrir({});
const out = {};

async function dump(tag) {
  out[tag] = { err: [...journal.consoleErrors], http: [...journal.httpErrors], pe: [...journal.pageErrors] };
  journal.consoleErrors.length = 0; journal.httpErrors.length = 0; journal.pageErrors.length = 0;
}

// 1) Outil Courriers via deep-link sur parcelle société
let ms = await aller(page, lien.outilSurParcelle('courriers', '97416000EW0446'));
await page.waitForTimeout(2500);
let txt1 = await page.evaluate(() => document.body.innerText.slice(0, 1500));
console.log('--- courriers EW0446 loadMs', ms, '---\n', txt1.slice(0, 900));
await shot(page, F, 'A_courriers_societe_EW0446', { full: true });
await dump('A_societe');

// cherche aperçu/générer
const boutons = await page.evaluate(() =>
  [...document.querySelectorAll('button,a')].map(b => (b.innerText || '').trim()).filter(Boolean).slice(0, 40));
console.log('BOUTONS:', JSON.stringify(boutons));

// 2) parcelle normale (particulier)
ms = await aller(page, lien.outilSurParcelle('courriers', '97411000AT0427'));
await page.waitForTimeout(2500);
let txt2 = await page.evaluate(() => document.body.innerText.slice(0, 1500));
console.log('--- courriers AT0427 loadMs', ms, '---\n', txt2.slice(0, 900));
await shot(page, F, 'A_courriers_particulier_AT0427', { full: true });
await dump('A_particulier');

// 3) parcelle "sans proprio" BD0967
ms = await aller(page, lien.outilSurParcelle('courriers', '97417000BD0967'));
await page.waitForTimeout(2500);
let txt3 = await page.evaluate(() => document.body.innerText.slice(0, 1500));
console.log('--- courriers BD0967 loadMs', ms, '---\n', txt3.slice(0, 900));
await shot(page, F, 'A_courriers_sansproprio_BD0967', { full: true });
await dump('A_sansproprio');

const deb = await debordements(page);
console.log('DEBORDEMENTS BD0967:', JSON.stringify(deb.slice(0, 8)));

console.log('JOURNAL', JSON.stringify(out, null, 1));
await browser.close();
